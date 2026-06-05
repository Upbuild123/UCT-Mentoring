import sys
sys.path.insert(0, ".")
import json
import os
import streamlit as st
import db
from config import COMPETENCIES, REFLECTION_QUESTIONS, RATING_OPTIONS
from services import processor

st.title("Submit Your Mentoring Recording")

students = db.get_students()
if not students:
    st.warning("No students found. Ask your admin to add students.")
    st.stop()

student_map = {s["name"]: s["id"] for s in students}
selected_name = st.selectbox("Your name", list(student_map.keys()))
student_id = student_map[selected_name]

round_num = st.radio("Round number", options=[1, 2, 3, 4], horizontal=True)

st.subheader("Video Recording", anchor=False)
video_file = st.file_uploader(
    "Upload your session recording", type=["mp4", "mov", "webm", "avi"]
)

st.subheader("Coach Self-Assessment Ratings", anchor=False)

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

st.subheader("Coach Reflections", anchor=False)
reflections = {}
for i, question in enumerate(REFLECTION_QUESTIONS):
    reflections[question] = st.text_area(question, height=128 if i < 2 else 80)

existing_rounds = [a["round"] for a in db.get_assessments_by_student(student_id)]
duplicate_warning = int(round_num) in existing_rounds

if duplicate_warning and not st.session_state.get("confirm_duplicate"):
    st.warning(f"⚠️ You have already submitted Round {round_num}. Are you sure you want to submit again?")
    if st.button("Yes, submit anyway", type="primary"):
        st.session_state["confirm_duplicate"] = True
        st.rerun()
    st.stop()

if st.button("Submit", type="primary") or st.session_state.get("confirm_duplicate"):
    st.session_state.pop("confirm_duplicate", None)
    if not video_file:
        st.error("Please upload a video recording before submitting.")
        st.stop()

    unrated = [comp["name"] for comp in COMPETENCIES if ratings.get(comp["name"]) == "-- select --"]
    if unrated:
        st.warning(f"Please rate all competencies. Missing: {', '.join(unrated)}")
        st.stop()

    mandatory_questions = REFLECTION_QUESTIONS[:-2]
    empty_reflections = [q for q in mandatory_questions if not reflections[q].strip()]
    if empty_reflections:
        st.warning(f"Please answer all required reflection questions. Missing: {', '.join(empty_reflections)}")
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

    progress_bar = st.progress(0.0, text="Uploading...")

    def update_progress(fraction: float, message: str) -> None:
        progress_bar.progress(fraction, text=message)

    try:
        processor.process_assessment(assessment["id"], video_path, progress_fn=update_progress)
        st.success("Mentoring recording submitted successfully!")
        updated = db.get_assessment_by_id(assessment["id"])
        if updated.get("drive_folder_url"):
            st.markdown(f"[View your Drive folder]({updated['drive_folder_url']})")
    except Exception as e:
        st.error(f"Processing failed: {e}")
        st.info("Your submission was saved. Ask your admin to retry processing from the Admin page.")
