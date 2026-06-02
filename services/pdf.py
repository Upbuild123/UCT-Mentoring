import json
from fpdf import FPDF


def generate_pdf(
    assessment: dict,
    student_name: str,
    transcript: str,
    ai_review: str,
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
    body(f"Student: {student_name}")
    body(f"Submitted: {assessment.get('submitted_at', 'N/A')}")
    pdf.ln(4)

    heading("Competency Ratings")
    ratings = json.loads(assessment.get("competency_ratings") or "{}")
    for comp, score in ratings.items():
        body(f"{comp}: {score}/5")
    pdf.ln(4)

    heading("Reflections")
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

    heading("AI Review")
    body(ai_review or "(no review)")

    pdf.output(output_path)
