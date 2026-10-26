"""Integration tests use an isolated temporary SQLite file, not the demo database."""
import csv
from io import StringIO
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=tmp_path / "students.db", seed=False)
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def student():
    return {
        "student_number": "TEST-0001", "first_name": "Amina", "last_name": "Mwangi",
        "email": "Amina@example.org", "phone": "+254700000000",
        "program": "Computer Science", "year": 2, "gpa": 3.75,
        "attendance": 92, "status": "Active", "enrolled_on": "2025-09-10",
        "notes": "Synthetic test record."
    }

def test_health_and_ui(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/").status_code == 200
    assert "NOVA Campus" in client.get("/").text
    assert client.get("/api/docs").status_code == 200

def test_complete_crud_flow(client, student):
    empty = client.get("/api/students").json()
    assert empty["total"] == 0
    added = client.post("/api/students", json=student)
    assert added.status_code == 201, added.text
    entry = added.json()
    assert entry["student_number"] == "TEST-0001"
    assert entry["email"] == "amina@example.org"
    assert entry["health"] == "Excellent"
    student_id = entry["id"]
    assert client.get(f"/api/students/{student_id}").json()["first_name"] == "Amina"
    updated = client.patch(f"/api/students/{student_id}", json={"gpa": 1.8, "attendance": 62})
    assert updated.status_code == 200
    assert updated.json()["health"] == "At risk"
    assert updated.json()["risk_reason"] == "Low GPA and attendance"
    assert client.get("/api/dashboard").json()["at_risk"] == 1
    assert client.delete(f"/api/students/{student_id}").status_code == 204
    assert client.get(f"/api/students/{student_id}").status_code == 404
    history = client.get("/api/activity").json()["items"]
    assert [h["action"] for h in history[:3]] == ["deleted", "updated", "created"]

def test_uniqueness_and_normalization(client, student):
    assert client.post("/api/students", json=student).status_code == 201
    copy = {**student,"email":"second@example.org"}
    assert client.post("/api/students", json=copy).status_code == 409
    copy = {**student, "student_number": "TEST-0002","email":"AMINA@EXAMPLE.ORG"}
    assert client.post("/api/students", json=copy).status_code == 409

@pytest.mark.parametrize("field,value", [
    ("year",7),("gpa",4.1),("gpa",-1),("attendance",101),
    ("email","broken"),("student_number","@"),("status","Alien")
])
def test_validation(client, student, field, value):
    payload={**student,field:value}
    assert client.post("/api/students",json=payload).status_code == 422

def test_invalid_patch_and_missing_record(client, student):
    assert client.patch("/api/students/99", json={"year":2}).status_code == 404
    assert client.delete("/api/students/99").status_code == 404
    student_id=client.post("/api/students",json=student).json()["id"]
    assert client.patch(f"/api/students/{student_id}",json={}).status_code == 422
    assert client.patch(f"/api/students/{student_id}",json={"year":None}).status_code == 422
    assert client.patch(f"/api/students/{student_id}",json={"first_name":"A"}).status_code == 422

def test_filters_sort_pagination_and_export(client, student):
    payloads=[
        {**student,"student_number":"TEST-01","email":"a@example.org","last_name":"Zed","program":"Design & Media"},
        {**student,"student_number":"TEST-02","email":"b@example.org","last_name":"Alpha","program":"Computer Science"},
        {**student,"student_number":"TEST-03","email":"c@example.org","last_name":"Beta","status":"On leave"},
    ]
    for p in payloads: assert client.post("/api/students",json=p).status_code == 201
    result=client.get("/api/students",params={"sort":"name","page_size":2}).json()
    assert result["total"]==3 and result["pages"]==2
    assert result["items"][0]["last_name"]=="Alpha"
    assert len(client.get("/api/students",params={"page":2,"page_size":2}).json()["items"])==1
    assert client.get("/api/students",params={"status":"On leave"}).json()["total"]==1
    assert client.get("/api/students",params={"program":"Design & Media"}).json()["total"]==1
    assert client.get("/api/students",params={"q":"TEST-02"}).json()["total"]==1
    assert client.get("/api/students",params={"sort":"invalid"}).status_code==422
    export=client.get("/api/students/export",params={"status":"On leave"})
    assert export.status_code==200 and "text/csv" in export.headers["content-type"]
    rows=list(csv.reader(StringIO(export.text.lstrip("\ufeff"))))
    assert len(rows)==2 and rows[1][0]=="TEST-03"

def test_dashboard_math_and_no_seed(client, student):
    assert client.get("/api/dashboard").json()["total"]==0
    assert client.post("/api/students",json=student).status_code==201
    stats=client.get("/api/dashboard").json()
    assert stats["total"]==1 and stats["active"]==1
    assert stats["average_gpa"]==3.75
    assert stats["average_attendance"]==92
    assert stats["departments"][0]["name"]=="Computer Science"

def test_csv_formula_injection_protection(client, student):
    student["first_name"]="=HYPERLINK"
    assert client.post("/api/students",json=student).status_code==201
    text=client.get("/api/students/export").text
    assert "'=HYPERLINK" in text

def test_sql_search_special_chars_literal(client, student):
    assert client.post("/api/students",json=student).status_code==201
    assert client.get("/api/students",params={"q":"%"}).json()["total"]==0
    assert client.get("/api/students",params={"q":"_"}).json()["total"]==0
