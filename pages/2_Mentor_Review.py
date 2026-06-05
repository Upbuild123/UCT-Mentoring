import sys
sys.path.insert(0, ".")
import json
from datetime import datetime
import streamlit as st
import db
from config import COMPETENCIES, REFLECTION_QUESTIONS, RATING_OPTIONS
from services.processor import generate_and_send_pdf

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
existing_feedback = db.get_mentor_feedback(assessment_id)

existing_mentor_ratings = json.loads(existing_feedback.get("mentor_ratings") or "{}") if existing_feedback else {}

MENTOR_QUESTIONS = [
    "What did the coach do well in this coaching session?",
    "What opportunities were there to strengthen this coaching session?",
    "What are the developmental opportunities for the coach?",
    "What are 1-2 development practices for the coach?",
]

existing_answers = {}
if existing_feedback and existing_feedback.get("feedback_text"):
    try:
        existing_answers = json.loads(existing_feedback["feedback_text"])
    except (json.JSONDecodeError, TypeError):
        pass

try:
    submitted_str = str(assessment.get('submitted_at', ''))
    submitted_date = datetime.fromisoformat(submitted_str).strftime("%-d %B").lstrip("0")
    submitted_label = f"Submitted on {datetime.fromisoformat(submitted_str).strftime('%B %-d')}"
except Exception:
    submitted_label = "Submitted on N/A"

st.subheader(f"Coach: {student['name']} -- Round {assessment['round']}", anchor=False)
st.caption(submitted_label)

# --- Competency ratings comparison ---
st.divider()
st.markdown("### Mentor Assessment Ratings")
coach_ratings = json.loads(assessment.get("competency_ratings") or "{}")

mentor_ratings = {}
current_category = None
for comp in COMPETENCIES:
    if comp["category"] != current_category:
        current_category = comp["category"]
        col_hdr, _ = st.columns([6, 5])
        with col_hdr:
            st.markdown(f"<p style='font-size:17px; font-weight:700; margin:14px 0 4px 0;'>{current_category}</p>", unsafe_allow_html=True)

    col_name, col_coach, col_mentor, _ = st.columns([3, 2, 2, 4])
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


# --- Reflections ---
st.divider()
st.markdown("### Coach Reflections")
reflections = json.loads(assessment.get("reflections") or "{}")
for question in REFLECTION_QUESTIONS:
    answer = reflections.get(question, "(no answer)")
    st.markdown(f"**{question}**")
    st.write(answer)

# --- Mentor feedback ---
st.divider()
st.markdown("### Mentor Reflections")
mentor_answers = {}
for i, question in enumerate(MENTOR_QUESTIONS):
    mentor_answers[question] = st.text_area(
        question,
        value=existing_answers.get(question, ""),
        height=192 if i < 2 else 120,
        key=f"mentor_q_{i}",
    )

if st.button("Submit Feedback", type="primary"):
    empty_answers = [q for q in MENTOR_QUESTIONS if not mentor_answers[q].strip()]
    if empty_answers:
        st.warning(f"Please answer all questions. Missing: {', '.join(empty_answers)}")
    else:
        unrated = [comp["name"] for comp in COMPETENCIES if mentor_ratings.get(comp["name"]) == "-- select --"]
        if unrated:
            st.warning(f"Please complete all mentor ratings. Missing: {', '.join(unrated)}")
        else:
            clean_mentor_ratings = {k: v for k, v in mentor_ratings.items() if v != "-- select --"}
            db.save_mentor_feedback(assessment_id, json.dumps(mentor_answers), json.dumps(clean_mentor_ratings))
            with st.spinner("Generating assessment PDF and sending to both parties..."):
                try:
                    pdf_url = generate_and_send_pdf(assessment_id)
                    st.success("Feedback saved. Assessment PDF generated and emailed to you and the coach.")
                    st.markdown(f"[View Assessment PDF]({pdf_url})")
                except Exception as e:
                    st.warning(f"Feedback saved, but PDF generation failed: {e}")

