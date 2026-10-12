const STATUS = {
  not_attempted: ["Not checked", ""],
  no_website: ["No website found", "warn"],
  no_email_found: ["No email found", "warn"],
  found: ["Contact found", "found"],
  error: ["Check failed", "error"],
};

const safeUrl = (u) => {
  try {
    const x = new URL(/^https?:\/\//i.test(u) ? u : "https://" + u);
    return /^https?:$/.test(x.protocol) ? x.href : null;
  } catch { return null; }
};
const fmtDate = (s) => {
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d) ? s : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
};
const None = () => <span className="muted">–</span>;
const Row = ({ k, children }) => <div><dt>{k}</dt><dd>{children}</dd></div>;

export default function JobCard({ job: j }) {
  const [label, cls] = STATUS[j.contact_status] || [j.contact_status, ""];
  const site = j.company_website && safeUrl(j.company_website);
  const page = j.contact_page_url && safeUrl(j.contact_page_url);
  const apply = j.apply_url && safeUrl(j.apply_url);
  return (
    <article className="job">
      <div className="job-top">
        <div><h3>{j.title}</h3><div className="sub">{j.company}</div></div>
        <span className={`badge ${cls}`}>{label}</span>
      </div>
      <div className="sub">{j.location || "Remote"}{j.posted_at ? ` – Posted ${fmtDate(j.posted_at)}` : ""}</div>
      {j.tags?.length > 0 && <div className="tags">{j.tags.slice(0, 8).map((t) => <span className="tag" key={t}>{t}</span>)}</div>}
      <dl className="contact">
        <Row k="Email">{j.recruiter_email ? <a href={`mailto:${j.recruiter_email}`}>{j.recruiter_email}</a> : <None />}</Row>
        <Row k="Website">{site ? <a href={site} target="_blank" rel="noopener noreferrer">{j.company_website}</a> : <None />}</Row>
        <Row k="Contact page">{page ? <a href={page} target="_blank" rel="noopener noreferrer">Open page</a> : <None />}</Row>
      </dl>
      {apply && <a className="btn ghost" href={apply} target="_blank" rel="noopener noreferrer">Apply</a>}
    </article>
  );
}
