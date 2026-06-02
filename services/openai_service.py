import os
import subprocess
import openai


def extract_audio(video_path: str, audio_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-q:a", "5",
            audio_path,
        ],
        check=True,
        capture_output=True,
    )


def transcribe(audio_path: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "[No API key configured]"
    client = openai.OpenAI(api_key=api_key)
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(model="whisper-1", file=f)
    raw = result.text
    return _add_speaker_labels(client, raw)


def _add_speaker_labels(client: openai.OpenAI, raw_transcript: str) -> str:
    prompt = f"""Below is a raw transcript of a coaching session between a coach and their client.

Reformat it with speaker labels on each turn. Use exactly "Coach:" and "Client:" as labels.
- The coach typically asks questions, reflects back, and facilitates exploration.
- The client shares their experience, challenges, and goals.

Return only the formatted transcript — no commentary, no preamble.

Raw transcript:
{raw_transcript}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def generate_ai_review(assessment: dict, transcript: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "[No API key configured]"
    prompt = f"""You are an experienced coaching mentor reviewing a coaching session transcript.

Your audience is NOT the coach.

Your audience is the coach's mentor, who will use your observations to guide a mentoring conversation.

Provide an honest, nuanced assessment of the coaching.

Do not soften feedback unnecessarily. Do not inflate praise. Do not focus on encouragement. Focus on accurate diagnosis.

Assume the mentor wants to understand:
- What the coach does well.
- What the coach tends to do repeatedly.
- What coaching habits are helping.
- What coaching habits are limiting depth.
- What developmental edge would most improve the coach's effectiveness.

Refer to the coach as "the coach" and the other person as "the client."

Support observations with specific examples and quotes.

---

## SESSION TRANSCRIPT

{transcript}

---

## OUTPUT STRUCTURE

# Executive Summary

In 1-3 paragraphs:
- What was the session really about?
- What was the coach's overall effectiveness?
- What stands out most about the coach's style?
- What appears to be the coach's primary developmental edge?

# Coaching Strengths

Identify the 3-7 strongest aspects of the coaching.

For each:

## [Strength]

Describe:
- What the coach did.
- Why it worked.
- How it affected the client.
- Evidence from the transcript.

Focus on recurring strengths rather than isolated moments.

# Developmental Edges

Identify the 3-5 most important developmental edges.

For each:

## [Developmental Edge]

Describe:
- What the coach did.
- Why it may limit coaching effectiveness.
- What a more advanced coach might have done.
- Example questions or approaches that could have deepened the work.

Focus on the highest-leverage growth opportunities.

# Deepest Doorways

Identify the 1-5 moments in the session that contained the greatest transformational potential.

For each:
- Quote the client's statement.
- Explain why it mattered.
- Explain what the coach did.
- Explain where the coaching might have gone if the coach had stayed there longer.

This section should focus on moments where identity, values, fear, assumptions, tension, purpose, or meaning emerged.

# Patterns in the Coach

Based on the session, identify recurring coaching tendencies. Only include patterns supported by evidence from this transcript.

# Mentor Focus

If the mentor had only 15 minutes with this coach, what would be the most valuable topic to discuss?

Explain:
- Why this is the highest-leverage developmental edge.
- What evidence supports it.
- What experiments or practices would help the coach improve.

# Overall Assessment

### Strongest Capabilities
- Bullet list

### Primary Growth Areas
- Bullet list

Rate each 1-10:
- Listening
- Presence
- Curiosity
- Following Client Energy
- Emotional Depth
- Ability to Evoke Insight
- Challenge
- Coaching Depth
- Overall Effectiveness

Finally answer:

"What kind of coach is this person becoming if they continue coaching this way?"

"What is the single biggest thing preventing them from becoming a significantly stronger coach?"

---

Base your evaluation entirely on what you observe in the transcript. Do not reference any self-ratings or written reflections submitted separately."""

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
