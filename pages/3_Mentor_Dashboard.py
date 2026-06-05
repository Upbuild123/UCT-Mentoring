import sys
sys.path.insert(0, ".")
import os
from datetime import datetime
import streamlit as st
import db

st.set_page_config(page_title="Mentor Dashboard", layout="wide")
st.markdown("<style>[data-testid='stSidebarNav'] {display: none;}</style>", unsafe_allow_html=True)
st.title("Mentor Dashboard")

params = st.query_params
mentor_id_str = params.get("mentor_id")

if not mentor_id_str:
    st.info("Select a mentor to view their dashboard.")
    mentors = db.get_mentors()
    if not mentors:
        st.warning("No mentors found.")
        st.stop()
    mentor_map = {m["name"]: m["id"] for m in mentors}
    selected = st.selectbox("Select mentor", list(mentor_map.keys()))
    mentor_id = mentor_map[selected]
else:
    try:
        mentor_id = int(mentor_id_str)
    except ValueError:
        st.error("Invalid mentor ID.")
        st.stop()

mentor = db.get_mentor_by_id(mentor_id)
if not mentor:
    st.error("Mentor not found.")
    st.stop()

st.subheader(f"Welcome, {mentor['name'].split()[0]}")

assessments = db.get_assessments_by_mentor(mentor_id)
app_url = os.environ.get("APP_URL", "http://localhost:8501")

# Group assessments by student
students = db.get_students()
mentor_students = [s for s in students if s["mentor_id"] == mentor_id]

if not mentor_students:
    st.info("No students assigned yet.")
    st.stop()

assessments_by_student = {}
for a in assessments:
    assessments_by_student.setdefault(a["student_id"], []).append(a)

for student in sorted(mentor_students, key=lambda s: s["name"]):
    student_assessments = sorted(assessments_by_student.get(student["id"], []), key=lambda a: a["round"])
    rounds_complete = len([a for a in student_assessments if a["status"] == "complete"])
    rounds_total = len(student_assessments)

    label = f"{student['name']}  —  {rounds_total} round{'s' if rounds_total != 1 else ''} submitted"

    with st.expander(label):
        if not student_assessments:
            st.caption("No submissions yet.")
        else:
            for a in student_assessments:
                try:
                    date_str = datetime.fromisoformat(str(a.get("submitted_at", ""))).strftime("%B %-d")
                except Exception:
                    date_str = "N/A"

                status_color = {"complete": "green", "error": "red", "processing": "orange"}.get(a["status"], "gray")
                review_url = f"{app_url}/Mentor_Review?assessment_id={a['id']}"

                col1, col2, col3 = st.columns([2, 2, 3])
                with col1:
                    st.markdown(f"**Round {a['round']}** — {date_str}")
                with col2:
                    st.markdown(f":{status_color}[{a['status'].upper()}]")
                with col3:
                    st.markdown(f"[Review]({review_url})")
                    if a.get("drive_folder_url"):
                        st.markdown(f"[Drive folder]({a['drive_folder_url']})")
