import sys
sys.path.insert(0, ".")
import json
import streamlit as st
import db
from config import COMPETENCIES, REFLECTION_QUESTIONS

st.set_page_config(page_title="Mentor Review", layout="wide")
st.title("Mentor Review")

params = st.query_params
assessment_id_str = params.get("assessment_id")

if not assessment_id_str:
    st.error("No assessment ID provided. Use the link from your notification email or dashboard.")
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
ai_review = db.get_ai_review(assessment_id)
existing_feedback = db.get_mentor_feedback(assessment_id)

st.subheader(f"Student: {student['name']} -- Round {assessment['round']}")
st.caption(f"Submitted: {assessment.get('submitted_at', 'N/A')} | Status: {assessment['status']}")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Competency Ratings")
    ratings = json.loads(assessment.get("competency_ratings") or "{}")
    for comp in COMPETENCIES:
        score = ratings.get(comp, "N/A")
        st.write(f"**{comp}:** {score}/5")

with col2:
    st.markdown("### Reflections")
    reflections = json.loads(assessment.get("reflections") or "{}")
    for question in REFLECTION_QUESTIONS:
        answer = reflections.get(question, "(no answer)")
        st.markdown(f"**{question}**")
        st.write(answer)

st.divider()
st.markdown("### Session Transcript")
transcript = assessment.get("transcript") or "(transcript not yet available)"
st.text_area("Transcript", value=transcript, height=200, disabled=True, label_visibility="collapsed")

if ai_review:
    st.divider()
    st.markdown("### AI Review (Internal)")
    st.info(ai_review["content"])

st.divider()
st.markdown("### Your Feedback")
feedback_text = st.text_area(
    "Write your feedback for the student",
    value=existing_feedback["feedback_text"] if existing_feedback else "",
    height=200,
)

if st.button("Save Feedback", type="primary"):
    if not feedback_text.strip():
        st.error("Please write feedback before saving.")
    else:
        db.save_mentor_feedback(assessment_id, feedback_text.strip())
        st.success("Feedback saved.")

if assessment.get("drive_folder_url"):
    st.markdown(f"[Open Drive Folder]({assessment['drive_folder_url']})")
if assessment.get("pdf_drive_url"):
    st.markdown(f"[View Assessment PDF]({assessment['pdf_drive_url']})")
