import { useEffect, useState } from "react";
import { getHealth, searchJobs, discoverContacts } from "./api.js";
import JobCard from "./JobCard.jsx";

const STORE = "openings.contacts";
const EXAMPLES = ["Java Developer", "Python Developer", "UI Designer", "Backend Developer"];
const ck = (c) => String(c || "").trim().toLowerCase();
const loadContacts = () => { try { return JSON.parse(localStorage.getItem(STORE) || "{}"); } catch { return {}; } };

const Spin = () => <span className="spin" />;

export default function Dashboard() {
  const [health, setHealth] = useState({ state: "checking", text: "Checking backend…" });
  const [input, setInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [jobs, setJobs] = useState([]);
  const [searched, setSearched] = useState(false);
  const [busy, setBusy] = useState(null); // "search" | "discover" | null
  const [limit, setLimit] = useState("10");
  const [msg, setMsg] = useState(null); // {kind, text}
  // Discovery results are matched to cards by company: search results never carry contact data,
  // and discovery results use the Mongo _id (not the RemoteOK job_id).
  const [contacts, setContacts] = useState(loadContacts);

  useEffect(() => {
    getHealth()
      .then((h) => setHealth({ state: "up", text: `Backend online – v${h.version}` }))
      .catch(() => setHealth({ state: "down", text: "Backend offline" }));
  }, []);

  async function runSearch(term) {
    const k = term.trim();
    if (k.length < 2) return setMsg({ kind: "err", text: "Enter at least 2 characters to search." });
    setMsg(null); setBusy("search");
    try {
      const data = await searchJobs(k);
      setKeyword(data.keyword_searched || k);
      setJobs(data.results || []);
      setSearched(true);
    } catch (err) {
      setMsg({ kind: "err", text: err.message });
    } finally {
      setBusy(null);
    }
  }

  async function runDiscover() {
    setMsg({ kind: "info", text: "Looking through company websites for public contact info. This can take a minute…" });
    setBusy("discover");
    try {
      const d = await discoverContacts(limit);
      const next = { ...contacts };
      (d.results || []).forEach((r) => {
        next[ck(r.company)] = {
          company_website: r.company_website, contact_page_url: r.contact_page_url,
          recruiter_email: r.recruiter_email, contact_status: r.contact_status,
        };
      });
      setContacts(next);
      try { localStorage.setItem(STORE, JSON.stringify(next)); } catch { /* storage unavailable */ }
      const visible = new Set(jobs.map((j) => ck(j.company)));
      const onScreen = (d.results || []).filter((r) => visible.has(ck(r.company))).length;
      setMsg(
        d.jobs_processed === 0
          ? { kind: "ok", text: "Nothing to process: every saved job has already been checked." }
          : { kind: d.success ? "ok" : "err",
              text: `Processed ${d.jobs_processed} job${d.jobs_processed === 1 ? "" : "s"}, found ${d.emails_found} public email${d.emails_found === 1 ? "" : "s"}. ${onScreen} matched jobs shown below.` }
      );
    } catch (err) {
      setMsg({ kind: "err", text: err.message });
    } finally {
      setBusy(null);
    }
  }

  const list = jobs.map((j) => ({ ...j, ...(contacts[ck(j.company)] || {}) }));
  const found = list.filter((j) => j.contact_status === "found").length;
  const loadingSearch = busy === "search";

  return (
    <main>
      <section className="container dash-head">
        <div className="status-line"><span className={`dot ${health.state === "checking" ? "" : health.state}`} /><span>{health.text}</span></div>
        <h1>Search remote jobs</h1>
        <form className="searchbar" role="search" onSubmit={(e) => { e.preventDefault(); runSearch(input); }}>
          <input type="search" value={input} onChange={(e) => setInput(e.target.value)} maxLength={100}
            placeholder="Search for jobs, skills or roles..." aria-label="Search jobs" autoComplete="off" autoFocus />
          <button className="btn primary" type="submit" disabled={!!busy}>{loadingSearch ? <><Spin />Searching</> : "Search"}</button>
        </form>
        <div className="examples">Try:{" "}
          {EXAMPLES.map((x) => (
            <button key={x} className="chip" disabled={!!busy} onClick={() => { setInput(x); runSearch(x); }}>{x}</button>
          ))}
        </div>
      </section>

      <section className="container">
        <div className="discover">
          <div>
            <h3>Contact discovery</h3>
            <p>Checks company websites for publicly listed recruiting or HR emails. It processes saved jobs that haven't been checked yet, and never sends email.</p>
          </div>
          <div className="d-actions">
            <label className="sel">Jobs per run
              <select value={limit} onChange={(e) => setLimit(e.target.value)} disabled={!!busy}>
                <option>10</option><option>25</option><option>50</option>
              </select>
            </label>
            <button className="btn dark" type="button" onClick={runDiscover} disabled={!!busy}>
              {busy === "discover" ? <><Spin />Discovering</> : "Discover Contacts"}
            </button>
          </div>
        </div>

        <div aria-live="polite">
          {msg && <div className={`note ${msg.kind}`} role={msg.kind === "err" ? "alert" : "status"}>{msg.text}</div>}
        </div>

        {searched && jobs.length > 0 && !loadingSearch && (
          <div className="meta">
            <span>{list.length} job{list.length === 1 ? "" : "s"} for “{keyword}”</span>
            <span>{found} with a public email</span>
          </div>
        )}

        {loadingSearch ? (
          <div className="cards">
            {Array.from({ length: 6 }, (_, i) => (
              <div className="job" key={i}>
                <div className="sk" style={{ height: 20, width: "70%" }} />
                <div className="sk" style={{ height: 14, width: "45%" }} />
                <div className="sk" style={{ height: 22, width: "60%" }} />
                <div className="sk" style={{ height: 60 }} />
                <div className="sk" style={{ height: 38 }} />
              </div>
            ))}
          </div>
        ) : !searched ? (
          <div className="empty"><h3>Start with a keyword</h3><p>Search for a role or skill above, for example “Python Developer”. Results will appear here.</p></div>
        ) : jobs.length === 0 ? (
          <div className="empty"><h3>No jobs found for “{keyword}”</h3><p>Try a single skill or a broader title, like “python” or “designer”.</p></div>
        ) : (
          <div className="cards">{list.map((j) => <JobCard key={j.job_id} job={j} />)}</div>
        )}
      </section>
    </main>
  );
}
