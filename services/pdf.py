import json
import os
import tempfile
from datetime import datetime
from fpdf import FPDF
from config import COMPETENCIES, RATING_OPTIONS

# Upbuild purple
PURPLE = (94, 53, 177)
LIGHT_PURPLE = (237, 231, 246)
DARK_TEXT = (30, 30, 30)
GRAY = (120, 120, 120)
WHITE = (255, 255, 255)
RULE_COLOR = (220, 210, 240)


def _make_logo_png(path: str) -> None:
    """Generate a simple Upbuild logo PNG if no real logo file exists."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (300, 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, 299, 79], radius=12, fill=(*PURPLE, 255))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 38)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 16), "Upbuild", fill=(255, 255, 255, 255), font=font)
    img.save(path)


def generate_pdf(
    assessment: dict,
    student_name: str,
    mentor_name: str,
    transcript: str,
    mentor_feedback: str,
    mentor_ratings: dict,
    output_path: str,
    logo_path: str = "",
) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()

    page_w = pdf.w - pdf.l_margin - pdf.r_margin

    # ── Header bar ──────────────────────────────────────────────────────────
    pdf.set_fill_color(*PURPLE)
    pdf.rect(0, 0, pdf.w, 28, style="F")

    # Logo in top-right of header
    logo_file = logo_path or os.path.join(os.path.dirname(__file__), "..", "assets", "upbuild_logo.png")
    _tmp_logo = None
    if not os.path.exists(logo_file):
        _tmp_logo = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        _tmp_logo.close()
        _make_logo_png(_tmp_logo.name)
        logo_file = _tmp_logo.name

    pdf.image(logo_file, x=pdf.w - 52, y=4, h=20)

    if _tmp_logo:
        try:
            os.unlink(_tmp_logo.name)
        except Exception:
            pass

    # Title text in header
    pdf.set_font("Helvetica", style="B", size=13)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(pdf.l_margin, 8)
    pdf.cell(0, 10, f"Mentoring Assessment  -  Round {assessment['round']}")

    # ── Meta block ───────────────────────────────────────────────────────────
    pdf.set_xy(pdf.l_margin, 34)

    try:
        raw = str(assessment.get("submitted_at", ""))
        date_label = datetime.fromisoformat(raw).strftime("%B %-d, %Y")
    except Exception:
        date_label = str(assessment.get("submitted_at", "N/A"))

    meta_lines = [
        ("Coach", student_name),
        ("Mentor", mentor_name or "-"),
        ("Date Submitted", date_label),
    ]
    for label, value in meta_lines:
        pdf.set_font("Helvetica", style="B", size=10)
        pdf.set_text_color(*GRAY)
        pdf.cell(38, 6, label.upper(), new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(*DARK_TEXT)
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Divider ───────────────────────────────────────────────────────────────
    def rule() -> None:
        pdf.set_draw_color(*RULE_COLOR)
        pdf.set_line_width(0.4)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + page_w, pdf.get_y())
        pdf.ln(4)

    def section_heading(text: str) -> None:
        pdf.ln(3)
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.set_text_color(*PURPLE)
        pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        rule()
        pdf.set_text_color(*DARK_TEXT)

    def label_value(label: str, value: str) -> None:
        pdf.set_font("Helvetica", style="B", size=10)
        pdf.set_text_color(*DARK_TEXT)
        pdf.multi_cell(0, 6, label)
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(60, 60, 60)
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(page_w - 4, 6, value or "(no answer)")
        pdf.set_x(pdf.l_margin)
        pdf.ln(3)

    # ── Competency Ratings ────────────────────────────────────────────────────
    section_heading("Competency Ratings")
    coach_ratings = json.loads(assessment.get("competency_ratings") or "{}")

    col_comp = page_w * 0.52
    col_side = page_w * 0.24

    # Table header
    pdf.set_fill_color(*LIGHT_PURPLE)
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_text_color(*PURPLE)
    pdf.cell(col_comp, 7, "Competency", fill=True, new_x="RIGHT", new_y="TOP")
    pdf.cell(col_side, 7, "Coach", fill=True, new_x="RIGHT", new_y="TOP", align="C")
    pdf.cell(col_side, 7, "Mentor", fill=True, new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*DARK_TEXT)
    fill = False
    current_category = None
    for comp in COMPETENCIES:
        if comp["category"] != current_category:
            current_category = comp["category"]
            pdf.set_font("Helvetica", style="B", size=9)
            pdf.set_text_color(*PURPLE)
            pdf.set_fill_color(248, 245, 255)
            pdf.cell(page_w, 6, f"  {current_category}", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(*DARK_TEXT)
            fill = False

        name = comp["name"]
        coach_val = coach_ratings.get(name, "-")
        mentor_val = mentor_ratings.get(name, "-") if mentor_ratings else "-"
        bg = (250, 248, 255) if fill else WHITE
        pdf.set_fill_color(*bg)
        pdf.cell(col_comp, 6, f"  {name}", fill=True, new_x="RIGHT", new_y="TOP")
        pdf.cell(col_side, 6, str(coach_val), fill=True, new_x="RIGHT", new_y="TOP", align="C")
        pdf.cell(col_side, 6, str(mentor_val), fill=True, new_x="LMARGIN", new_y="NEXT", align="C")
        fill = not fill
    pdf.ln(4)

    # ── Coach Reflections ─────────────────────────────────────────────────────
    section_heading("Coach Reflections")
    reflections = json.loads(assessment.get("reflections") or "{}")
    for question, answer in reflections.items():
        label_value(question, answer)

    # ── Mentor Feedback ───────────────────────────────────────────────────────
    section_heading("Mentor Feedback")
    try:
        feedback_answers = json.loads(mentor_feedback) if mentor_feedback else {}
    except (json.JSONDecodeError, TypeError):
        feedback_answers = {}
    if feedback_answers and isinstance(feedback_answers, dict):
        for question, answer in feedback_answers.items():
            label_value(question, answer)
    else:
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, mentor_feedback or "(no mentor feedback)")

    # ── Footer ────────────────────────────────────────────────────────────────
    pdf.set_y(-14)
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 6, "Upbuild Mentoring Program", align="C")

    pdf.output(output_path)
