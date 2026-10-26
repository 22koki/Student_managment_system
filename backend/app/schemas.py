"""API input validation, normalization, and explicit constraints."""
from datetime import date
from typing import Literal
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["Active", "On leave", "Graduated", "Suspended"]

def tidy_name(value):
    value = " ".join(value.split())
    if len(value) < 2:
        raise ValueError("Enter at least two characters.")
    return value

def tidy_email(value):
    value = value.strip().lower()
    if len(value) > 120 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError("Enter a valid email address.")
    return value

def tidy_number(value):
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9-]{3,24}", value):
        raise ValueError("Use 3–24 letters, numbers or hyphens.")
    return value

def tidy_phone(value):
    if value is None or not value.strip():
        return None
    value = value.strip()
    if not re.fullmatch(r"[+0-9() .-]{7,20}", value):
        raise ValueError("Enter a valid phone number, or leave blank.")
    return value

class StudentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    student_number: str = Field(min_length=3, max_length=24)
    first_name: str = Field(min_length=2, max_length=60)
    last_name: str = Field(min_length=2, max_length=60)
    email: str = Field(max_length=120)
    phone: str | None = None
    program: str = Field(min_length=2, max_length=80)
    year: int = Field(ge=1, le=6)
    gpa: float = Field(ge=0, le=4, allow_inf_nan=False)
    attendance: int = Field(ge=0, le=100)
    status: Status = "Active"
    enrolled_on: date = Field(default_factory=date.today)
    notes: str = Field(default="", max_length=500)

    @field_validator("first_name", "last_name", "program")
    @classmethod
    def validate_name(cls, value):
        return tidy_name(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return tidy_email(value)

    @field_validator("student_number")
    @classmethod
    def validate_number(cls, value):
        return tidy_number(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        return tidy_phone(value)

class StudentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    student_number: str | None = Field(default=None, min_length=3, max_length=24)
    first_name: str | None = Field(default=None, min_length=2, max_length=60)
    last_name: str | None = Field(default=None, min_length=2, max_length=60)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = None
    program: str | None = Field(default=None, min_length=2, max_length=80)
    year: int | None = Field(default=None, ge=1, le=6)
    gpa: float | None = Field(default=None, ge=0, le=4, allow_inf_nan=False)
    attendance: int | None = Field(default=None, ge=0, le=100)
    status: Status | None = None
    enrolled_on: date | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("first_name", "last_name", "program")
    @classmethod
    def validate_name(cls, value):
        return tidy_name(value) if value is not None else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return tidy_email(value) if value is not None else value

    @field_validator("student_number")
    @classmethod
    def validate_number(cls, value):
        return tidy_number(value) if value is not None else value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        return tidy_phone(value)
