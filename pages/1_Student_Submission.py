import sys
sys.path.insert(0, ".")
import json
import os
import streamlit as st
import db
from config import COMPETENCIES, REFLECTION_QUESTIONS
from services import processor

st.set_page_config(page_title="Student Submission", layout="centered")
st.title("Submit Your Assessment")

students = db.get_students()
if not students:
    st.warning("No students found. Ask your admin to add students.")
    st.stop()

student_map = {s["name"]: s["id"] for s in students}
selected_name = st.selectbox("Your name", list(student_map.keys()))
student_id = student_map[selected_name]

round_num = st.number_input("Round number", min_value=1, max_value=50, value=1, step=1)

st.subheader("Competency Self-Ratings")
st.caption("Rate yourself from 1 (needs work) to 5 (excellent)")
ratings = {}
for comp in COMPETENCIES:
    ratings[comp] = st.slider(comp, min_value=1, max_value=5, value=3)

st.subheader("Reflections")
reflections = {}
for question in REFLECTION_QUESTIONS:
    reflections[question] = st.text_area(question, height=100)

st.subheader("Video Recording")
video_file = st.file_uploader(
    "Upload your session recording", type=["mp4", "mov", "webm", "avi"]
)

if st.button("Submit Assessment", type="primary"):
    if not video_file:
        st.error("Please upload a video recording before submitting.")
        st.stop()

    empty_reflections = [q for q in REFLECTION_QUESTIONS if not reflections[q].strip()]
    if empty_reflections:
        st.warning(f"Please answer all reflection questions. Missing: {', '.join(empty_reflections)}")
        st.stop()

    os.makedirs("uploads", exist_ok=True)
    video_path = f"uploads/submission_{student_id}_round{int(round_num)}.mp4"
    with open(video_path, "wb") as f:
        f.write(video_file.read())

    assessment = db.create_assessment(
        student_id=student_id,
        round_num=int(round_num),
        competency_ratings=json.dumps(ratings),
        reflections=json.dumps(reflections),
    )

    progress_bar = st.progress(0.0, text="Starting...")

    def update_progress(fraction: float, message: str) -> None:
        progress_bar.progress(fraction, text=message)

    try:
        processor.process_assessment(assessment["id"], video_path, progress_fn=update_progress)
        st.success("Assessment submitted successfully!")
        updated = db.get_assessment_by_id(assessment["id"])
        if updated.get("drive_folder_url"):
            st.markdown(f"[View your Drive folder]({updated['drive_folder_url']})")
    except Exception as e:
        st.error(f"Processing failed: {e}")
        st.info("Your submission was saved. Ask your admin to retry processing from the Admin page.")
