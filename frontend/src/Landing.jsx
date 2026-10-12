const Bar = () => <div className="pv-bar"><i /><i /><i /></div>;
const Search = () => <div className="pv-search"><span /><b>Search</b></div>;
const Chips = ({ n }) => <div className="chips">{Array.from({ length: n }, (_, i) => <u key={i} />)}</div>;
const Card = ({ a, b, n, foot }) => (
  <div className="pv-card">
    <div className={`l ${a}`} /><div className={`l ${b} s`} /><Chips n={n} />
    {foot && <div className="pv-foot"><em className={foot.ok ? "ok" : ""}>{foot.text}</em><div className="l w30" /></div>}
  </div>
);

const FEATURES = [
  ["Keyword job search", "Type a role or skill. The backend matches it against titles, tags and company names."],
  ["Real RemoteOK listings", "Jobs come from RemoteOK's public API, with a direct apply link on every card."],
  ["Public contact discovery", "Visits company websites and looks for a recruiting or HR email on public pages."],
  ["Saved in MongoDB", "Jobs are stored once, duplicates are skipped by RemoteOK ID, and contact results are written back."],
];
const STEPS = [
  ["Search", "Enter a keyword such as Python Developer."],
  ["Discover jobs", "Matching listings are fetched and saved."],
  ["Discover contacts", "Public company pages are checked for contact info."],
  ["Apply", "You review everything and apply yourself."],
];

export default function Landing() {
  return (
    <main>
      <section id="home" className="hero container">
        <div className="hero-text">
          <h1>Find remote jobs, and the people behind them.</h1>
          <p className="lead">Search live RemoteOK listings, then look up the publicly listed contact details on each company's own website. Everything in one place, nothing sent on your behalf.</p>
          <div className="cta-row">
            <a className="btn primary lg" href="#/app">Start Searching</a>
            <a className="btn ghost lg" href="#how">How It Works</a>
          </div>
        </div>
        <div className="preview" aria-hidden="true">
          <Bar /><Search />
          <Card a="w60" b="w40" n={3} foot={{ ok: true, text: "found" }} />
          <Card a="w70" b="w30" n={2} foot={{ text: "not attempted" }} />
        </div>
      </section>

      <section id="features" className="section container">
        <h2>What it does</h2>
        <div className="grid4">
          {FEATURES.map(([t, d]) => <article className="feat" key={t}><h3>{t}</h3><p>{d}</p></article>)}
        </div>
      </section>

      <section id="how" className="section container">
        <h2>How it works</h2>
        <ol className="steps">
          {STEPS.map(([t, d], i) => <li key={t}><span>{i + 1}</span><h3>{t}</h3><p>{d}</p></li>)}
        </ol>
      </section>

      <section className="section container">
        <h2>The dashboard</h2>
        <p className="muted narrow">Results appear as cards: title, company, location, tags, posted date, apply link, and a contact status that updates after discovery.</p>
        <div className="preview wide" aria-hidden="true">
          <Bar /><Search />
          <div className="pv-grid">
            <Card a="w60" b="w40" n={2} /><Card a="w70" b="w30" n={3} /><Card a="w50" b="w40" n={1} />
          </div>
        </div>
      </section>

      <section className="section container">
        <div className="principles">
          <h2>Principles</h2>
          <ul>
            <li>Only public job listings and public company contact information.</li>
            <li>No LinkedIn scraping, no LinkedIn login or automation.</li>
            <li>No automatic emailing. You decide who to contact and how.</li>
          </ul>
        </div>
      </section>

      <section className="section container final">
        <h2>Find your next opportunity</h2>
        <a className="btn primary lg" href="#/app">Find Jobs</a>
      </section>
    </main>
  );
}
