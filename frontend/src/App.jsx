import { useEffect, useState } from "react";
import Landing from "./Landing.jsx";
import Dashboard from "./Dashboard.jsx";

const useHash = () => {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const on = () => setHash(window.location.hash);
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return hash;
};

export default function App() {
  const hash = useHash();
  const dash = hash.startsWith("#/app");

  useEffect(() => {
    if (!dash && /^#(features|how|home)$/.test(hash)) document.getElementById(hash.slice(1))?.scrollIntoView();
    else window.scrollTo(0, 0);
  }, [hash, dash]);

  return (
    <>
      <header className="nav">
        <div className="container nav-in">
          <a className="brand" href="#/"><span className="logo">O</span>Openings</a>
          <nav className="links">
            {dash ? (
              <>
                <a href="#/">Home</a>
                <a href="#/" className="hide-m">Features</a>
              </>
            ) : (
              <>
                <a href="#home">Home</a>
                <a href="#features" className="hide-m">Features</a>
                <a href="#how" className="hide-m">How It Works</a>
              </>
            )}
            <a className="btn primary" href="#/app">Find Jobs</a>
          </nav>
        </div>
      </header>

      {dash ? <Dashboard /> : <Landing />}

      <footer className="footer">
        <div className="container">
          <span>Openings – public listings and public contact info only.</span>
          <span className="muted">Uses RemoteOK's public API.</span>
        </div>
      </footer>
    </>
  );
}
