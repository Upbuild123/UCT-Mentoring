import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import db
db.init_db()

# Seed default mentors if none exist
import seed
seed.seed()

import streamlit as st

st.set_page_config(page_title="Mentoring Assessment", layout="centered")
st.markdown("<style>[data-testid='stSidebarNav'] {display: none;} [data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
st.switch_page("pages/1_Student_Submission.py")
