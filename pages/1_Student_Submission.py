import sys
sys.path.insert(0, ".")
import json
import os
import streamlit as st
import db
from config import COMPETENCIES, REFLECTION_QUESTIONS, RATING_OPTIONS
from services import processor

st.set_page_config(page_title="Student Submission", layout="centered")
st.title("Submit Your Mentoring Record")

students = db.get_students()
if not students:
    st.warning("No students found. Ask your admin to add students.")
    st.stop()

student_map = {s["name"]: s["id"] for s in students}
selected_name = st.selectbox("Your name", list(student_map.keys()))
student_id = student_map[selected_name]

round_num = st.radio("Round number", options=[1, 2, 3, 4], horizontal=True)

st.subheader("Video Recording")
video_file = st.file_uploader(
    "Upload your session recording", type=["mp4", "mov", "webm", "avi"]
)

st.subheader("Student Self-Assessment Ratings")

ratings = {}
current_category = None
for comp in COMPETENCIES:
    if comp["category"] != current_category:
        current_category = comp["category"]
        st.markdown(f"<p style='font-size:15px; font-weight:600; margin:8px 0 4px 0;'>{current_category}</p>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"<p style='margin:0; font-size:13px; font-weight:600;'>{comp['name']}</p>", unsafe_allow_html=True)
        st.caption(comp["description"])
    with col2:
        ratings[comp["name"]] = st.selectbox(
            comp["name"],
            options=["-- select --"] + RATING_OPTIONS,
            label_visibility="collapsed",
            key=f"rating_{comp['name']}",
        )

st.subheader("Coach Self-Assessment")
reflections = {}
for question in REFLECTION_QUESTIONS:
    reflections[question] = st.text_area(question, height=80)

if st.button("Submit", type="primary"):
    if not video_file:
        st.error("Please upload a video recording before submitting.")
        st.stop()

    unrated = [comp["name"] for comp in COMPETENCIES if ratings.get(comp["name"]) == "-- select --"]
    if unrated:
        st.warning(f"Please rate all competencies. Missing: {', '.join(unrated)}")
        st.stop()

    empty_reflections = [q for q in REFLECTION_QUESTIONS if not reflections[q].strip()]
    if empty_reflections:
        st.warning(f"Please answer all reflection questions. Missing: {', '.join(empty_reflections)}")
        st.stop()

    # Strip placeholder from saved ratings
    clean_ratings = {k: v for k, v in ratings.items() if v != "-- select --"}

    os.makedirs("uploads", exist_ok=True)
    video_path = f"uploads/submission_{student_id}_round{int(round_num)}.mp4"
    with open(video_path, "wb") as f:
        f.write(video_file.read())

    assessment = db.create_assessment(
        student_id=student_id,
        round_num=int(round_num),
        competency_ratings=json.dumps(clean_ratings),
        reflections=json.dumps(reflections),
    )

    progress_bar = st.progress(0.0, text="Starting...")

    def update_progress(fraction: float, message: str) -> None:
        progress_bar.progress(fraction, text=message)

    try:
        processor.process_assessment(assessment["id"], video_path, progress_fn=update_progress)
        st.success("Mentoring record submitted successfully!")
        updated = db.get_assessment_by_id(assessment["id"])
        if updated.get("drive_folder_url"):
            st.markdown(f"[View your Drive folder]({updated['drive_folder_url']})")
    except Exception as e:
        st.error(f"Processing failed: {e}")
        st.info("Your submission was saved. Ask your admin to retry processing from the Admin page.")
