import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import db
db.init_db()

import seed
seed.seed()

import streamlit as st

st.set_page_config(page_title="Mentoring Assessment", layout="wide")

pg = st.navigation(
    [
        st.Page("pages/1_Student_Submission.py", title="Student Submission", default=True),
        st.Page("pages/2_Mentor_Review.py", title="Mentor Review"),
        st.Page("pages/3_Mentor_Dashboard.py", title="Mentor Dashboard"),
        st.Page("pages/4_Admin.py", title="Admin"),
        st.Page("pages/5_Transcript.py", title="Transcript"),
        st.Page("pages/6_AI_Review.py", title="AI Review"),
    ],
    position="hidden",
)
pg.run()
