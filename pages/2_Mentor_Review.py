import sys
sys.path.insert(0, ".")
import json
import streamlit as st
import db
from config import COMPETENCIES, REFLECTION_QUESTIONS, RATING_OPTIONS
from services.processor import generate_and_send_pdf

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

existing_mentor_ratings = json.loads(existing_feedback.get("mentor_ratings") or "{}") if existing_feedback else {}

st.subheader(f"Coach: {student['name']} -- Round {assessment['round']}", anchor=False)
st.caption(f"Submitted: {assessment.get('submitted_at', 'N/A')} | Status: {assessment['status']}")

# --- Competency ratings comparison ---
st.divider()
st.markdown("### Self-Assessment Ratings", anchor=False)
coach_ratings = json.loads(assessment.get("competency_ratings") or "{}")

mentor_ratings = {}
current_category = None
for comp in COMPETENCIES:
    if comp["category"] != current_category:
        current_category = comp["category"]
        st.markdown(f"<p style='font-size:14px; font-weight:600; margin:10px 0 4px 0;'>{current_category}</p>", unsafe_allow_html=True)

    col_name, col_coach, col_mentor = st.columns([3, 2, 2])
    with col_name:
        st.markdown(f"<p style='margin:6px 0 0 0; font-size:13px; font-weight:600;'>{comp['name']}</p>", unsafe_allow_html=True)
    with col_coach:
        coach_val = coach_ratings.get(comp["name"], "-")
        st.markdown(f"<p style='margin:6px 0 0 0; font-size:12px; color:#555;'>Coach: <strong>{coach_val}</strong></p>", unsafe_allow_html=True)
    with col_mentor:
        default_idx = (RATING_OPTIONS.index(existing_mentor_ratings[comp["name"]]) + 1
                       if existing_mentor_ratings.get(comp["name"]) in RATING_OPTIONS else 0)
        mentor_ratings[comp["name"]] = st.selectbox(
            comp["name"],
            options=["-- select --"] + RATING_OPTIONS,
            index=default_idx,
            label_visibility="collapsed",
            key=f"mentor_rating_{comp['name']}",
        )

# --- Column headers for ratings ---
st.caption("Left column: coach self-rating. Right column: your rating.")

# --- Reflections ---
st.divider()
st.markdown("### Coach Reflections", anchor=False)
reflections = json.loads(assessment.get("reflections") or "{}")
for question in REFLECTION_QUESTIONS:
    answer = reflections.get(question, "(no answer)")
    st.markdown(f"**{question}**")
    st.write(answer)

# --- Transcript ---
st.divider()
st.markdown("### Session Transcript", anchor=False)
transcript = assessment.get("transcript") or "(transcript not yet available)"
st.text_area("Transcript", value=transcript, height=200, disabled=True, label_visibility="collapsed")

# --- AI Review (mentor only) ---
if ai_review:
    st.divider()
    st.markdown("### AI Review", anchor=False)
    st.info(ai_review["content"])

# --- Mentor feedback ---
st.divider()
st.markdown("### Your Feedback", anchor=False)
feedback_text = st.text_area(
    "Write your feedback for the coach",
    value=existing_feedback["feedback_text"] if existing_feedback else "",
    height=200,
)

if st.button("Save Feedback", type="primary"):
    if not feedback_text.strip():
        st.error("Please write feedback before saving.")
    else:
        unrated = [comp["name"] for comp in COMPETENCIES if mentor_ratings.get(comp["name"]) == "-- select --"]
        if unrated:
            st.warning(f"Please complete all mentor ratings. Missing: {', '.join(unrated)}")
        else:
            clean_mentor_ratings = {k: v for k, v in mentor_ratings.items() if v != "-- select --"}
            db.save_mentor_feedback(assessment_id, feedback_text.strip(), json.dumps(clean_mentor_ratings))
            with st.spinner("Generating assessment PDF and sending to both parties..."):
                try:
                    pdf_url = generate_and_send_pdf(assessment_id)
                    st.success("Feedback saved. Assessment PDF generated and emailed to you and the coach.")
                    st.markdown(f"[View Assessment PDF]({pdf_url})")
                except Exception as e:
                    st.warning(f"Feedback saved, but PDF generation failed: {e}")

if assessment.get("drive_folder_url"):
    st.markdown(f"[Open Drive Folder]({assessment['drive_folder_url']})")
if assessment.get("pdf_drive_url"):
    st.markdown(f"[View Assessment PDF]({assessment['pdf_drive_url']})")
