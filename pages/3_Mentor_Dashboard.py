import sys
sys.path.insert(0, ".")
import os
import streamlit as st
import db

st.set_page_config(page_title="Mentor Dashboard", layout="wide")
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

st.subheader(f"Assessments for {mentor['name']}")

assessments = db.get_assessments_by_mentor(mentor_id)
if not assessments:
    st.info("No assessments assigned yet.")
    st.stop()

app_url = os.environ.get("APP_URL", "http://localhost:8501")

for a in assessments:
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.markdown(f"**{a['student_name']}** -- Round {a['round']}")
            st.caption(f"Submitted: {a.get('submitted_at', 'N/A')}")
        with col2:
            status_color = {"complete": "green", "error": "red", "processing": "orange"}.get(
                a["status"], "gray"
            )
            st.markdown(f":{status_color}[{a['status'].upper()}]")
        with col3:
            review_url = f"{app_url}/Mentor_Review?assessment_id={a['id']}"
            st.markdown(f"[Review]({review_url})")
            if a.get("drive_folder_url"):
                st.markdown(f"[Drive folder]({a['drive_folder_url']})")
