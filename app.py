"""
app.py  –  HNW Lead Intelligence Dashboard
Run: streamlit run app.py
"""

import sys
import os
import time
import math
import threading
from pathlib import Path
from queue import Queue, Empty

import streamlit as st

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="HNW Lead Intelligence",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400;500&family=Syne:wght@400;500;700;800&display=swap');

/* ── Root variables ── */
:root {
  --gold:       #C9A84C;
  --gold-light: #E8C97A;
  --gold-dim:   #8A6E2F;
  --ink:        #0D0D0D;
  --ink-soft:   #1A1A1A;
  --ink-mid:    #2C2C2C;
  --surface:    #141414;
  --surface2:   #1E1E1E;
  --surface3:   #252525;
  --border:     rgba(201,168,76,0.18);
  --text:       #E8E0D0;
  --text-dim:   #9A9080;
  --text-muted: #5A5248;
  --hot:        #E85A4F;
  --warm:       #E8A84C;
  --cold:       #4C9BE8;
  --radius:     4px;
}

/* ── Global reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; }

html, body, [data-testid="stAppViewContainer"] {
  background: var(--ink) !important;
  color: var(--text) !important;
  font-family: 'DM Mono', monospace;
}

[data-testid="stAppViewContainer"] > .main {
  background: var(--ink) !important;
  padding: 0 !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ── Hero header ── */
.hnw-hero {
  background: linear-gradient(180deg, #0A0A0A 0%, var(--ink) 100%);
  border-bottom: 1px solid var(--border);
  padding: 52px 64px 40px;
  position: relative;
  overflow: hidden;
}
.hnw-hero::before {
  content: '';
  position: absolute;
  top: -120px; left: -120px;
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(201,168,76,0.07) 0%, transparent 70%);
  pointer-events: none;
}
.hnw-hero::after {
  content: '';
  position: absolute;
  bottom: -80px; right: -80px;
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(201,168,76,0.04) 0%, transparent 70%);
  pointer-events: none;
}
.hero-eyebrow {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  font-weight: 400;
  letter-spacing: 0.3em;
  color: var(--gold);
  text-transform: uppercase;
  margin-bottom: 16px;
}
.hero-title {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(42px, 5vw, 68px);
  font-weight: 300;
  line-height: 1.05;
  color: var(--text);
  margin-bottom: 12px;
  letter-spacing: -0.02em;
}
.hero-title em {
  font-style: italic;
  color: var(--gold-light);
}
.hero-sub {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 0.08em;
  margin-top: 8px;
}

/* ── Search section ── */
.search-section {
  padding: 40px 64px;
  border-bottom: 1px solid rgba(201,168,76,0.08);
  background: var(--ink-soft);
}
.search-label {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.3em;
  color: var(--gold-dim);
  text-transform: uppercase;
  margin-bottom: 12px;
}

/* ── Streamlit input override ── */
[data-testid="stTextInput"] input {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
  font-family: 'Cormorant Garamond', serif !important;
  font-size: 22px !important;
  font-weight: 300 !important;
  padding: 16px 20px !important;
  letter-spacing: 0.02em;
  transition: border-color 0.2s;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 3px rgba(201,168,76,0.08) !important;
  outline: none !important;
}
[data-testid="stTextInput"] input::placeholder {
  color: var(--text-muted) !important;
  font-style: italic;
}
[data-testid="stTextInput"] label { display: none !important; }

/* ── Button ── */
[data-testid="stButton"] > button {
  background: var(--gold) !important;
  color: var(--ink) !important;
  border: none !important;
  border-radius: var(--radius) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  letter-spacing: 0.2em !important;
  text-transform: uppercase !important;
  padding: 16px 40px !important;
  cursor: pointer !important;
  transition: all 0.2s !important;
  width: 100%;
}
[data-testid="stButton"] > button:hover {
  background: var(--gold-light) !important;
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(201,168,76,0.25) !important;
}
[data-testid="stButton"] > button:active { transform: translateY(0); }

/* ── Pipeline progress ── */
.pipeline-wrap {
  padding: 40px 64px;
  background: var(--ink);
}
.pipeline-title {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.3em;
  color: var(--gold-dim);
  text-transform: uppercase;
  margin-bottom: 24px;
}
.pipeline-steps {
  display: flex;
  gap: 0;
  align-items: center;
  margin-bottom: 32px;
  flex-wrap: wrap;
  gap: 8px;
}
.step-pill {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  padding: 6px 14px;
  border-radius: 2px;
  border: 1px solid transparent;
}
.step-pending  { border-color: var(--text-muted); color: var(--text-muted); }
.step-active   { border-color: var(--gold); color: var(--gold); background: rgba(201,168,76,0.08); animation: pulse-step 1.5s ease-in-out infinite; }
.step-done     { border-color: var(--gold-dim); color: var(--ink); background: var(--gold-dim); }

