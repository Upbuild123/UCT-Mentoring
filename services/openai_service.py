import os
import subprocess
import openai


def extract_audio(video_path: str, audio_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
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
    return result.text


def generate_ai_review(assessment: dict, transcript: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "[No API key configured]"
    import json
    ratings = json.loads(assessment.get("competency_ratings") or "{}")
    reflections = json.loads(assessment.get("reflections") or "{}")
    ratings_text = "\n".join(f"- {k}: {v}/5" for k, v in ratings.items())
    reflections_text = "\n".join(f"- {k}: {v}" for k, v in reflections.items())
    prompt = f"""You are a mentoring program coach reviewing a student's self-assessment for round {assessment['round']}.

Competency ratings (1-5):
{ratings_text}

Student reflections:
{reflections_text}

Session transcript:
{transcript}

Provide a constructive, encouraging review (3-5 paragraphs) highlighting strengths, areas for growth, and specific recommendations."""

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
