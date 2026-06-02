import sys
sys.path.insert(0, ".")
import streamlit as st
import db

st.set_page_config(page_title="Session Transcript", layout="centered")
st.title("Session Transcript")

params = st.query_params
assessment_id_str = params.get("assessment_id")

if not assessment_id_str:
    st.error("No assessment ID provided.")
    st.stop()

try:
    assessment_id = int(assessment_id_str)
except ValueError:
    st.error("Invalid assessment ID.")
    st.stop()

assessment = db.get_assessment_by_id(assessment_id)
if not assessment:
    st.error("Assessment not found.")
    st.stop()

student = db.get_student_by_id(assessment["student_id"])
st.caption(f"{student['name']} -- Round {assessment['round']}")
st.divider()

transcript = assessment.get("transcript") or "(Transcript not yet available.)"
st.markdown(transcript)
