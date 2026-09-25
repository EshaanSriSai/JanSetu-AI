import React, { useEffect, useState } from "react";
import { signInAnonymously } from "firebase/auth";

const API = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const samples = [
  "మా గ్రామంలో మూడు నెలలుగా తాగునీరు సరిగ్గా రావడం లేదు. ప్రజలు చాలా ఇబ్బంది పడుతున్నారు.",
  "There are large potholes on the main road near our village school.",
  "हमारे इलाके में सरकारी अस्पताल में डॉक्टर उपलब्ध नहीं हैं।",
];

async function tokenFor(auth) {
  if (!auth) return null;
  if (!auth.currentUser) await signInAnonymously(auth);
  return auth.currentUser?.getIdToken();
}

export default function App({ auth, firebaseReady }) {
  const [message, setMessage] = useState("");
  const [source, setSource] = useState("text");
  const [result, setResult] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function api(path, options = {}) {
    const token = await tokenFor(auth);
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(`${API}${path}`, { ...options, headers });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  async function refreshDashboard() {
    try {
      const [d, r] = await Promise.all([
        api("/dashboard"),
        api("/recommendations"),
      ]);
      setDashboard(d);
      setRecommendations(r.recommendations || []);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    if (firebaseReady) refreshDashboard();
  }, [firebaseReady]);

  async function submit(e) {
    e.preventDefault();
    if (!message.trim()) return;
    setBusy(true);
    setError("");
    try {
      const data = await api("/analyze", {
        method: "POST",
        body: JSON.stringify({ message, source }),
      });
      setResult(data.complaint);
      setMessage("");
      refreshDashboard();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <div>
          <div className="eyebrow">DIGITAL PUBLIC GOOD • INDIA</div>
          <h1>JanSetu <span>AI</span></h1>
          <p>Turning citizen voices into actionable infrastructure intelligence.</p>
        </div>
        <div className="status">
          <span className="dot" />
          {firebaseReady ? "Authenticated session" : "Firebase setup required"}
        </div>
      </header>

      <main>
        <section className="grid">
          <div className="card submit-card">
            <div className="card-title">Report a civic issue</div>
            <p className="muted">Write in English, Telugu, Hindi, or another language.</p>

            <div className="samples">
              {samples.map((s) => (
                <button key={s} onClick={() => setMessage(s)}>{s.slice(0, 34)}…</button>
              ))}
            </div>

            <form onSubmit={submit}>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Describe the problem in your own words..."
                rows="7"
              />
              <div className="form-row">
                <select value={source} onChange={(e) => setSource(e.target.value)}>
                  <option value="text">Text</option>
                  <option value="whatsapp">Messaging</option>
                  <option value="voice">Voice transcript</option>
                </select>
                <button className="primary" disabled={busy || !firebaseReady}>
                  {busy ? "Analysing…" : "Analyse & Submit"}
                </button>
              </div>
            </form>

            {!firebaseReady && (
              <div className="warning">
                Add the Firebase web-app values to <code>frontend/.env</code> and enable Anonymous Authentication.
              </div>
            )}
            {error && <div className="error">{error}</div>}
          </div>

          <div className="card result-card">
            <div className="card-title">AI analysis</div>
            {!result ? (
              <div className="empty">Your structured citizen signal will appear here.</div>
            ) : (
              <>
                <div className="score">{result.priority_score}<small>/100</small></div>
                <div className="summary">{result.problem_summary}</div>
                <div className="chips">
                  <b>{result.category}</b>
                  <span>{result.language}</span>
                  <span>{result.location}</span>
                  <span>Severity: {result.severity}</span>
                  <span>Urgency: {result.urgency}</span>
                </div>
              </>
            )}
          </div>
        </section>

        <section className="metrics">
          <div><strong>{dashboard?.total_requests ?? "—"}</strong><span>Citizen requests</span></div>
          <div><strong>{dashboard?.average_priority ?? "—"}</strong><span>Average priority</span></div>
          <div><strong>{dashboard ? Object.keys(dashboard.category_counts).length : "—"}</strong><span>Issue categories</span></div>
        </section>

        <section className="grid lower">
          <div className="card">
            <div className="card-title">Demand hotspots</div>
            {dashboard?.hotspots?.length ? dashboard.hotspots.map((h) => (
              <div className="hotspot" key={`${h.location}-${h.category}`}>
                <div>
                  <strong>{h.location}</strong>
                  <span>{h.category} · {h.requests} requests</span>
                </div>
                <b>{h.total_priority}</b>
              </div>
            )) : <div className="empty">No hotspot data yet.</div>}
          </div>

          <div className="card">
            <div className="card-title">Recommended public projects</div>
            {recommendations.length ? recommendations.map((r) => (
              <div className="recommendation" key={`${r.location}-${r.category}`}>
                <strong>{r.location} · {r.category}</strong>
                <p>{r.recommended_project}</p>
                <small>{r.evidence_requests} evidence requests · {r.high_priority_requests} high priority</small>
              </div>
            )) : <div className="empty">Recommendations appear when location data is available.</div>}
          </div>
        </section>
      </main>

      <footer>JanSetu AI · Citizen signal → AI analysis → Firestore → hotspots → public-service priorities</footer>
    </div>
  );
}
