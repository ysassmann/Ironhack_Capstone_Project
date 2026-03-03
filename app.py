"""
EvidenceAI v0.1 — Streamlit App
"""

import streamlit as st
import time, os, sys, json, re
from datetime import datetime

st.set_page_config(
    page_title="EvidenceAI v0.1",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

HISTORY_FILE       = "./research_history.json"
CONTEXT_CHAR_LIMIT = 3000

# ══════════════════════════════════════════════════════════════════════════════
# CSS — aggressive overrides to beat Streamlit defaults
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg:        #0e1117;
    --surface:   #161b27;
    --surface2:  #1e2535;
    --surface3:  #252d40;
    --border:    #2a3347;
    --border2:   #3a4560;
    --text:      #f0f4ff;
    --text-sec:  #8b9abf;
    --text-mute: #5a6a8a;
    --accent:    #4f8ef7;
    --acc-dim:   #2a4a8a;
    --acc-glow:  rgba(79,142,247,0.15);
    --green:     #34d399;
    --red:       #f87171;
    --amber:     #fbbf24;
    --r:         8px;
    --rs:        5px;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

[data-testid="collapsedControl"] { visibility: visible !important; }
.block-container { padding-top: 2rem !important; padding-bottom: 4rem !important; max-width: 860px !important; }

/* ── Force white text in main ── */
.main p, .main li, .main span, .main h1, .main h2, .main h3, .main h4,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] *,
.stMarkdown, .stMarkdown * { color: var(--text) !important; }
[data-testid="stMarkdownContainer"] strong { color: #fff !important; font-weight: 600 !important; }
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 { color: #fff !important; font-weight: 600 !important; }
[data-testid="stMarkdownContainer"] code {
    background: var(--surface3) !important; color: var(--accent) !important;
    padding: .15em .4em !important; border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: .83em !important;
}
[data-testid="stMarkdownContainer"] ul li::marker,
[data-testid="stMarkdownContainer"] ol li::marker { color: var(--accent) !important; }

/* ══ SIDEBAR ══ */
[data-testid="stSidebar"] { background-color: var(--surface) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] > div { padding: 1.2rem 0.9rem !important; }
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] input {
    background: var(--surface2) !important; color: var(--text) !important;
    border: 1px solid var(--border2) !important; border-radius: var(--rs) !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: .8rem !important;
    padding: .4rem .65rem !important;
}
[data-testid="stSidebar"] hr { border-color: var(--border) !important; margin: .6rem 0 !important; }

/* ── Sidebar buttons: FORCE small mono single-line ── */
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] .stButton button,
section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    background: var(--surface2) !important;
    color: var(--text-sec) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--rs) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem !important;
    font-weight: 400 !important;
    line-height: 1.2 !important;
    padding: 0.3rem 0.55rem !important;
    width: 100% !important;
    text-align: left !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 100% !important;
    display: block !important;
    margin-bottom: 3px !important;
    transition: all .12s !important;
    min-height: unset !important;
    height: auto !important;
}
section[data-testid="stSidebar"] button:hover,
section[data-testid="stSidebar"] .stButton button:hover {
    background: var(--surface3) !important;
    border-color: var(--accent) !important;
    color: var(--text) !important;
}
/* Override paragraph inside button */
section[data-testid="stSidebar"] button p,
section[data-testid="stSidebar"] .stButton button p {
    font-size: 0.65rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    color: inherit !important;
    margin: 0 !important;
    padding: 0 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.2 !important;
}

