export const API_BASE = "http://127.0.0.1:8000";

/* Backend facts (from the repo):
   POST /search/ -> {success, keyword_searched, total_results, results:[JobResult]}; contact fields are always
   null / "not_attempted" there. POST /search/discover-contacts?limit=N -> {success, jobs_processed, emails_found,
   results:[{job_id (Mongo _id), company, company_website, contact_page_url, recruiter_email, contact_status}]}. */
async function request(path, opts = {}) {
  let res;
  try {
    res = await fetch(API_BASE + path, opts);
  } catch {
    throw new Error(`Can't reach the backend at ${API_BASE}. Start FastAPI (uvicorn app.main:app --reload) and make sure CORS is enabled.`);
  }
  const text = await res.text();
  let data = null;
  try { data = JSON.parse(text); } catch { /* not JSON */ }
  if (!res.ok) {
    let d = data?.detail;
    if (Array.isArray(d)) d = d.map((x) => x.msg).join("; ");
    throw new Error(`Backend error (${res.status}): ${d || text || res.statusText}`);
  }
  return data;
}

export const getHealth = () => request("/health/");
export const searchJobs = (keyword) =>
  request("/search/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword }),
  });
export const discoverContacts = (limit) =>
  request(`/search/discover-contacts?limit=${limit}`, { method: "POST" });
