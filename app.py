import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import db
db.init_db()

import seed
seed.seed()

import streamlit as st

st.set_page_config(page_title="Upbuild Mentoring", layout="centered")
st.markdown("<style>[data-testid='stSidebarNav'] {display: none;}</style>", unsafe_allow_html=True)
st.title("Welcome to Upbuild Mentoring")