/* ══ MAIN BUTTONS ══ */
.stButton > button {
    background: var(--accent) !important; color: #fff !important;
    border: none !important; border-radius: var(--rs) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: .78rem !important; font-weight: 600 !important;
    padding: .48rem 1.1rem !important; transition: all .15s !important;
    letter-spacing: .01em !important;
}
.stButton > button:hover { background: #6aa0f9 !important; box-shadow: 0 4px 14px rgba(79,142,247,.3) !important; }
.stButton > button:disabled { background: var(--surface3) !important; color: var(--text-mute) !important; box-shadow: none !important; }

/* ══ TEXTAREA ══ */
.stTextArea textarea {
    background: var(--surface) !important; color: var(--text) !important;
    border: 1px solid var(--border2) !important; border-radius: var(--r) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: .95rem !important; line-height: 1.65 !important;
    padding: .85rem 1rem !important; caret-color: var(--accent) !important;
}
.stTextArea textarea:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--acc-glow) !important; outline: none !important; }
.stTextArea textarea::placeholder { color: var(--text-mute) !important; }

/* ══ EXPANDER ══ */
[data-testid="stExpander"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: var(--rs) !important; margin-bottom: .3rem !important; }
[data-testid="stExpander"] summary { color: var(--text-sec) !important; font-size: .8rem !important; font-weight: 500 !important; padding: .5rem .7rem !important; }
[data-testid="stExpander"] summary:hover { color: var(--text) !important; }
[data-testid="stExpander"] [data-testid="stExpanderDetails"] { background: var(--surface2) !important; border-top: 1px solid var(--border) !important; padding: .7rem !important; }
[data-testid="stExpander"] p, [data-testid="stExpander"] span,
[data-testid="stExpander"] code, [data-testid="stExpander"] pre { color: var(--text-sec) !important; }

/* ══ DOWNLOAD BUTTON ══ */
.stDownloadButton > button {
    background: transparent !important; color: var(--text-sec) !important;
    border: 1px solid var(--border2) !important; border-radius: var(--rs) !important;
    font-size: .74rem !important; font-weight: 500 !important; padding: .35rem .85rem !important;
}
.stDownloadButton > button:hover { border-color: var(--accent) !important; color: var(--accent) !important; background: var(--acc-glow) !important; transform: none !important; box-shadow: none !important; }

/* ══ ALERTS ══ */
.stSuccess { background: rgba(52,211,153,.1) !important; color: var(--green) !important; border-color: var(--green) !important; }
.stError   { background: rgba(248,113,113,.1) !important; color: var(--red) !important;   border-color: var(--red) !important; }

/* ══ SCROLLBAR ══ */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

