import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import db
db.init_db()

import seed
seed.seed()

import streamlit as st

st.set_page_config(page_title="Upbuild Mentoring", layout="wide")

st.markdown("""
<style>
/* ── Top branded header bar ─────────────────────────────────── */
[data-testid="stAppViewContainer"] > section:first-child::before {
    content: "";
    display: block;
    height: 4px;
    background: #5E328C;
    width: 100%;
}

/* ── Headings ────────────────────────────────────────────────── */
h1 { color: #5E328C !important; font-weight: 700 !important; }
h2 { color: #5E328C !important; font-weight: 600 !important; }
h3 { color: #3d1f6e !important; font-weight: 600 !important; }

/* ── Dividers ────────────────────────────────────────────────── */
hr { border-color: #D8C8F0 !important; }

/* ── Metric labels ───────────────────────────────────────────── */
[data-testid="stMetricLabel"] { color: #5E328C !important; }

/* ── Expander headers ────────────────────────────────────────── */
[data-testid="stExpander"] summary {
    font-weight: 600;
    color: #5E328C !important;
}

/* ── Tab labels ──────────────────────────────────────────────── */
[data-testid="stTabs"] button[role="tab"] {
    font-weight: 500;
    color: #5E328C !important;
}

/* ── Captions ────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] { color: #7a5fa0 !important; }

/* ── Info/warning/success box accents ───────────────────────── */
[data-testid="stAlert"] { border-radius: 8px !important; }

/* ── Top bar accent line ─────────────────────────────────────── */
header[data-testid="stHeader"] {
    border-bottom: 3px solid #5E328C;
}
</style>
""", unsafe_allow_html=True)

pg = st.navigation(
    [
        st.Page("pages/home.py", title="Home", default=True),
        st.Page("pages/1_Student_Submission.py", title="Student Submission"),
        st.Page("pages/2_Mentor_Review.py", title="Mentor Review"),
        st.Page("pages/3_Mentor_Dashboard.py", title="Mentor Dashboard"),
        st.Page("pages/4_Admin.py", title="Admin"),
        st.Page("pages/5_Transcript.py", title="Transcript"),
        st.Page("pages/6_AI_Review.py", title="AI Review"),
    ],
    position="hidden",
)
pg.run()
