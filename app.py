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

st.switch_page("pages/1_Student_Submission.py")
