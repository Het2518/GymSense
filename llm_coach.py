# === FILE: llm_coach.py ===
# GymSense AI — LLM coaching module using Google Gemini API

import os
import json
import re
import logging

from groq import Groq
from backend.config import settings

logger = logging.getLogger('gymsense')

_groq_client = None

def _get_groq_client():
    """Configure Groq API client with key from environment."""
    global _groq_client
    if _groq_client is not None:
        return _groq_client
        
    api_key = settings.groq_api_key or os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        logger.warning("GROQ_API_KEY not set — LLM coaching will be disabled.")
        raise ValueError("GROQ_API_KEY not configured")
        
    _groq_client = Groq(api_key=api_key)
    logger.info("Groq API configured successfully.")
    return _groq_client


# ── Focus-specific appendices ───────────────────────────────────────────────
FOCUS_APPENDIX = {
    'general': '',
    'form': (
        "\n\nFOCUS DIRECTIVE — FORM & TECHNIQUE:\n"
        "Prioritise form analysis. For every exercise where fatigue was detected or tempo "
        "score < 70, provide a precise biomechanical cue (e.g. 'keep chest up through the "
        "eccentric phase of the squat'). Reference exact rep numbers."
    ),
    'progressive_overload': (
        "\n\nFOCUS DIRECTIVE — PROGRESSIVE OVERLOAD:\n"
        "Analyse volume load trends. Based on this session's total reps, sets, and tempo scores, "
        "recommend whether to increase weight, add a set, or deload next session. "
        "Be specific — e.g. 'Add 1 set to BenchPress if tempo score stays above 80'."
    ),
    'recovery': (
        "\n\nFOCUS DIRECTIVE — RECOVERY & READINESS:\n"
        "Focus on rest intervals between sets, rest adequacy flags, and any fatigue signals. "
        "Cross-reference with the user's sleep quality. "
        "Recommend a specific recovery protocol (active recovery, sleep duration, foam rolling targets)."
    ),
}


# ── Prompt builder ────────────────────────────────────────────────────────────
def _build_prompt(session_json, focus='general', user_profile=None):
    """Construct a rich, personalised coaching prompt for Gemini."""

    focus_appendix = FOCUS_APPENDIX.get(focus, '')

    # ── Build user profile block ────────────────────────────────────────────
    profile_block = ""
    if user_profile:
        lines = []

        # Identity
        identity_parts = []
        if user_profile.get('name'):       identity_parts.append(user_profile['name'])
        if user_profile.get('age'):        identity_parts.append(f"{user_profile['age']} years old")
        if user_profile.get('gender'):     identity_parts.append(user_profile['gender'])
        if identity_parts:
            lines.append(f"Athlete: {', '.join(identity_parts)}")

        # Body composition
        if user_profile.get('height') and user_profile.get('weight'):
            h_m = user_profile['height'] / 100
            bmi = round(user_profile['weight'] / (h_m ** 2), 1)
            lines.append(
                f"Body: {user_profile['weight']} kg | {user_profile['height']} cm | BMI: {bmi}"
            )
        elif user_profile.get('weight'):
            lines.append(f"Weight: {user_profile['weight']} kg")

        if user_profile.get('target_weight'):
            delta = round(user_profile['target_weight'] - (user_profile.get('weight') or 0), 1)
            direction = "gain" if delta > 0 else "lose"
            lines.append(
                f"Target weight: {user_profile['target_weight']} kg "
                f"(needs to {direction} {abs(delta)} kg)"
            )

        # Fitness profile
        if user_profile.get('experience_level'):
            lines.append(f"Training experience: {user_profile['experience_level']}")
        if user_profile.get('primary_goal'):
            lines.append(f"Primary goal: {user_profile['primary_goal']}")
        if user_profile.get('workout_frequency'):
            lines.append(f"Trains: {user_profile['workout_frequency']} days/week")
        if user_profile.get('preferred_workout_duration'):
            lines.append(f"Preferred session length: {user_profile['preferred_workout_duration']} min")

        # Lifestyle
        if user_profile.get('dietary_preference'):
            lines.append(f"Diet: {user_profile['dietary_preference']}")
        if user_profile.get('sleep_quality'):
            lines.append(f"Sleep quality: {user_profile['sleep_quality']}")

        # Medical / notes
        if user_profile.get('medical_conditions'):
            lines.append(f"Medical notes / goals: {user_profile['medical_conditions']}")

        if lines:
            profile_block = (
                "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "ATHLETE PROFILE (use this to personalise ALL advice)\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                + "\n".join(f"• {l}" for l in lines)
                + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )

    # ── Compose the full prompt ──────────────────────────────────────────────
    prompt = f"""You are an elite-level AI personal trainer and sports scientist named GymSense Coach.
You analyse wearable sensor data from real gym sessions to deliver deeply personalised, data-driven coaching.
{profile_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION DATA (wearable sensor analysis)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(session_json, indent=2)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COACHING RULES (follow strictly):
1. NEVER give generic advice. Every sentence must reference actual numbers from the session data.
2. Reference the athlete's goal, experience level, and any medical notes when making recommendations.
3. If the athlete wants Weight Loss — emphasise caloric burn, session density, and cardio integration.
4. If the athlete wants Hypertrophy — focus on rep ranges, time under tension, and progressive overload.
5. If the athlete wants Strength — prioritise rest adequacy between sets and neuromuscular fatigue.
6. If sleep quality is Poor or Fair — warn about recovery and reduce volume recommendations accordingly.
7. If fatigue was detected, cite the exact exercise and rep number.
{focus_appendix}

Generate feedback in EXACTLY this format (use these section headers verbatim):

[STRENGTHS]
• (Point 1 — cite a specific number or metric from the data)
• (Point 2 — cite a specific number or metric from the data)

[IMPROVEMENTS]
• (Point 1 — actionable cue referencing specific data, mention exercise + rep if fatigue detected)
• (Point 2 — actionable cue referencing specific data)

[NEXT SESSION]
(One focused paragraph, 4-5 sentences. Recommend: which muscles to prioritise, specific volume adjustments, rest duration targets, and one lifestyle tip aligned to their goal and diet.)

[MOTIVATION]
(One personalised sentence of encouragement that references their primary goal and what they did well today.)

Keep total response under 400 words. Be precise, data-driven, and motivating."""

    logger.info(
        f"Prompt built — profile_provided={bool(user_profile)}, "
        f"focus={focus}, session_exercises={session_json.get('total_exercises', '?')}"
    )
    return prompt


