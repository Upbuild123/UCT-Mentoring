import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import db
db.init_db()

import streamlit as st

st.set_page_config(page_title="Mentoring Assessment", layout="centered")
st.title("Mentoring Assessment Program")
st.markdown("""
Welcome. Use the sidebar to navigate:

- **Student Submission** -- submit your video and self-assessment
- **Mentor Review** -- review a student submission (use the link from your email)
- **Mentor Dashboard** -- view all your assigned assessments
- **Admin** -- manage mentors, students, and all assessments
""")