@keyframes pulse-step {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.6; }
}

.log-console {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  height: 200px;
  overflow-y: auto;
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  line-height: 1.8;
}
.log-line { color: var(--text-dim); }
.log-line.info  { color: var(--text-dim); }
.log-line.good  { color: var(--gold); }
.log-line.warn  { color: var(--warm); }
.log-line.error { color: var(--hot); }

/* ── Stats bar ── */
.stats-bar {
  display: flex;
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 40px;
}
.stat-cell {
  flex: 1;
  background: var(--surface);
  padding: 20px 24px;
  text-align: center;
}
.stat-value {
  font-family: 'Cormorant Garamond', serif;
  font-size: 36px;
  font-weight: 300;
  color: var(--gold-light);
  line-height: 1;
  margin-bottom: 6px;
}
.stat-label {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* ── Results section ── */
.results-section { padding: 0 64px 80px; }
.results-header {
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 32px;
  padding-top: 40px;
  border-top: 1px solid var(--border);
}
.results-title {
  font-family: 'Cormorant Garamond', serif;
  font-size: 28px;
  font-weight: 300;
  color: var(--text);
  letter-spacing: -0.01em;
}
.results-count {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 0.15em;
}

/* ── Lead card ── */
.lead-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 16px;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
  position: relative;
}
.lead-card:hover {
  border-color: rgba(201,168,76,0.4);
  box-shadow: 0 4px 32px rgba(0,0,0,0.4);
}
.lead-card-accent {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
}
.accent-hot  { background: var(--hot); }
.accent-warm { background: var(--warm); }
.accent-cold { background: var(--cold); }
.accent-none { background: var(--text-muted); }

.lead-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 24px 28px 18px 28px;
  gap: 16px;
}
.lead-name {
  font-family: 'Cormorant Garamond', serif;
  font-size: 24px;
  font-weight: 400;
  color: var(--text);
  letter-spacing: -0.01em;
  line-height: 1.1;
}
.lead-title-role {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 0.1em;
  margin-top: 4px;
}
.lead-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: flex-end;
}
.badge {
  font-family: 'DM Mono', monospace;
  font-size: 8px;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 2px;
}
.badge-hot  { background: rgba(232,90,79,0.15);  color: var(--hot);  border: 1px solid rgba(232,90,79,0.3); }
.badge-warm { background: rgba(232,168,76,0.15); color: var(--warm); border: 1px solid rgba(232,168,76,0.3); }
.badge-cold { background: rgba(76,155,232,0.15); color: var(--cold); border: 1px solid rgba(76,155,232,0.3); }
.badge-cat  { background: rgba(201,168,76,0.1);  color: var(--gold); border: 1px solid var(--border); }
.badge-score { background: var(--surface3); color: var(--text-dim); border: 1px solid rgba(255,255,255,0.06); }

.lead-divider { height: 1px; background: var(--border); margin: 0 28px; }

.lead-body {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0;
}
.lead-section {
  padding: 18px 28px;
  border-right: 1px solid var(--border);
}
.lead-section:last-child { border-right: none; }

.section-label {
  font-family: 'DM Mono', monospace;
  font-size: 8px;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 10px;
}
.section-value {
  font-family: 'Cormorant Garamond', serif;
  font-size: 18px;
  font-weight: 300;
  color: var(--text);
}
.section-value.gold { color: var(--gold-light); }
.section-sub {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  color: var(--text-muted);
  margin-top: 3px;
  letter-spacing: 0.05em;
}

.lead-known-for {
  padding: 14px 28px 20px;
  font-family: 'Cormorant Garamond', serif;
  font-size: 15px;
  font-style: italic;
  color: var(--text-dim);
  line-height: 1.5;
  border-top: 1px solid var(--border);
}

.lead-footer {
  padding: 12px 28px;
  border-top: 1px solid var(--border);
  background: var(--surface2);
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}
.footer-chip {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}
.footer-chip span { color: var(--text-dim); }

