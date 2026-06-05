import json
from fpdf import FPDF
from config import COMPETENCIES, RATING_OPTIONS


def generate_pdf(
    assessment: dict,
    student_name: str,
    transcript: str,
    mentor_feedback: str,
    mentor_ratings: dict,
    output_path: str,
) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def heading(text: str, size: int = 14) -> None:
        pdf.set_font("Helvetica", style="B", size=size)
        pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def body(text: str, size: int = 11) -> None:
        pdf.set_font("Helvetica", size=size)
        pdf.multi_cell(0, 7, text)
        pdf.ln(3)

    heading(f"Mentoring Assessment - Round {assessment['round']}", size=16)
    body(f"Coach: {student_name}")
    body(f"Submitted: {assessment.get('submitted_at', 'N/A')}")
    pdf.ln(4)

    # Competency ratings — coach vs mentor side by side
    heading("Competency Ratings")
    coach_ratings = json.loads(assessment.get("competency_ratings") or "{}")
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.cell(90, 7, "Competency", new_x="RIGHT", new_y="TOP")
    pdf.cell(50, 7, "Coach", new_x="RIGHT", new_y="TOP")
    pdf.cell(50, 7, "Mentor", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for comp in COMPETENCIES:
        name = comp["name"]
        coach_val = coach_ratings.get(name, "-")
        mentor_val = mentor_ratings.get(name, "-") if mentor_ratings else "-"
        pdf.cell(90, 6, name, new_x="RIGHT", new_y="TOP")
        pdf.cell(50, 6, str(coach_val), new_x="RIGHT", new_y="TOP")
        pdf.cell(50, 6, str(mentor_val), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    heading("Coach Reflections")
    reflections = json.loads(assessment.get("reflections") or "{}")
    for question, answer in reflections.items():
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.multi_cell(0, 7, question)
        pdf.set_x(pdf.l_margin)
        body(answer or "(no answer)")
    pdf.ln(4)

    heading("Session Transcript")
    body(transcript or "(no transcript)")
    pdf.ln(4)

    heading("Mentor Feedback")
    try:
        feedback_answers = json.loads(mentor_feedback) if mentor_feedback else {}
    except (json.JSONDecodeError, TypeError):
        feedback_answers = {}
    if feedback_answers and isinstance(feedback_answers, dict):
        for question, answer in feedback_answers.items():
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.multi_cell(0, 7, question)
            pdf.set_x(pdf.l_margin)
            body(answer or "(no answer)")
    else:
        body(mentor_feedback or "(no mentor feedback)")

    pdf.output(output_path)
