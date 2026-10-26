/* NOVA Campus: small, framework-free interface consuming the documented REST API. */
"use strict";
const state = { view: "overview", page: 1, pageSize: 10, q: "", status: "", program: "", sort: "newest", dashboard: null, list: null, loadId: 0 };
const $ = selector => document.querySelector(selector);
const $$ = selector => Array.from(document.querySelectorAll(selector));
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const initials = row => ((row.first_name?.[0] || "") + (row.last_name?.[0] || "")).toUpperCase();
const fullName = row => row.first_name + " " + row.last_name;
const shades = ["#e7e4ff","#e3f5f0","#fff0dd","#e5edff","#fbe5e9","#edeaff"];
const inks = ["#6a5bdc","#389f85","#c68e53","#5b84cc","#c36a86","#786aca"];
const avatar = (s, size = "") => `<div class="small-avatar ${size}" style="background:${shades[(s.id || 0) % shades.length]};color:${inks[(s.id || 0) % inks.length]}">${escapeHtml(initials(s))}</div>`;
const dateNice = value => { const date = new Date(value); return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"}); };
const relative = value => { const t = new Date(value).getTime(), seconds = Math.floor((Date.now()-t)/1000); if (!Number.isFinite(t)) return ""; if (seconds<60) return "Just now"; if (seconds<3600) return Math.floor(seconds/60)+" min ago"; if (seconds<86400) return Math.floor(seconds/3600)+" hr ago"; return dateNice(value); };
async function api(url, options = {}) {
  let response;
  try { response = await fetch(url, {...options, headers: {"Content-Type": "application/json", ...(options.headers || {})}}); }
  catch { throw new Error("Cannot connect to the server. Check that NOVA is running."); }
  if (!response.ok) {
    let message = "Request failed (" + response.status + ").";
    try { const body = await response.json(); if (typeof body.detail === "string") message = body.detail; else if (Array.isArray(body.detail)) message = body.detail.map(d => `${d.loc?.at(-1) || "Field"}: ${d.msg}`).join("; "); } catch {}
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
function toast(message, error = false) {
  const element = document.createElement("div"); element.className = "toast" + (error ? " error" : ""); element.textContent = message;
  $("#toastContainer").append(element);
  setTimeout(() => element.remove(), 4500);
}
function setView(view) {
  state.view = view; $$(".page").forEach(p => p.classList.toggle("active",p.id === view + "Page"));
  $$(".nav-item").forEach(item => item.classList.toggle("active",item.dataset.view === view));
  $("#breadcrumb").textContent = {overview:"Overview",students:"Students",insights:"Insights",activity:"Activity log"}[view];
  $("#sidebar").classList.remove("open"); $("#mobileShade").classList.remove("open");
  window.scrollTo({top:0,behavior:"smooth"});
  if (view === "students") loadStudents();
  if (view === "activity") loadActivity();
  if (view === "insights") loadDashboard();
  if (view === "overview") loadDashboard();
}
async function loadDashboard() {
  try {
    const data = await api("/api/dashboard"); state.dashboard = data;
    $("#navCount").textContent = data.total;
    renderDashboard(data);
  } catch (err) { toast(err.message,true); }
}
function statCard(icon, palette, label, value, foot) {
  return `<article class="stat-card"><div class="stat-card-top"><span class="stat-icon ${palette}">${icon}</span><span class="stat-trend">● LIVE</span></div><small>${escapeHtml(label)}</small><div class="stat-value">${escapeHtml(value)}</div><div class="stat-helper">${escapeHtml(foot)}</div></article>`;
}
function departmentBars(items) {
  if (!items.length) return '<div class="empty-state">No program data yet</div>';
  const max = Math.max(1,...items.map(x=>x.count));
  return '<div class="dept-list">'+items.slice(0,7).map(item => `<div class="dept-row"><div class="dept-title"><span>${escapeHtml(item.name)}</span><strong>${item.count} students</strong></div><div class="progress"><div style="width:${item.count/max*100}%"></div></div></div>`).join("")+"</div>";
}
function barChart(items) {
  if (!items.length) return '<div class="empty-state">No enrollment data yet</div>';
  const max = Math.max(1,...items.map(x => x.count));
  return items.map((x,i)=>`<div class="bar-col"><div class="bar ${i===items.length-1 ? "featured":""}" style="height:${Math.max(x.count ? 4:0,x.count/max*83)}%"><span class="bar-value">${x.count}</span></div><div class="bar-label">${escapeHtml(x.label)}</div></div>`).join("");
}
function riskList(items, limit=5) {
  if (!items.length) return '<div class="empty-state"><span>✧</span>All active students are meeting the selected GPA and attendance thresholds.</div>';
  return items.slice(0,limit).map(s=>`<div class="person-item">${avatar(s)}<div class="person-details"><strong>${escapeHtml(fullName(s))}</strong><small>${escapeHtml(s.program)} · ${escapeHtml(s.risk_reason)}</small></div><button class="row-action" data-view-student="${s.id}">View ↗</button></div>`).join("");
}
function activityMarkup(items) {
  if (!items.length) return '<div class="empty-state"><span>✧</span>No changes have been recorded yet.</div>';
  const signs = {created:"+",updated:"✎",deleted:"×",demo:"✦"};
  return items.map(a => `<div class="activity-item"><div class="activity-symbol ${escapeHtml(a.action)}">${signs[a.action]||"•"}</div><div class="activity-details"><strong>${escapeHtml(a.student_name)}</strong><small>${escapeHtml(a.description)}</small></div><span class="subtle">${escapeHtml(relative(a.created_at))}</span></div>`).join("");
}
function renderDashboard(d) {
  $("#statsGrid").innerHTML = [
    statCard("♙","purple","Total students",d.total,"Across all programs"),
    statCard("✓","green","Active enrollments",d.active,"Currently enrolled"),
    statCard("✳","blue","Average GPA",d.average_gpa.toFixed(2)+" / 4","Campus-wide performance"),
    statCard("♡","orange","Need a check-in",d.at_risk,"Students flagged for support")
  ].join("");
  $("#enrollmentChart").innerHTML=barChart(d.enrollments);
  $("#departmentChart").innerHTML=departmentBars(d.departments);
  $("#riskPreview").innerHTML=riskList(d.risk_students,3);
  $("#activityPreview").innerHTML=activityMarkup(d.recent_activity.slice(0,4));
  $("#insightStats").innerHTML=[
    statCard("☷","purple","Average attendance",d.average_attendance+"%","Across all students"),
    statCard("✧","green","Active students",d.active,"Currently enrolled"),
    statCard("♡","orange","Wellbeing flags",d.at_risk,"Active students needing outreach")
  ].join("");
  $("#insightDepartments").innerHTML=departmentBars(d.departments);
  $("#riskFull").innerHTML=riskList(d.risk_students,99);
  const parts=[["Active","#7569ed"],["On leave","#ecb178"],["Graduated","#67c9ad"],["Suspended","#ec819a"]];
  let from=0;
  const stops=parts.map(([name,color])=>{let count=d.status_breakdown[name]||0;let to=from+(d.total?count/d.total*100:0);let part=`${color} ${from.toFixed(2)}% ${to.toFixed(2)}%`;from=to;return part;});
  $("#statusDonut").innerHTML=`<div class="donut" style="background:conic-gradient(${d.total?stops.join(","):"#f2f1ff 0% 100%"})"><div class="donut-center"><strong>${d.total}</strong><span>Students</span></div></div><div class="legend">${parts.map(([name,color])=>`<div class="legend-row"><span class="legend-dot" style="background:${color}"></span>${name}<strong>${d.status_breakdown[name]||0}</strong></div>`).join("")}</div>`;
  $("#lastUpdated").textContent="Updated "+new Date().toLocaleTimeString(undefined,{hour:"numeric",minute:"2-digit"});
}
function queryString() {
  return new URLSearchParams({q:state.q,status:state.status,program:state.program,sort:state.sort,page:String(state.page),page_size:String(state.pageSize)}).toString();
}
async function loadStudents() {
  const id=++state.loadId;
  $("#studentRows").innerHTML='<tr><td colspan="8"><div class="empty-state">Loading student records…</div></td></tr>';
  try {
    const data=await api("/api/students?"+queryString());
    if (id!==state.loadId) return;
    state.list=data;
    renderStudents(data);
  } catch(e) { if(id===state.loadId){$("#studentRows").innerHTML=`<tr><td colspan="8"><div class="empty-state">${escapeHtml(e.message)}</div></td></tr>`;toast(e.message,true);} }
}
function renderStudents(d) {
  $("#directoryTotal").textContent=d.total+" students";
  const select=$("#programFilter"), selected=select.value;
  select.innerHTML='<option value="">All programs</option>'+d.programs.map(p=>`<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`).join("");
  select.value=selected;
  $("#studentRows").innerHTML=d.items.length ? d.items.map(s=>`<tr>
    <td><div class="student-person">${avatar(s)}<div><strong>${escapeHtml(fullName(s))}</strong><small>${escapeHtml(s.email)}</small></div></div></td>
    <td><span class="student-id">${escapeHtml(s.student_number)}</span></td><td>${escapeHtml(s.program)}</td><td>Year ${s.year}</td>
    <td><span class="gpa-chip">${s.gpa.toFixed(2)}</span></td><td>${s.attendance}%</td><td><span class="pill ${s.status.toLowerCase().replaceAll(" ","-")}">${escapeHtml(s.status)}</span></td>
    <td><div class="row-actions"><button class="row-action" data-view-student="${s.id}">View</button><button class="row-action icon-only" aria-label="Edit ${escapeHtml(fullName(s))}" data-edit-student="${s.id}">✎</button></div></td>
  </tr>`).join(""):'<tr><td colspan="8"><div class="empty-state"><span>⌕</span>No students match your search. Try other filters or add a new student.</div></td></tr>';
  const start=d.total?(d.page-1)*d.page_size+1:0,end=Math.min(d.total,d.page*d.page_size);
  $("#paginationLabel").textContent=`Showing ${start}–${end} of ${d.total} students`;
  $("#pageIndicator").textContent=`${d.page} / ${d.pages}`;
  $("#prevPage").disabled=d.page<=1;$("#nextPage").disabled=d.page>=d.pages;
}
async function loadActivity() {
  try { const data=await api("/api/activity");$("#activityFull").innerHTML=activityMarkup(data.items); }
  catch(e) {toast(e.message,true);}
}
function modal(title,eyebrow,content) {
  $("#modalTitle").textContent=title;$("#modalEyebrow").textContent=eyebrow;
  $("#modalContent").innerHTML=content;$("#modalOverlay").classList.add("show");
  $("#modalOverlay").setAttribute("aria-hidden","false");
  document.body.style.overflow="hidden";
  $("#closeModal").focus();
}
function closeModal() {
  $("#modalOverlay").classList.remove("show");$("#modalOverlay").setAttribute("aria-hidden","true");document.body.style.overflow="";
}
const formatDate = () => { const d=new Date(), year=d.getFullYear(),month=String(d.getMonth()+1).padStart(2,"0"),day=String(d.getDate()).padStart(2,"0");return `${year}-${month}-${day}`;};
const formFields=[
  ["first_name","First name","text","e.g. Amara",true],
  ["last_name","Last name","text","e.g. Okafor",true],
  ["student_number","Student ID","text","e.g. NC-2026-101",true],
  ["email","Email address","email","e.g. amara@example.org",true],
  ["phone","Phone number (optional)","tel","+254 700 000 000",false],
  ["program","Program / Course","text","e.g. Computer Science",true],
  ["year","Academic year","number","1–6",true],
  ["gpa","GPA (out of 4.0)","number","0.00–4.00",true],
  ["attendance","Attendance %","number","0–100",true],
  ["enrolled_on","Enrollment date","date","",true]
];
function studentForm(student=null) {
  const isEdit=!!student, field= (name,label,type,placeholder,required) => {
    const value=student?.[name] ?? (name==="enrolled_on"?formatDate():"");
    const constraints=type==="number" ? (name==="gpa"?'min="0" max="4" step="0.01"':name==="attendance"?'min="0" max="100" step="1"':'min="1" max="6" step="1"'):"";
    return `<div class="field"><label for="field-${name}">${label}</label><input id="field-${name}" name="${name}" type="${type}" value="${escapeHtml(value)}" placeholder="${escapeHtml(placeholder)}" ${required?"required":""} ${constraints}></div>`;
  };
  const fields=formFields.map(f=>field(...f)).join("");
  const statuses=["Active","On leave","Graduated","Suspended"];
  modal(isEdit?"Edit student profile":"Add a new student",isEdit?"KEEP THE STORY CURRENT":"A NEW CHAPTER BEGINS",`
    <p class="modal-help">Fields marked as required are validated before saving. Changes persist in your campus database.</p>
    <form id="studentForm"><div class="form-grid">${fields}<div class="field"><label for="field-status">Enrollment status</label><select id="field-status" name="status">${statuses.map(s=>`<option ${s===(student?.status||"Active")?"selected":""}>${s}</option>`).join("")}</select></div><div class="field full"><label for="field-notes">Notes (optional)</label><textarea id="field-notes" name="notes" maxlength="500" placeholder="Any helpful context…">${escapeHtml(student?.notes || "")}</textarea></div></div>
    <div class="modal-actions"><button type="button" class="btn secondary" id="cancelForm">Cancel</button><button type="submit" class="btn primary" id="saveStudent">${isEdit?"Save changes":"＋ Add student"}</button></div></form>`);
  $("#cancelForm").onclick=closeModal;
  $("#studentForm").onsubmit=async event=>{
    event.preventDefault();const button=$("#saveStudent");button.disabled=true;button.textContent="Saving…";
    const data=Object.fromEntries(new FormData(event.currentTarget).entries());
    data.year=Number(data.year);data.gpa=Number(data.gpa);data.attendance=Number(data.attendance);
    if(!data.phone) data.phone=null;
    try{
      await api(isEdit?"/api/students/"+student.id:"/api/students",{method:isEdit?"PATCH":"POST",body:JSON.stringify(data)});
      closeModal();toast(isEdit?"Student profile updated successfully.":"Student added successfully.");
      await Promise.all([loadDashboard(),state.view==="students"?loadStudents():Promise.resolve()]);
    }catch(e){toast(e.message,true);button.disabled=false;button.textContent=isEdit?"Save changes":"＋ Add student";}
  };
}
async function viewStudent(id) {
  try {
    const s=await api("/api/students/"+id);
    modal("Student profile","THE FULL PICTURE",`
      <div class="detail-banner">${avatar(s)}<div><strong>${escapeHtml(fullName(s))}</strong><span>${escapeHtml(s.student_number)} · ${escapeHtml(s.program)}</span></div></div>
      <div class="detail-grid">
      ${[["Email",s.email],["Phone",s.phone||"Not provided"],["Academic year","Year "+s.year],["GPA",s.gpa.toFixed(2)+" / 4.00"],["Attendance",s.attendance+"%"],["Status",s.status],["Enrolled on",dateNice(s.enrolled_on)],["Wellbeing indicator",s.health]].map(([label,value])=>`<div class="detail-box"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`).join("")}
      </div>${s.notes?`<div class="detail-note"><strong>Notes:</strong> ${escapeHtml(s.notes)}</div>`:""}
      ${s.risk_reason?`<div class="detail-note"><strong>Support consideration:</strong> ${escapeHtml(s.risk_reason)}. Connect with the student before drawing conclusions.</div>`:""}
      <div class="modal-actions"><button class="btn secondary" id="deleteFromDetail">Delete</button><button class="btn primary" id="editFromDetail">✎ Edit student</button></div>`);
    $("#editFromDetail").onclick=()=>studentForm(s);
    $("#deleteFromDetail").onclick=()=>confirmDelete(s);
  }catch(e){toast(e.message,true);}
}
async function editStudent(id){try{studentForm(await api("/api/students/"+id));}catch(e){toast(e.message,true);}}
function confirmDelete(student){
  modal("Delete this student?","PLEASE CONFIRM",`<div class="danger-panel">You're about to permanently remove <strong>${escapeHtml(fullName(student))}</strong> (${escapeHtml(student.student_number)}). This action cannot be undone.</div><div class="modal-actions"><button class="btn secondary" id="cancelDelete">Keep student</button><button class="btn danger" id="deleteStudent">Delete permanently</button></div>`);
  $("#cancelDelete").onclick=closeModal;
  $("#deleteStudent").onclick=async()=>{
    const button=$("#deleteStudent");button.disabled=true;
    try{await api("/api/students/"+student.id,{method:"DELETE"});closeModal();toast("Student deleted.");
      await loadDashboard();if(state.view==="students"){ if(state.list?.items.length===1 && state.page>1) state.page--;await loadStudents();}
    }catch(e){toast(e.message,true);button.disabled=false;}
  };
}
function exportCsv(){
  const params=new URLSearchParams({q:state.q,status:state.status,program:state.program});
  const link=document.createElement("a");link.href="/api/students/export?"+params;link.download="nova-campus-students.csv";
  document.body.appendChild(link);link.click();link.remove();toast("Your CSV export has been requested.");
}
function wireUp(){
  $("#yearText").textContent=new Date().getFullYear();
  $$(".nav-item").forEach(button=>button.addEventListener("click",()=>setView(button.dataset.view)));
  document.addEventListener("click",event=>{
    const action=event.target.closest("[data-action]")?.dataset.action;
    if(action==="add") studentForm();
    if(action==="export") exportCsv();
    if(["students","insights","activity"].includes(action)) setView(action);
    const view=event.target.closest("[data-view-student]");
    if(view) viewStudent(Number(view.dataset.viewStudent));
    const edit=event.target.closest("[data-edit-student]");
    if(edit) editStudent(Number(edit.dataset.editStudent));
  });
  let timer;
  $("#searchInput").addEventListener("input",e=>{clearTimeout(timer);timer=setTimeout(()=>{state.q=e.target.value;state.page=1;loadStudents();},220);});
  $("#statusFilter").onchange=e=>{state.status=e.target.value;state.page=1;loadStudents();};
  $("#programFilter").onchange=e=>{state.program=e.target.value;state.page=1;loadStudents();};
  $("#sortFilter").onchange=e=>{state.sort=e.target.value;state.page=1;loadStudents();};
  $("#prevPage").onclick=()=>{if(state.page>1){state.page--;loadStudents();}};
  $("#nextPage").onclick=()=>{if(state.list && state.page<state.list.pages){state.page++;loadStudents();}};
  $("#closeModal").onclick=closeModal;
  $("#modalOverlay").onclick=e=>{if(e.target===$("#modalOverlay")) closeModal();};
  document.addEventListener("keydown",e=>{if(e.key==="Escape" && $("#modalOverlay").classList.contains("show")) closeModal();});
  $("#refreshBtn").onclick=()=>{if(state.view==="students")loadStudents();else if(state.view==="activity")loadActivity();else loadDashboard();toast("Refreshing workspace…");};
  $("#activityRefresh").onclick=loadActivity;
  $("#menuBtn").onclick=()=>{$("#sidebar").classList.toggle("open");$("#mobileShade").classList.toggle("open");};
  $("#mobileShade").onclick=()=>{$("#sidebar").classList.remove("open");$("#mobileShade").classList.remove("open");};
  loadDashboard();
}
document.addEventListener("DOMContentLoaded",wireUp);