/* ── Score bar ── */
.score-bar-wrap { margin-top: 8px; }
.score-bar-track {
  height: 3px;
  background: var(--surface3);
  border-radius: 2px;
  overflow: hidden;
  width: 100%;
}
.score-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 1s ease;
}

/* ── Empty state ── */
.empty-state {
  text-align: center;
  padding: 80px 40px;
  color: var(--text-muted);
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.4;
}
.empty-text {
  font-family: 'Cormorant Garamond', serif;
  font-size: 20px;
  font-style: italic;
  color: var(--text-muted);
}

/* ── Filter bar ── */
.filter-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 24px;
  align-items: center;
}
.filter-label {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.2em;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-right: 4px;
}

/* ── Streamlit selectbox / multiselect override ── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
  background: var(--surface) !important;
  border-color: var(--border) !important;
  color: var(--text) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 11px !important;
}

/* ── Spinner override ── */
[data-testid="stSpinner"] { display: none !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--gold-dim); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ── Helper functions ──────────────────────────────────────────────────────────




def score_color(score):
    if score >= 80: return "#C9A84C"
    if score >= 60: return "#E8A84C"
    if score >= 40: return "#9A9080"
    return "#5A5248"


def status_accent(status):
    return {"HOT": "hot", "WARM": "warm", "COLD": "cold"}.get(status, "none")


def status_badge_class(status):
    return {"HOT": "badge-hot", "WARM": "badge-warm", "COLD": "badge-cold"}.get(status, "badge-score")


def render_lead_card(lead, idx):
    name     = lead.get("full_name") or "Unknown"
    role     = lead.get("title") or ""
    company  = lead.get("company_name") or ""
    category = lead.get("category", "HNW_INDIVIDUAL").replace("_", " ")
    status   = lead.get("qualification_status", "WARM")
    score    = lead.get("overall_hni_score", 0) or 0
    industry = lead.get("industry", "—")
    nw_val= lead.get("net_worth")
    nw_cur=lead.get("net_worth_currency", "INR")
    nw_src   = lead.get("net_worth_source", "ESTIMATED")
    known_for = lead.get("known_for", "")
    city     = lead.get("city", "")
    country  = lead.get("country", "")
    nri      = lead.get("nri_status", "UNKNOWN")
    estate   = lead.get("estate_planning_status", "UNKNOWN")
    keyman   = lead.get("keyman_insurance_potential", "—")
    priority = lead.get("insurance_priority_type", "—")
    source_url = lead.get("source_url", "")
    conf     = lead.get("data_confidence_score", 0) or 0

    accent   = status_accent(status)
    s_color  = score_color(score)

    role_line = " · ".join(filter(None, [role, company]))

    st.markdown(f"""
    <div class="lead-card">
      <div class="lead-card-accent accent-{accent}"></div>

      <div class="lead-header">
        <div>
          <div class="lead-name">{name}</div>
          <div class="lead-title-role">{role_line or industry}</div>
        </div>
        <div class="lead-badges">
          <span class="badge {status_badge_class(status)}">{status}</span>
          <span class="badge badge-cat">{category}</span>
          <span class="badge badge-score">Score {score}</span>
        </div>
      </div>

      <div class="lead-divider"></div>

      <div class="lead-body">
        <div class="lead-section">
          <div class="section-label">Net Worth</div>
          <div class="section-value gold">{nw_val}</div>
          <div class="section-sub">{nw_src.replace("_"," ")}</div>
          <div class="score-bar-wrap">
            <div class="score-bar-track">
              <div class="score-bar-fill" style="width:{score}%; background:{s_color};"></div>
            </div>
          </div>
        </div>
        <div class="lead-section">
          <div class="section-label">Industry</div>
          <div class="section-value">{industry}</div>
          <div class="section-sub">NRI: {nri}</div>
        </div>
        <div class="lead-section">
          <div class="section-label">Insurance Priority</div>
          <div class="section-value" style="font-size:16px">{priority.replace("_"," ")}</div>
          <div class="section-sub">Keyman: {keyman} · Estate: {estate.replace("_"," ")}</div>
        </div>
      </div>

      {'<div class="lead-known-for">' + known_for + '</div>' if known_for else ''}

      <div class="lead-footer">
        <span class="footer-chip">📍 <span>{city}{", " + country if country else ""}</span></span>
        <span class="footer-chip">🎯 <span>Confidence {conf}%</span></span>
        {'<span class="footer-chip">🔗 <a href="' + source_url + '" target="_blank" style="color:var(--gold-dim);text-decoration:none;">' + source_url[:55] + ('…' if len(source_url)>55 else '') + '</a></span>' if source_url else ''}
      </div>
    </div>
    """, unsafe_allow_html=True)


