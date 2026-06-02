import sys
sys.path.insert(0, ".")
import os
import streamlit as st
import db
from services import processor

st.set_page_config(page_title="Admin", layout="wide")
st.title("Admin Dashboard")

tab_assessments, tab_mentors, tab_students = st.tabs(["Assessments", "Mentors", "Students"])

app_url = os.environ.get("APP_URL", "http://localhost:8501")

# --- Assessments Tab ---
with tab_assessments:
    st.subheader("All Assessments")

    all_assessments = db.get_all_assessments()
    if not all_assessments:
        st.info("No assessments yet.")
    else:
        status_filter = st.selectbox(
            "Filter by status",
            ["all", "submitted", "processing", "complete", "error"],
        )
        filtered = (
            all_assessments
            if status_filter == "all"
            else [a for a in all_assessments if a["status"] == status_filter]
        )

        for a in filtered:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 3])
                with col1:
                    st.markdown(f"**{a['student_name']}** (mentor: {a['mentor_name']})")
                    st.caption(f"Round {a['round']} | {a.get('submitted_at', 'N/A')}")
                with col2:
                    status_color = {"complete": "green", "error": "red", "processing": "orange"}.get(
                        a["status"], "gray"
                    )
                    st.markdown(f":{status_color}[{a['status'].upper()}]")
                    if a.get("error_message"):
                        st.caption(f"Error: {a['error_message'][:80]}")
                with col3:
                    review_url = f"{app_url}/Mentor_Review?assessment_id={a['id']}"
                    st.markdown(f"[Review]({review_url})")
                    if a["status"] == "error":
                        if st.button(f"Retry #{a['id']}", key=f"retry_{a['id']}"):
                            video_path = f"uploads/submission_{a['student_id']}_round{a['round']}.mp4"
                            if not os.path.exists(video_path):
                                st.error(f"Video file not found at {video_path}. Cannot retry.")
                            else:
                                with st.spinner("Retrying..."):
                                    try:
                                        processor.process_assessment(a["id"], video_path)
                                        st.success("Retry succeeded.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Retry failed: {e}")

# --- Mentors Tab ---
with tab_mentors:
    st.subheader("Mentors")
    mentors = db.get_mentors()
    for m in mentors:
        with st.expander(f"{m['name']} -- {m['email']}"):
            with st.form(key=f"mentor_form_{m['id']}"):
                new_name = st.text_input("Name", value=m["name"])
                new_email = st.text_input("Email", value=m["email"])
                st.caption(f"Dashboard token: {m['dashboard_token']}")
                dashboard_url = f"{app_url}/Mentor_Dashboard?mentor_id={m['id']}"
                st.markdown(f"[Dashboard link]({dashboard_url})")
                if st.form_submit_button("Save"):
                    db.update_mentor(m["id"], new_name, new_email)
                    st.success("Saved.")
                    st.rerun()

    st.divider()
    st.markdown("#### Add Mentor")
    with st.form("add_mentor_form"):
        name = st.text_input("Name")
        email_addr = st.text_input("Email")
        if st.form_submit_button("Add Mentor"):
            if name.strip() and email_addr.strip():
                db.add_mentor(name.strip(), email_addr.strip())
                st.success(f"Mentor {name} added.")
                st.rerun()
            else:
                st.error("Name and email are required.")

# --- Students Tab ---
with tab_students:
    st.subheader("Students")
    students = db.get_students()
    mentors = db.get_mentors()
    mentor_map = {m["id"]: m["name"] for m in mentors}
    mentor_options = {m["name"]: m["id"] for m in mentors}

    for s in students:
        current_mentor_name = mentor_map.get(s["mentor_id"], "")
        with st.expander(f"{s['name']} -- mentor: {current_mentor_name or 'unassigned'}"):
            with st.form(key=f"student_form_{s['id']}"):
                new_name = st.text_input("Name", value=s["name"])
                mentor_names = list(mentor_options.keys())
                default_idx = mentor_names.index(current_mentor_name) if current_mentor_name in mentor_names else 0
                new_mentor_name = st.selectbox("Mentor", mentor_names, index=default_idx)
                if st.form_submit_button("Save"):
                    db.update_student(s["id"], new_name.strip(), mentor_options[new_mentor_name])
                    st.success("Saved.")
                    st.rerun()

    st.divider()
    st.markdown("#### Add Student")
    with st.form("add_student_form"):
        name = st.text_input("Name")
        mentor_name = st.selectbox("Mentor", list(mentor_options.keys()))
        if st.form_submit_button("Add Student"):
            if name.strip():
                db.add_student(name.strip(), mentor_options[mentor_name])
                st.success(f"Student {name} added.")
                st.rerun()
            else:
                st.error("Name is required.")
