const API_BASE = "http://127.0.0.1:8000";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeUrl = u => { try { const x = new URL(/^https?:\/\//i.test(u) ? u : "https://" + u); return /^https?:$/.test(x.protocol) ? x.href : null; } catch { return null; } };

/* Backend facts (from the repo):
   POST /search/ -> {success, keyword_searched, total_results, results:[JobResult]}; its contact fields are always
   null / "not_attempted", even for jobs already checked. POST /search/discover-contacts?limit=N returns
   {success, jobs_processed, emails_found, results:[{job_id (Mongo _id, not RemoteOK id), company, ...}]}.
   So discovery outcomes are matched to cards by company name and remembered in the browser. */
const STORE = "openings.contacts";
let contacts = {}; try { contacts = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch {}
const ck = c => String(c || "").trim().toLowerCase();
let jobs = [], keyword = "", searched = false, busy = null;

/* ---- routing ---- */
function route() {
  const dash = location.hash.startsWith("#/app");
  $("landing").hidden = dash; $("app").hidden = !dash;
  $("navLinks").innerHTML = dash
    ? `<a href="#/">Home</a><a href="#/" class="hide-m">Features</a><a class="btn primary" href="#/app">Find Jobs</a>`
    : `<a href="#home">Home</a><a href="#features" class="hide-m">Features</a><a href="#how" class="hide-m">How It Works</a><a class="btn primary" href="#/app">Find Jobs</a>`;
  if (dash) { checkHealth(); $("kw").focus(); window.scrollTo(0, 0); }
  else if (/^#(features|how|home)$/.test(location.hash)) $(location.hash.slice(1))?.scrollIntoView();
  else if (location.hash === "#/" || !location.hash) window.scrollTo(0, 0);
}
addEventListener("hashchange", route);

/* ---- API ---- */
async function api(path, opts = {}) {
  let res;
  try { res = await fetch(API_BASE + path, opts); }
  catch { throw new Error(`Can't reach the backend at ${API_BASE}. Start FastAPI (uvicorn app.main:app --reload) and make sure CORS is enabled.`); }
  const text = await res.text(); let data = null; try { data = JSON.parse(text); } catch {}
  if (!res.ok) {
    let d = data?.detail;
    if (Array.isArray(d)) d = d.map(x => x.msg).join("; ");
    throw new Error(`Backend error (${res.status}): ${d || text || res.statusText}`);
  }
  return data;
}
async function checkHealth() {
  try { const h = await api("/health/"); $("dot").className = "dot up"; $("apiState").textContent = `Backend online – v${h.version}`; }
  catch { $("dot").className = "dot down"; $("apiState").textContent = "Backend offline"; }
}

/* ---- UI helpers ---- */
const STATUS = { not_attempted:["Not checked",""], no_website:["No website found","warn"], no_email_found:["No email found","warn"], found:["Contact found","found"], error:["Check failed","error"] };
const note = (kind, msg) => $("msg").innerHTML = msg ? `<div class="note ${kind}" role="${kind==="err"?"alert":"status"}">${esc(msg)}</div>` : "";
function setBusy(which) {
  busy = which;
  $("searchBtn").disabled = !!which; $("discoverBtn").disabled = !!which;
  $("searchBtn").innerHTML = which === "search" ? '<span class="spin"></span>Searching' : "Search";
  $("discoverBtn").innerHTML = which === "discover" ? '<span class="spin"></span>Discovering' : "Discover Contacts";
}
const fmtDate = s => { if (!s) return null; const d = new Date(s); return isNaN(d) ? s : d.toLocaleDateString(undefined, { year:"numeric", month:"short", day:"numeric" }); };
const withContact = j => ({ ...j, ...(contacts[ck(j.company)] || {}) });

function skeletons() {
  $("results").innerHTML = `<div class="cards">${Array(6).fill(`<div class="job"><div class="sk" style="height:20px;width:70%"></div><div class="sk" style="height:14px;width:45%"></div><div class="sk" style="height:22px;width:60%"></div><div class="sk" style="height:60px"></div><div class="sk" style="height:38px"></div></div>`).join("")}</div>`;
}

function render() {
  const el = $("results"), sum = $("summary");
  if (!searched) { sum.hidden = true; el.innerHTML = `<div class="empty"><h3>Start with a keyword</h3><p>Search for a role or skill above, for example “Python Developer”. Results will appear here.</p></div>`; return; }
  if (!jobs.length) { sum.hidden = true; el.innerHTML = `<div class="empty"><h3>No jobs found for “${esc(keyword)}”</h3><p>Try a single skill or a broader title, like “python” or “designer”.</p></div>`; return; }
  const list = jobs.map(withContact), found = list.filter(j => j.contact_status === "found").length;
  sum.hidden = false; sum.innerHTML = `<span>${list.length} job${list.length === 1 ? "" : "s"} for “${esc(keyword)}”</span><span>${found} with a public email</span>`;
  el.innerHTML = `<div class="cards">${list.map(j => {
    const [label, cls] = STATUS[j.contact_status] || [j.contact_status, ""];
    const site = j.company_website && safeUrl(j.company_website), cp = j.contact_page_url && safeUrl(j.contact_page_url), ap = j.apply_url && safeUrl(j.apply_url);
    const row = (k, v) => `<div><dt>${k}</dt><dd>${v}</dd></div>`, none = '<span class="muted">–</span>';
    return `<article class="job">
      <div class="job-top"><div><h3>${esc(j.title)}</h3><div class="sub">${esc(j.company)}</div></div><span class="badge ${cls}">${esc(label)}</span></div>
      <div class="sub">${esc(j.location || "Remote")}${j.posted_at ? " – Posted " + esc(fmtDate(j.posted_at)) : ""}</div>
      ${j.tags?.length ? `<div class="tags">${j.tags.slice(0, 8).map(t => `<span class="tag">${esc(t)}</span>`).join("")}</div>` : ""}
      <dl class="contact">
        ${row("Email", j.recruiter_email ? `<a href="mailto:${esc(j.recruiter_email)}">${esc(j.recruiter_email)}</a>` : none)}
        ${row("Website", site ? `<a href="${esc(site)}" target="_blank" rel="noopener noreferrer">${esc(j.company_website)}</a>` : none)}
        ${row("Contact page", cp ? `<a href="${esc(cp)}" target="_blank" rel="noopener noreferrer">Open page</a>` : none)}
      </dl>
      ${ap ? `<a class="btn ghost" href="${esc(ap)}" target="_blank" rel="noopener noreferrer">Apply</a>` : ""}
    </article>`;
  }).join("")}</div>`;
}

/* ---- actions ---- */
async function search(e) {
  e?.preventDefault();
  const k = $("kw").value.trim();
  if (k.length < 2) { note("err", "Enter at least 2 characters to search."); return; }
  note(); setBusy("search"); skeletons(); $("summary").hidden = true;
  try {
    const data = await api("/search/", { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify({ keyword: k }) });
    keyword = data.keyword_searched || k; jobs = data.results || []; searched = true;
  } catch (err) { note("err", err.message); searched = !!jobs.length || searched; }
  setBusy(); render();
}

async function discover() {
  note("info", "Looking through company websites for public contact info. This can take a minute…");
  setBusy("discover");
  try {
    const d = await api(`/search/discover-contacts?limit=${$("limit").value}`, { method:"POST" });
    (d.results || []).forEach(r => { contacts[ck(r.company)] = { company_website:r.company_website, contact_page_url:r.contact_page_url, recruiter_email:r.recruiter_email, contact_status:r.contact_status }; });
    try { localStorage.setItem(STORE, JSON.stringify(contacts)); } catch {}
    const visible = new Set(jobs.map(j => ck(j.company)));
    const onScreen = (d.results || []).filter(r => visible.has(ck(r.company))).length;
    note(d.success ? "ok" : "err", d.jobs_processed === 0
      ? "Nothing to process: every saved job has already been checked."
      : `Processed ${d.jobs_processed} job${d.jobs_processed === 1 ? "" : "s"}, found ${d.emails_found} public email${d.emails_found === 1 ? "" : "s"}. ${onScreen} matched jobs shown below.`);
  } catch (err) { note("err", err.message); }
  setBusy(); render();
}

$("searchForm").addEventListener("submit", search);
$("discoverBtn").addEventListener("click", discover);
document.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => { $("kw").value = c.dataset.kw; search(); }));
route(); render();