def run_pipeline(city, log_queue):
    """Runs in a background thread, pushes log messages to queue."""
    try:
        from pipeline.orchestrator import HNWPipeline

        log_queue.put(("info", f"Initialising pipeline for {city}…"))
        pipeline = HNWPipeline(city=city)

        log_queue.put(("good", f"Searching for HNW profiles in {city}…"))

        # Monkey-patch logger to forward to queue
        import logging
        class QueueHandler(logging.Handler):
            def emit(self, record):
                msg = self.format(record)
                level = "good" if "✓" in msg else "warn" if "✗" in msg or "WARNING" in record.levelname else "info"
                if record.levelname == "ERROR":
                    level = "error"
                log_queue.put((level, msg[-120:]))

        root = logging.getLogger()
        qh = QueueHandler()
        root.addHandler(qh)

        leads = pipeline.run()

        root.removeHandler(qh)
        log_queue.put(("good", f"✓ Complete — {len(leads)} qualified leads found"))
        log_queue.put(("__done__", leads))

    except Exception as e:
        log_queue.put(("error", f"Pipeline error: {e}"))
        log_queue.put(("__done__", []))


# ── Session state ─────────────────────────────────────────────────────────────
if "leads"    not in st.session_state: st.session_state.leads    = []
if "running"  not in st.session_state: st.session_state.running  = False
if "logs"     not in st.session_state: st.session_state.logs     = []
if "done"     not in st.session_state: st.session_state.done     = False
if "log_q"    not in st.session_state: st.session_state.log_q    = None


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hnw-hero">
  <div class="hero-eyebrow">◆ Intelligence Platform · Private Wealth</div>
  <div class="hero-title">High Net Worth<br><em>Lead Discovery</em></div>
  <div class="hero-sub">POWERED BY TAVILY · AZURE GPT-4 · MULTI-SCRAPER CHAIN · MONGODB</div>