/* ══ CUSTOM COMPONENTS ══ */
.ev-header { display:flex; align-items:baseline; gap:.7rem; padding-bottom:1.1rem; border-bottom:1px solid var(--border); margin-bottom:1.8rem; }
.ev-title  { font-size:1.5rem; font-weight:700; color:#fff; letter-spacing:-.03em; }
.ev-ver    { font-family:'JetBrains Mono',monospace; font-size:.67rem; color:var(--accent); background:var(--acc-glow); border:1px solid var(--acc-dim); padding:.1rem .42rem; border-radius:20px; }
.ev-sub    { font-size:.79rem; color:var(--text-mute); margin-left:auto; }

.runtime-banner {
    display:flex; align-items:center; gap:.6rem;
    background:var(--surface2); border:1px solid var(--border2);
    border-left:3px solid var(--amber); border-radius:var(--rs);
    padding:.55rem .9rem; margin-top:.75rem;
    font-size:.82rem; color:var(--text-sec);
}
.runtime-banner b { color:var(--amber); }

.q-bubble { background:var(--surface2); border:1px solid var(--border2); border-left:3px solid var(--accent); border-radius:var(--r); padding:.85rem 1.1rem; margin-top:1.5rem; }
.q-label  { font-family:'JetBrains Mono',monospace; font-size:.59rem; letter-spacing:.12em; color:var(--accent); text-transform:uppercase; margin-bottom:.3rem; display:flex; align-items:center; gap:.45rem; }
.q-text   { font-size:.94rem; color:var(--text) !important; line-height:1.5; font-weight:500; }
.fu-badge { background:rgba(251,191,36,.1); color:var(--amber); border:1px solid rgba(251,191,36,.3); font-family:'JetBrains Mono',monospace; font-size:.57rem; padding:.08rem .38rem; border-radius:20px; }

.a-card   { background:var(--surface); border:1px solid var(--border); border-top:none; border-radius:0 0 var(--r) var(--r); padding:1.2rem 1.4rem; margin-bottom:.4rem; }
.a-metrics{ display:flex; flex-wrap:wrap; gap:.9rem; padding-bottom:.8rem; border-bottom:1px solid var(--border); margin-bottom:.95rem; }
.a-metric { font-family:'JetBrains Mono',monospace; font-size:.65rem; color:var(--text-mute); }
.a-metric b { color:var(--text-sec); font-weight:500; }

.tc-badge { display:inline-block; font-family:'JetBrains Mono',monospace; font-size:.63rem; padding:.09rem .42rem; border-radius:4px; margin:.08rem .12rem; }
.tc-num   { background:var(--surface3); color:var(--text-mute); }
.tc-name  { background:var(--acc-glow); color:var(--accent); border:1px solid var(--acc-dim); }

.fu-section { background:var(--surface); border:1px solid var(--border); border-top:2px solid var(--accent); border-radius:0 0 var(--r) var(--r); padding:1rem 1.2rem; margin-top:1.8rem; }
.fu-label   { font-family:'JetBrains Mono',monospace; font-size:.62rem; letter-spacing:.1em; text-transform:uppercase; color:var(--accent); margin-bottom:.5rem; }
.ctx-prev   { background:var(--surface2); border:1px solid var(--border); border-left:2px solid var(--acc-dim); border-radius:var(--rs); padding:.48rem .72rem; font-family:'JetBrains Mono',monospace; font-size:.67rem; color:var(--text-mute); margin-bottom:.7rem; line-height:1.5; }

.empty-state { text-align:center; padding:3rem 2rem; }
.empty-icon  { font-size:2rem; margin-bottom:.8rem; display:block; opacity:.3; }
.empty-title { font-size:1.1rem; font-weight:600; color:var(--text); margin-bottom:.35rem; }
.empty-desc  { font-size:.84rem; color:var(--text-mute); max-width:400px; margin:0 auto 1.6rem; line-height:1.6; }
.info-box    { background:var(--acc-glow); border:1px solid var(--acc-dim); border-radius:var(--rs); padding:.65rem .95rem; font-size:.81rem; color:var(--accent); font-weight:500; }

.sb-title { font-size:.95rem; font-weight:700; color:#fff; letter-spacing:-.02em; }
.sb-sub   { font-family:'JetBrains Mono',monospace; font-size:.57rem; color:var(--text-mute); letter-spacing:.1em; text-transform:uppercase; margin-top:.1rem; margin-bottom:1rem; }
.sb-lbl   { font-family:'JetBrains Mono',monospace; font-size:.57rem; letter-spacing:.1em; text-transform:uppercase; color:var(--text-mute); margin-bottom:.38rem; margin-top:.1rem; }
.sb-meta  { font-family:'JetBrains Mono',monospace; font-size:.59rem; color:var(--text-mute); line-height:1.85; margin-top:.75rem; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# REPORTLAB PDF EXPORT
# ══════════════════════════════════════════════════════════════════════════════
def generate_pdf(session: dict) -> bytes:
    import io as _io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

    buf = _io.BytesIO()
    W, H = A4

    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#0e1117"))
        canvas.rect(0, H - 1.1*cm, W, 1.1*cm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor("#4f8ef7"))
        canvas.drawString(1.8*cm, H - 0.72*cm, "EvidenceAI v0.1")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#8b9abf"))
        canvas.drawRightString(W - 1.8*cm, H - 0.72*cm, session.get("created", ""))
        canvas.setFillColor(colors.HexColor("#161b27"))
        canvas.rect(0, 0, W, 0.85*cm, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#5a6a8a"))
        canvas.drawCentredString(W/2, 0.3*cm, f"Page {doc.page}  ·  GIZ Project Evaluation Database")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.8*cm, bottomMargin=1.5*cm)

    ink     = colors.HexColor("#1a1a2e")
    accent  = colors.HexColor("#4f8ef7")
    muted   = colors.HexColor("#5a6a8a")
    mid     = colors.HexColor("#3a4a6a")
    amber   = colors.HexColor("#b45309")

    s_doctitle = ParagraphStyle("dt", fontName="Helvetica-Bold", fontSize=20, textColor=colors.HexColor("#0e1117"), spaceAfter=4, leading=24)
    s_docsub   = ParagraphStyle("ds", fontName="Helvetica",      fontSize=8,  textColor=muted, spaceAfter=14, leading=12)
    s_qlabel   = ParagraphStyle("ql", fontName="Helvetica-Bold", fontSize=6.5,textColor=accent, spaceBefore=16, spaceAfter=3, leading=9, leftIndent=6)
    s_qtext    = ParagraphStyle("qt", fontName="Helvetica-Bold", fontSize=10.5,textColor=ink, leftIndent=6, spaceAfter=3, leading=15)
    s_meta     = ParagraphStyle("qm", fontName="Helvetica",      fontSize=7,  textColor=muted, spaceAfter=8,  leading=10)
    s_body     = ParagraphStyle("bo", fontName="Helvetica",      fontSize=9.5,textColor=ink, leading=14, spaceAfter=5)
    s_h1       = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=12, textColor=ink, spaceBefore=12, spaceAfter=3, leading=16)
    s_h2       = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5,textColor=ink, spaceBefore=9, spaceAfter=3, leading=14)
    s_h3       = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=9,  textColor=mid, spaceBefore=7, spaceAfter=2, leading=12)
    s_bullet   = ParagraphStyle("bu", fontName="Helvetica",      fontSize=9.5,textColor=ink, leading=13, leftIndent=14, bulletIndent=5, spaceAfter=3)
    s_fu       = ParagraphStyle("fu", fontName="Helvetica-Oblique", fontSize=7, textColor=amber, leftIndent=6, spaceAfter=2)

    def md_to_flowables(text):
        out = []
        text = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        for line in text.split("\n"):
            s = line.strip()
            if not s:
                out.append(Spacer(1, 3)); continue
            s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
            s = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', s)
            s = re.sub(r'`(.+?)`',       r'<font face="Courier" size="8">\1</font>', s)
            if s.startswith("### "):         out.append(Paragraph(s[4:], s_h3))
            elif s.startswith("## "):        out.append(Paragraph(s[3:], s_h2))
            elif s.startswith("# "):         out.append(Paragraph(s[2:], s_h1))
            elif s.startswith("- ") or s.startswith("* ") or s.startswith("&bull; "):
                out.append(Paragraph(f"• {s[2:]}", s_bullet))
            elif s.startswith("**") and s.endswith("**") and len(s) > 4:
                out.append(Paragraph(s[2:-2], s_h2))
            else:
                out.append(Paragraph(s, s_body))
        return out

    story = [Spacer(1, 0.4*cm)]
    story.append(Paragraph("EvidenceAI", s_doctitle))
    story.append(Paragraph(
        f"Research Session Export  ·  {session.get('created','')}  ·  {len(session.get('turns',[]))} turn(s)",
        s_docsub))
    story.append(HRFlowable(width="100%", thickness=2, color=accent, spaceAfter=16))

    for i, turn in enumerate(session.get("turns", [])):
        label = f"QUESTION {i+1}{'  ·  FOLLOW-UP' if turn.get('is_followup') else ''}"
        story.append(Paragraph(label, s_qlabel))
        if turn.get("is_followup"):
            story.append(Paragraph("Follow-up (context from prior answer passed to agent)", s_fu))
        story.append(Paragraph(
            turn["question"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"),
            s_qtext))
        story.append(Paragraph(
            f"{turn['elapsed']}s  ·  {len(turn['tool_calls'])} tool calls  ·  {turn['timestamp']}",
            s_meta))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dde3f0"), spaceAfter=6))
        story += md_to_flowables(turn["output"])
        if i < len(session.get("turns", [])) - 1:
            story.append(Spacer(1, 0.3*cm))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#c7d0e8"), spaceAfter=4))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    return buf.getvalue()


# ── Persistent history ─────────────────────────────────────────────────────────
def load_history_from_disk() -> list:
    if not os.path.exists(HISTORY_FILE): return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def save_history_to_disk(sessions: list):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(sessions, f, ensure_ascii=False, indent=2)
    except Exception as e: st.warning(f"Could not save: {e}")

def session_title(session: dict) -> str:
    if session.get("turns"):
        q = session["turns"][0]["question"].replace("\n", " ").strip()
        return (q[:32] + "…") if len(q) > 32 else q
    return "—"

# ── State ──────────────────────────────────────────────────────────────────────
for key, val in [("sessions", load_history_from_disk()), ("active_session_id", None), ("agent", None), ("agent_ready", False)]:
    if key not in st.session_state: st.session_state[key] = val

def load_agent(path):
    try:
        root = os.path.dirname(os.path.abspath(__file__))
        if root not in sys.path: sys.path.insert(0, root)
        from agent import DeepResearchAgent
        return DeepResearchAgent(persist_directory=path), None
    except Exception as e: return None, str(e)

def build_followup_prompt(prior, q):
    ctx = prior[:CONTEXT_CHAR_LIMIT] + ("\n[...truncated...]" if len(prior) > CONTEXT_CHAR_LIMIT else "")
    return f"PRIOR RESEARCH CONTEXT:\n{'='*60}\n{ctx}\n{'='*60}\n\nFOLLOW-UP QUESTION:\n{q}"

def run_agent(question, is_followup=False, prior_output=""):
    prompt = build_followup_prompt(prior_output, question) if (is_followup and prior_output) else question
    start  = time.time()
    result = st.session_state.agent.research(prompt)
    elapsed = round(time.time() - start, 1)
    tool_calls = []
    for i, step in enumerate(result.get("intermediate_steps", [])):
        action, obs = step
        preview = str(obs)[:600] + ("…" if len(str(obs)) > 600 else "")
        tool_calls.append({"call_number": i+1, "tool_name": getattr(action,"tool","?"), "tool_input": str(getattr(action,"tool_input","")), "preview": preview})
    return {"question": question, "output": result.get("output",""), "tool_calls": tool_calls, "elapsed": elapsed, "is_followup": is_followup, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}

def get_active_session():
    sid = st.session_state.active_session_id
    if sid is None: return None
    for s in st.session_state.sessions:
        if s["id"] == sid: return s
    return None

def create_new_session(first_turn):
    s = {"id": f"s_{int(time.time()*1000)}", "created": datetime.now().strftime("%Y-%m-%d %H:%M"), "turns": [first_turn]}
    st.session_state.sessions.insert(0, s)
    st.session_state.active_session_id = s["id"]
    save_history_to_disk(st.session_state.sessions)
    return s

def append_turn(session_id, turn):
    for s in st.session_state.sessions:
        if s["id"] == session_id: s["turns"].append(turn); break
    save_history_to_disk(st.session_state.sessions)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sb-title">EvidenceAI</div><div class="sb-sub">GIZ Project Database · v0.1</div>', unsafe_allow_html=True)

    chroma_path = st.text_input("db", value="./chroma_db", label_visibility="collapsed", placeholder="./chroma_db")
    if st.button("⚡ Connect", use_container_width=True):
        with st.spinner("Connecting…"):
            agent, err = load_agent(chroma_path)
            if agent: st.session_state.agent = agent; st.session_state.agent_ready = True; st.success("Connected")
            else: st.error(str(err))

    c = "#34d399" if st.session_state.agent_ready else "#f87171"
    t = "● CONNECTED" if st.session_state.agent_ready else "○ NOT CONNECTED"
    st.markdown(f"<div style='font-size:.68rem;color:{c};font-weight:600;margin-top:.2rem;font-family:JetBrains Mono,monospace;'>{t}</div>", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("＋ New Session", use_container_width=True):
        st.session_state.active_session_id = None; st.rerun()
    st.markdown("---")

    if st.session_state.sessions:
        st.markdown('<div class="sb-lbl">Sessions</div>', unsafe_allow_html=True)
        for session in st.session_state.sessions[:30]:
            title     = session_title(session)
            n         = len(session.get("turns", []))
            is_active = session["id"] == st.session_state.active_session_id
            label     = f"{'▸ ' if is_active else ''}{title}"
            if st.button(label, key=f"sess_{session['id']}", use_container_width=True,
                         help=f"{session.get('created','')[:10]} · {n} turn(s)"):
                st.session_state.active_session_id = session["id"]; st.rerun()
    else:
        st.markdown("<div style='font-size:.7rem;color:var(--text-mute);'>No sessions yet.</div>", unsafe_allow_html=True)

    st.markdown("---")
    if st.session_state.sessions:
        if st.button("🗑 Clear History", use_container_width=True):
            st.session_state.sessions = []; st.session_state.active_session_id = None
            save_history_to_disk([]); st.rerun()

    st.markdown('<div class="sb-meta">History → research_history.json<br>Max calls: 4 · Iterations: 8<br>Model: GPT-5</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
    <div class="ev-header">
        <span class="ev-title">EvidenceAI</span>
        <span class="ev-ver">v0.1</span>
        <span class="ev-sub">GIZ Project Evaluation Database</span>
    </div>
""", unsafe_allow_html=True)

active_session = get_active_session()

# ── VIEW A ─────────────────────────────────────────────────────────────────────
if active_session is None:
    st.markdown("""
        <div class="empty-state">
            <span class="empty-icon">🧠</span>
            <div class="empty-title">Start a new research session</div>
            <div class="empty-desc">Ask questions about GIZ project evaluations.<br>Follow-ups carry context from prior answers.</div>
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.agent_ready:
        st.markdown('<div class="info-box">⚡ Connect to the vector database in the sidebar to begin.</div>', unsafe_allow_html=True)
    else:
        query = st.text_area("q", height=130,
            placeholder="e.g. What institutional factors determined sustainability of water projects in East Africa after project closure?",
            label_visibility="collapsed")

        c1, _ = st.columns([1, 5])
        with c1:
            run_btn = st.button("▶ Run Research", disabled=not (query or "").strip())

        st.markdown('<div class="runtime-banner">⏱ &nbsp; Estimated runtime: <b>1 – 3 minutes</b> &nbsp;·&nbsp; Up to <b>4 tool calls</b></div>', unsafe_allow_html=True)

        if run_btn and (query or "").strip():
            with st.spinner("Researching…"):
                try:
                    turn = run_agent(query.strip())
                    create_new_session(turn)
                    st.rerun()
                except Exception as e:
                    st.error(f"Agent error: {e}")

# ── VIEW B ─────────────────────────────────────────────────────────────────────
else:
    turns = active_session.get("turns", [])

    for t_idx, turn in enumerate(turns):
        badge = '<span class="fu-badge">FOLLOW-UP</span>' if turn.get("is_followup") else ""
        st.markdown(f"""
            <div class="q-bubble">
                <div class="q-label">Question {t_idx+1}&nbsp;{badge}</div>
                <div class="q-text">{turn['question'].replace('<','&lt;').replace('>','&gt;')}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""
            <div class="a-card">
                <div class="a-metrics">
                    <div class="a-metric">⏱ <b>{turn['elapsed']}s</b></div>
                    <div class="a-metric">🔧 <b>{len(turn['tool_calls'])} tool calls</b></div>
                    <div class="a-metric">📅 <b>{turn['timestamp']}</b></div>
                    <div class="a-metric">📝 <b>{len(turn['output']):,} chars</b></div>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown(turn["output"])

        if turn["tool_calls"]:
            with st.expander(f"🔧 Tool call trace — {len(turn['tool_calls'])} calls"):
                for call in turn["tool_calls"]:
                    st.markdown(f'<span class="tc-badge tc-num">#{call["call_number"]}</span><span class="tc-badge tc-name">{call["tool_name"]}</span>', unsafe_allow_html=True)
                    st.markdown(f"`{call['tool_input']}`")
                    with st.expander("Result preview"):
                        st.text(call["preview"])
                    st.markdown("---")

        e1, e2 = st.columns(2)
        with e1:
            st.download_button(
                "⬇ Export turn (.txt)",
                data=f"Q: {turn['question']}\n\n{'='*60}\n\n{turn['output']}",
                file_name=f"turn_{t_idx+1}_{active_session['id']}.txt",
                mime="text/plain",
                key=f"dl_txt_{active_session['id']}_{t_idx}",
            )
        with e2:
            try:
                single = {**active_session, "turns": [turn]}
                st.download_button(
                    "⬇ Export turn (.pdf)",
                    data=generate_pdf(single),
                    file_name=f"evidenceai_turn_{t_idx+1}.pdf",
                    mime="application/pdf",
                    key=f"dl_pdf_{active_session['id']}_{t_idx}",
                )
            except Exception as e:
                st.caption(f"PDF error: {e}")

    # ── Follow-up ──────────────────────────────────────────────────────────────
    if st.session_state.agent_ready:
        st.markdown('<div class="fu-section">', unsafe_allow_html=True)
        st.markdown('<div class="fu-label">↩ Ask a follow-up question</div>', unsafe_allow_html=True)
        if turns:
            preview = turns[-1]["output"][:200].replace("\n"," ") + ("…" if len(turns[-1]["output"])>200 else "")
            st.markdown(f'<div class="ctx-prev">Context: "{preview}"</div>', unsafe_allow_html=True)
        followup = st.text_area("fu", height=85,
            placeholder="e.g. Focus specifically on Kenya — what was different there?",
            label_visibility="collapsed", key=f"fu_{active_session['id']}")
        fc1, fc2 = st.columns([1,1])
        with fc1:
            run_fu = st.button("▶ Run Follow-up", disabled=not (followup or "").strip(), key=f"run_fu_{active_session['id']}")
        with fc2:
            if st.button("＋ New Session", key=f"new_{active_session['id']}"):
                st.session_state.active_session_id = None; st.rerun()
        st.markdown('<div class="runtime-banner" style="margin-top:.6rem;">⏱ &nbsp; Estimated runtime: <b>1 – 3 minutes</b> &nbsp;·&nbsp; Up to <b>4 tool calls</b></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if run_fu and (followup or "").strip():
            prior = turns[-1]["output"] if turns else ""
            with st.spinner("Researching follow-up…"):
                try:
                    turn = run_agent(followup.strip(), is_followup=True, prior_output=prior)
                    append_turn(active_session["id"], turn)
                    st.rerun()
                except Exception as e:
                    st.error(f"Agent error: {e}")
    else:
        st.markdown('<div class="info-box" style="margin-top:1.5rem;">⚡ Connect to the vector database to ask follow-up questions.</div>', unsafe_allow_html=True)

    # ── Full session export ────────────────────────────────────────────────────
    if turns:
        st.markdown("---")
        s1, s2 = st.columns(2)
        with s1:
            full_txt = f"EvidenceAI v0.1\n{active_session['created']}\n{'='*60}\n\n"
            for i, t in enumerate(turns):
                fu = " [FOLLOW-UP]" if t.get("is_followup") else ""
                full_txt += f"Q{i+1}{fu}: {t['question']}\n\n{t['output']}\n\n{'—'*40}\n\n"
            st.download_button("⬇ Full session (.txt)", data=full_txt,
                file_name=f"evidenceai_session_{active_session['id']}.txt", mime="text/plain",
                key=f"dl_full_txt_{active_session['id']}")
        with s2:
            try:
                st.download_button("⬇ Full session (.pdf)", data=generate_pdf(active_session),
                    file_name=f"evidenceai_session_{active_session['id']}.pdf", mime="application/pdf",
                    key=f"dl_full_pdf_{active_session['id']}")
            except Exception as e:
                st.caption(f"PDF error: {e}")