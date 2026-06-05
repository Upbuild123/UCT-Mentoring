import sys
sys.path.insert(0, ".")
import os
import streamlit as st
import db
from services import processor
from services.openai_service import generate_ai_review


admin_password = os.environ.get("ADMIN_PASSWORD", "")
if admin_password:
    entered = st.text_input("Admin password", type="password")
    if entered != admin_password:
        if entered:
            st.error("Incorrect password.")
        st.stop()

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
                    if a["status"] == "complete":
                        if st.button(f"Regenerate AI Review #{a['id']}", key=f"regen_{a['id']}"):
                            with st.spinner("Regenerating AI review..."):
                                try:
                                    assessment_data = db.get_assessment_by_id(a["id"])
                                    transcript = assessment_data.get("transcript") or ""
                                    new_review = generate_ai_review(assessment_data, transcript)
                                    db.save_ai_review(a["id"], new_review)
                                    st.success("AI review regenerated.")
                                except Exception as e:
                                    st.error(f"Failed: {e}")

# --- Mentors Tab ---
with tab_mentors:
    st.subheader("Mentors")
    mentors = db.get_mentors()
    for m in mentors:
        with st.expander(f"{m['name']} -- {m['email']}"):
            mentor_students = [s for s in db.get_students() if s["mentor_id"] == m["id"]]
            if mentor_students:
                st.markdown("**Students**")
                for s in mentor_students:
                    st.caption(f"• {s['name']} ({s.get('email') or 'no email'})")
            else:
                st.caption("No students assigned.")
            st.divider()
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
                new_email = st.text_input("Email", value=s.get("email") or "")
                mentor_names = list(mentor_options.keys())
                default_idx = mentor_names.index(current_mentor_name) if current_mentor_name in mentor_names else 0
                new_mentor_name = st.selectbox("Mentor", mentor_names, index=default_idx)
                if st.form_submit_button("Save"):
                    if not new_email.strip():
                        st.error("Email is required.")
                    else:
                        db.update_student(s["id"], new_name.strip(), mentor_options[new_mentor_name], new_email.strip())
                        st.success("Saved.")
                        st.rerun()

    st.divider()
    st.markdown("#### Bulk Import Students")
    st.caption("Copy 3 columns from Google Sheets (Name, Email, Mentor) and paste below.")
    bulk_data = st.text_area("Paste rows here", height=150, placeholder="Jane Smith\tjane@email.com\tMichael Sloyer\nJohn Doe\tjohn@email.com\tGina Kellogg")
    if st.button("Import Students"):
        if not bulk_data.strip():
            st.error("Nothing to import.")
        else:
            added, skipped = [], []
            for i, line in enumerate(bulk_data.strip().splitlines(), 1):
                parts = [p.strip() for p in line.split("\t")]
                if len(parts) != 3:
                    skipped.append(f"Row {i}: expected 3 columns, got {len(parts)}")
                    continue
                s_name, s_email, s_mentor = parts
                if not s_name or not s_email:
                    skipped.append(f"Row {i}: name and email are required")
                    continue
                if s_mentor not in mentor_options:
                    skipped.append(f"Row {i}: mentor '{s_mentor}' not found")
                    continue
                db.add_student(s_name, mentor_options[s_mentor], s_email)
                added.append(s_name)
            if added:
                st.success(f"Imported {len(added)} student(s): {', '.join(added)}")
            if skipped:
                for msg in skipped:
                    st.warning(msg)
            if added:
                st.rerun()

    st.divider()
    st.markdown("#### Add Student")
    with st.form("add_student_form"):
        name = st.text_input("Name")
        new_student_email = st.text_input("Email")
        mentor_name = st.selectbox("Mentor", list(mentor_options.keys()))
        if st.form_submit_button("Add Student"):
            if not name.strip():
                st.error("Name is required.")
            elif not new_student_email.strip():
                st.error("Email is required.")
            else:
                db.add_student(name.strip(), mentor_options[mentor_name], new_student_email.strip())
                st.success(f"Student {name} added.")
                st.rerun()