# ── Section parser ────────────────────────────────────────────────────────────
def _parse_sections(raw_text):
    """Parse all four coaching sections from raw LLM output."""
    sections = {
        'strengths': '',
        'improvements': '',
        'next_session': '',
        'motivation': '',
    }

    patterns = {
        'strengths':    r'\[STRENGTHS\]\s*(.*?)(?=\[IMPROVEMENTS\]|\[NEXT SESSION\]|\[MOTIVATION\]|\Z)',
        'improvements': r'\[IMPROVEMENTS\]\s*(.*?)(?=\[NEXT SESSION\]|\[MOTIVATION\]|\Z)',
        'next_session': r'\[NEXT SESSION\]\s*(.*?)(?=\[MOTIVATION\]|\Z)',
        'motivation':   r'\[MOTIVATION\]\s*(.*?)(?=\Z)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            sections[key] = match.group(1).strip()

    return sections


# ── Public API ────────────────────────────────────────────────────────────────
def generate_coaching(session_json, focus='general', user_profile=None):
    """
    Generate personalised coaching using Google Gemini.

    Args:
        session_json   : dict — full session data from session_processor
        focus          : str  — 'general' | 'form' | 'progressive_overload' | 'recovery'
        user_profile   : dict — user physical / lifestyle profile from MongoDB

    Returns:
        dict with keys: strengths, improvements, next_session, motivation, raw
    """
    logger.info(f"generate_coaching called: focus={focus}, profile_provided={bool(user_profile)}")

    try:
        client = _get_groq_client()
    except ValueError as e:
        logger.error(f"Groq config error: {e}")
        return {
            'strengths': 'AI coaching is unavailable — Groq API key not configured.',
            'improvements': str(e),
            'next_session': 'Please set GROQ_API_KEY in your .env file to enable AI coaching.',
            'motivation': '',
            'raw': '',
        }

    prompt = _build_prompt(session_json, focus, user_profile)

    try:
        logger.info("Sending request to Groq API (llama3-70b-8192)...")
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.72,
            max_tokens=1200,
        )
        raw = completion.choices[0].message.content
        logger.info(f"Groq response received ({len(raw)} chars)")
    except Exception as e:
        logger.error(f"Groq API error: {e}", exc_info=True)
        return {
            'strengths': 'Error generating coaching feedback.',
            'improvements': f'API error: {str(e)}',
            'next_session': 'Please try again later.',
            'motivation': '',
            'raw': '',
        }

    sections = _parse_sections(raw)
    sections['raw'] = raw
    logger.info("Coaching sections parsed successfully.")
    return sections


def format_coaching_text(sections):
    """Format parsed coaching sections into a single display string."""
    parts = []
    if sections.get('strengths'):
        parts.append(f"✓ STRENGTHS\n{sections['strengths']}")
    if sections.get('improvements'):
        parts.append(f"↑ IMPROVEMENTS\n{sections['improvements']}")
    if sections.get('next_session'):
        parts.append(f"→ NEXT SESSION\n{sections['next_session']}")
    if sections.get('motivation'):
        parts.append(f"★ {sections['motivation']}")
    return '\n\n'.join(parts) if parts else 'No coaching data available.'
