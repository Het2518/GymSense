# === FILE: report_builder.py ===
# GymSense AI — PDF report generation using pdfkit

import os
import math
from jinja2 import Template
from xhtml2pdf import pisa

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'report.html')
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')



EXERCISE_COLORS = {
    'Squat': '#e74c3c',
    'BenchPress': '#3498db',
    'LegPress': '#2ecc71',
    'Adductor': '#9b59b6',
    'LegCurl': '#f39c12',
    'ArmCurl': '#1abc9c',
    'RopeSkipping': '#e67e22',
    'Running': '#2980b9',
    'Walking': '#27ae60',
    'StairClimber': '#8e44ad',
    'Riding': '#d35400',
    'Null': '#d5d8dc',
}


def generate_timeline_svg(timeline, total_duration_s):
    width = 700
    height = 40
    if total_duration_s <= 0:
        return f'<svg width="{width}" height="{height}"></svg>'

    bars = []
    x = 0
    for entry in timeline:
        dur = entry['duration_s']
        bar_width = max(1, (dur / total_duration_s) * width)
        color = EXERCISE_COLORS.get(entry['exercise'], '#d5d8dc')

        bars.append(
            f'<rect x="{x:.1f}" y="0" width="{bar_width:.1f}" height="{height}" '
            f'fill="{color}" stroke="#fff" stroke-width="0.5">'
            f'<title>{entry["exercise"]} ({entry["start"]}–{entry["end"]}, {dur:.0f}s)</title>'
            f'</rect>'
        )
        x += bar_width

    return f'<svg width="{width}" height="{height}">' + ''.join(bars) + '</svg>'


def generate_tempo_gauge_svg(score, size=60):
    cx, cy = size // 2, size // 2
    r = size // 2 - 4
    circumference = 2 * math.pi * r
    half_circ = circumference / 2

    filled = (score / 100) * half_circ

    if score >= 75:
        color = '#1D9E75'
    elif score >= 50:
        color = '#f39c12'
    else:
        color = '#e74c3c'

    return f'''
<svg width="{size}" height="{size // 2 + 10}">
  <path d="M {cx - r},{cy} A {r},{r} 0 0,1 {cx + r},{cy}"
        fill="none" stroke="#e0e4ea" stroke-width="6"/>
  <path d="M {cx - r},{cy} A {r},{r} 0 0,1 {cx + r},{cy}"
        fill="none" stroke="{color}" stroke-width="6"
        stroke-dasharray="{filled:.1f} {half_circ:.1f}"/>
  <text x="{cx}" y="{cy - 2}" text-anchor="middle"
        font-size="12" font-weight="bold" fill="{color}">{score}</text>
</svg>
'''


def build_report(session_json, coaching_text, session_id):
    os.makedirs(REPORTS_DIR, exist_ok=True)

    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = Template(f.read())

    total_duration_s = session_json['total_duration_min'] * 60

    timeline_svg = generate_timeline_svg(
        session_json.get('timeline', []),
        total_duration_s
    )

    exercises = session_json.get('exercises', [])
    for ex in exercises:
        ex['tempo_gauge_svg'] = generate_tempo_gauge_svg(
            ex.get('tempo_score', 0)
        )

    present_exercises = set(e['exercise'] for e in session_json.get('timeline', []))
    exercise_colors = {k: v for k, v in EXERCISE_COLORS.items() if k in present_exercises}

    html_content = template.render(
        session_date=session_json.get('session_date', 'Unknown'),
        total_duration_min=session_json.get('total_duration_min', 0),
        total_exercises=session_json.get('total_exercises', 0),
        total_reps=session_json.get('total_reps', 0),
        avg_tempo_score=session_json.get('avg_tempo_score', 0),
        timeline_svg=timeline_svg,
        exercise_colors=exercise_colors,
        exercises=exercises,
        muscle_groups_trained=session_json.get('muscle_groups_trained', []),
        coaching_text=coaching_text or 'No coaching data available.',
    )

    pdf_path = os.path.join(REPORTS_DIR, f'{session_id}.pdf')

    # ✅ Generate PDF using xhtml2pdf
    with open(pdf_path, "w+b") as result_file:
        pisa_status = pisa.CreatePDF(
            src=html_content,
            dest=result_file
        )
        if pisa_status.err:
            print(f"[REPORT] Error generating PDF: {pisa_status.err}")

    print(f"[REPORT] PDF saved → {pdf_path}")
    return pdf_path