</div>
""", unsafe_allow_html=True)


# ── Search ────────────────────────────────────────────────────────────────────
st.markdown('<div class="search-section">', unsafe_allow_html=True)
st.markdown('<div class="search-label">◆ Target Location</div>', unsafe_allow_html=True)

col_input, col_btn = st.columns([4, 1])
with col_input:
    city_input = st.text_input(
        "city",
        placeholder="Enter city — Bangalore, Mumbai, Dubai, London…",
        label_visibility="hidden",
        key="city_field",
        disabled=st.session_state.running,
    )
with col_btn:
    st.markdown("<div style='padding-top:2px'>", unsafe_allow_html=True)
    search_clicked = st.button(
        "◆ DISCOVER LEADS",
        disabled=st.session_state.running or not city_input,
        key="search_btn",
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# ── Trigger pipeline ──────────────────────────────────────────────────────────
if search_clicked and city_input and not st.session_state.running:
    st.session_state.running = True
    st.session_state.done    = False
    st.session_state.leads   = []
    st.session_state.logs    = []
    q = Queue()
    st.session_state.log_q   = q
    t = threading.Thread(target=run_pipeline, args=(city_input.strip(), q), daemon=True)
    t.start()
    st.rerun()


# ── Pipeline progress display ─────────────────────────────────────────────────
STEPS = ["SEARCH", "SCRAPE", "CHUNK", "ANALYSE", "DEDUPLICATE", "STORE"]

if st.session_state.running or (st.session_state.done and not st.session_state.leads):

    st.markdown('<div class="pipeline-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="pipeline-title">◆ Pipeline Status</div>', unsafe_allow_html=True)

    # Drain the queue
    if st.session_state.log_q:
        q = st.session_state.log_q
        while True:
            try:
                item = q.get_nowait()
                if item[0] == "__done__":
                    st.session_state.leads   = item[1]
                    st.session_state.running = False
                    st.session_state.done    = True
                    st.session_state.log_q   = None
                    break
                else:
                    st.session_state.logs.append(item)
            except Empty:
                break

    # Infer step from logs
    log_text = " ".join(m for _, m in st.session_state.logs).lower()
    if "store" in log_text or "upsert" in log_text or "complete" in log_text:
        active_step = 5
    elif "dedup" in log_text or "unique leads" in log_text:
        active_step = 4
    elif "analysis" in log_text or "chunk" in log_text:
        active_step = 3
    elif "chunk" in log_text:
        active_step = 2
    elif "scrape" in log_text or "attempt" in log_text:
        active_step = 1
    elif "search" in log_text or "url" in log_text:
        active_step = 0
    else:
        active_step = 0

    # Render step pills
    pills_html = '<div class="pipeline-steps">'
    for i, step in enumerate(STEPS):
        if i < active_step:
            cls = "step-done"
        elif i == active_step and st.session_state.running:
            cls = "step-active"
        else:
            cls = "step-pending"
        pills_html += f'<span class="step-pill {cls}">{step}</span>'
        if i < len(STEPS) - 1:
            pills_html += '<span style="color:var(--text-muted);font-size:10px;padding:0 4px">→</span>'
    pills_html += "</div>"
    st.markdown(pills_html, unsafe_allow_html=True)

    # Log console
    log_lines = "".join(
        f'<div class="log-line {lvl}">{msg}</div>'
        for lvl, msg in st.session_state.logs[-40:]
    )
    st.markdown(
        f'<div class="log-console" id="logbox">{log_lines}'
        '<script>var b=document.getElementById("logbox");if(b)b.scrollTop=b.scrollHeight;</script>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.running:
        time.sleep(1.2)
        st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.done or st.session_state.leads:
    leads = st.session_state.leads

    if not leads:
        st.markdown("""
        <div class="results-section">
          <div class="empty-state">
            <div class="empty-icon">◇</div>
            <div class="empty-text">No qualifying leads found for this location.</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Stats
        hot_count  = sum(1 for l in leads if l.get("qualification_status") == "HOT")
        warm_count = sum(1 for l in leads if l.get("qualification_status") == "WARM")
        avg_score  = int(sum(l.get("overall_hni_score", 0) or 0 for l in leads) / len(leads))

        st.markdown(f"""
        <div class="results-section">
          <div style="padding-top:40px;">
            <div class="stats-bar">
              <div class="stat-cell">
                <div class="stat-value">{len(leads)}</div>
                <div class="stat-label">Total Leads</div>
              </div>
              <div class="stat-cell">
                <div class="stat-value" style="color:var(--hot)">{hot_count}</div>
                <div class="stat-label">Hot Leads</div>
              </div>
              <div class="stat-cell">
                <div class="stat-value" style="color:var(--warm)">{warm_count}</div>
                <div class="stat-label">Warm Leads</div>
              </div>
              <div class="stat-cell">
                <div class="stat-value">{avg_score}</div>
                <div class="stat-label">Avg HNI Score</div>
              </div>
            </div>
          </div>
        """, unsafe_allow_html=True)

        # Filter controls
        st.markdown('<div style="margin-bottom:8px">', unsafe_allow_html=True)
        fcol1, fcol2, fcol3 = st.columns([1, 1, 2])
        with fcol1:
            status_filter = st.selectbox(
                "Status",
                ["All", "HOT", "WARM", "COLD"],
                label_visibility="visible",
                key="filter_status",
            )
        with fcol2:
            sort_by = st.selectbox(
                "Sort by",
                ["HNI Score ↓", "Net Worth ↓", "Name A–Z"],
                label_visibility="visible",
                key="sort_by",
            )
        with fcol3:
            categories = sorted({l.get("category", "").replace("_", " ") for l in leads if l.get("category")})
            cat_filter = st.multiselect("Category", categories, key="filter_cat")
        st.markdown("</div>", unsafe_allow_html=True)

        # Apply filters
        filtered = leads
        if status_filter != "All":
            filtered = [l for l in filtered if l.get("qualification_status") == status_filter]
        if cat_filter:
            filtered = [l for l in filtered if l.get("category", "").replace("_", " ") in cat_filter]

        # Sort
        if sort_by == "HNI Score ↓":
            filtered = sorted(filtered, key=lambda l: l.get("overall_hni_score", 0) or 0, reverse=True)
        else:
            filtered = sorted(filtered, key=lambda l: l.get("full_name", "") or "")

        st.markdown(f"""
          <div class="results-header">
            <div class="results-title">Qualified Leads</div>
            <div class="results-count">{len(filtered)} of {len(leads)} shown</div>
          </div>
        """, unsafe_allow_html=True)

        for i, lead in enumerate(filtered):
            render_lead_card(lead, i)

        st.markdown("</div>", unsafe_allow_html=True)