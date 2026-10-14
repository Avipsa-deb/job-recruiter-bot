import { STATUS, safeUrl, fmtDate, None, Row } from "./JobCard.jsx";

export default function JobDetails({ jobId, jobs, contacts }) {
  const base = jobs.find((j) => String(j.job_id) === String(jobId));

  if (!base) {
    return (
      <main className="container">
        <a className="btn ghost back" href="#/app"><span className="ms">arrow_back</span>Back to results</a>
        <div className="empty">
          <h3>This job isn't loaded</h3>
          <p>Job details come from your latest search. Run the search again to bring it back.</p>
        </div>
      </main>
    );
  }

  const j = { ...base, ...(contacts[String(base.company || "").trim().toLowerCase()] || {}) };
  const [label, cls] = STATUS[j.contact_status] || [j.contact_status || "Not checked", ""];
  const site = j.company_website && safeUrl(j.company_website);
  const page = j.contact_page_url && safeUrl(j.contact_page_url);
  const apply = j.apply_url && safeUrl(j.apply_url);

  return (
    <main className="container">
      <a className="btn ghost back" href="#/app"><span className="ms">arrow_back</span>Back to results</a>

      <section className="detail glass">
        <div className="detail-co">
          <div className="co-logo" aria-hidden="true">{(j.company || "?").trim().charAt(0).toUpperCase()}</div>
          <div><div style={{ fontWeight: 600 }}>{j.company || "Company not listed"}</div><span className={`badge ${cls}`}>{label}</span></div>
        </div>
        <h1>{j.title}</h1>
        <div className="facts">
          <span className="fact"><span className="ms" style={{ fontSize: 16 }}>location_on</span>{j.location || "Location not specified"}</span>
          {j.posted_at && <span className="fact"><span className="ms" style={{ fontSize: 16 }}>calendar_today</span>Posted {fmtDate(j.posted_at)}</span>}
        </div>
        {j.tags?.length > 0 && <div className="tags">{j.tags.map((t) => <span className="tag" key={t}>{t}</span>)}</div>}
      </section>

      <div className="detail-grid">
        <section className="panel glass">
          <h2>Public contact information</h2>
          <dl className="contact">
            <Row k="Email">{j.recruiter_email ? <a href={`mailto:${j.recruiter_email}`}>{j.recruiter_email}</a> : <None />}</Row>
            <Row k="Website">{site ? <a href={site} target="_blank" rel="noopener noreferrer">{j.company_website}</a> : <None />}</Row>
            <Row k="Contact page">{page ? <a href={page} target="_blank" rel="noopener noreferrer">{j.contact_page_url}</a> : <None />}</Row>
          </dl>
          {j.contact_status === "not_attempted" && <p className="apply-note">Contacts haven't been checked yet. Use “Discover Contacts” on the search page.</p>}
        </section>

        <aside className="panel glass">
          <h2>Apply</h2>
          {apply
            ? <a className="btn primary lg" style={{ width: "100%" }} href={apply} target="_blank" rel="noopener noreferrer">Apply on Original Website <span className="ms">open_in_new</span></a>
            : <p className="muted">No application link was provided for this listing.</p>}
          <p className="apply-note">You apply directly on the original listing. Career Compass never sends applications or emails for you.</p>
        </aside>
      </div>
    </main>
  );
}
