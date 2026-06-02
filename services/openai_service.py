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
    prompt = f"""You are a master coach evaluating a coaching session transcript using the Upbuild Coaching Training framework. Your feedback is generous and rigorous, evidence-based, and always oriented toward the coach's growth.

## SESSION TRANSCRIPT

{transcript}

---

## EVALUATION FRAMEWORK

### Rating Scale
- 1 (Not Demonstrated): Skill not visible in this session
- 2 (Emerging): Present but inconsistent or underdeveloped
- 3 (Competent): Demonstrated reliably and effectively
- 4 (Exceptional): Mastery-level with nuance and impact

Half-points (e.g., 2.5) are acceptable. Most coaches in training operate around 2 on most skills.

---

### META-SKILLS

**1. Know Yourself**
Uses self-knowledge and self-work to help the client discover who they are.
Look for: Does the coach demonstrate awareness of their own patterns/triggers? Is the coach coaching from their own inner work - not just technique? Does the coach use self-knowledge skillfully rather than projecting? Can you sense the coach's groundedness in their own development? Does the coach share personal experience in service of the client (not self-indulgently)?

**2. Experiment and Learn**
Holds an experimental mindset, interacts with the client in new ways, and takes risks for the sake of the client.
Look for: Does the coach try something new or unexpected? Is there willingness to risk being wrong? Does the coach follow intuition even when it's uncertain? Does the coach recover gracefully when an experiment doesn't land? Is the client invited into the experiment or is it done to them?

**3. Serve Not Fix**
Focuses on coaching the whole person and their whole life, not the problem or issue; avoids being an expert and advice-giver.
Look for: Is the coach working with the person or the problem? Are there moments of advice-giving, teaching, or fixing disguised as coaching? Does the coach trust the client's wisdom or impose their own? When the coach offers a framework, does the client discover through it or receive it passively? Is there space for the client to sit with discomfort rather than being rescued?

**4. Call on the Creative**
Accesses and coaches from the creative level of consciousness to help the client access and live from their creative consciousness.
Look for: Does the coach help the client shift from reactive to creative? Is there attention to the field (energy, body, space, metaphor) and not just content? Does the coach use or invite imagery, somatic awareness, or creative reframing? Are there moments where the conversation transcends problem-solving into something deeper?

---

### CORE SKILLS

**1. Co-Creating and Maintaining the Relationship**
Establishes agreements; cultivates trust, safety and mutual respect; partners around overall client outcomes.
Look for: Is trust evident in how the client shows up? Does the client bring vulnerability, risk, real material? Does the coach maintain appropriate boundaries while being warm? Is there a sense of partnership rather than hierarchy?

**2. Structuring the Coaching Session**
Follows 10/80/10 structure: 10% (topic, agenda, desired outcomes), 80% (exploration and deepening of learning), 10% (action, next steps, accountability).
Look for: Is there a clear opening that establishes what to work on? Does the session have a discernible arc? Does the coach hold multiple agendas (presenting, deeper, transformational)? Is the close clean - does the client synthesize their own learning? Who manages time and transitions?

**3. Listening**
Offers full presence, listens without judgment, and hears what the client might be saying separate from their words.
Look for: Does the coach hear what's underneath the words? Are there moments where the coach reflects something the client didn't explicitly say? Is the coach tracking energy shifts, not just content? Is the coach's own agenda quiet enough to hear the client?

**4. Asking Curious and Powerful Questions**
Practices open-ended questions that invite exploration of possibility and the unknown.
Look for: Are questions genuinely open-ended or leading? Do questions open new territory or confirm the coach's hypothesis? Is there a balance of questions and other interventions? Does the coach resist the urge to fill silence after a powerful question?

**5. Balancing Action and Learning**
Invites the client to engage in personal reflection to deepen their learning and take meaningful action toward goals.
Look for: Does the client leave with both insight and a concrete next step? Is action grounded in learning or just task-oriented? Who generates the action - coach or client? Does the coach check that action feels owned, not assigned? Is there sufficient exploration before moving to action?

---

### COMMON PITFALLS TO WATCH FOR
- Teaching or mentoring disguised as coaching
- Coach doing more talking than the client
- Reassurance when the client needs to stay with discomfort
- Leading questions that confirm the coach's hypothesis
- Rushing past emotion to get to insight
- Closing a session without the client synthesizing their own learning
- Over-synthesizing on the client's behalf

---

## OUTPUT STRUCTURE

Write the evaluation as a narrative document with exactly these five sections:

**1. META-SKILLS ASSESSMENT**
For each of the 4 meta-skills: rating, 1-2 paragraphs of evidence and analysis. Name specific transcript moments. Name what's working and what could deepen.

**2. CORE SKILLS ASSESSMENT**
For each of the 5 core skills: rating, 1 paragraph of evidence and analysis. Be concise but specific.

**3. SIGNATURE MOMENTS**
Identify 2-4 key moments from the session. Quote or paraphrase the transcript. Explain why each moment matters.

**4. DEVELOPMENTAL EDGE**
Name the ONE primary growth area for the coach based on this session. Offer one concrete practice to try.

**5. OVERALL**
2-3 sentences synthesizing the session's quality and the coach's development trajectory.

---

IMPORTANT: Base your evaluation entirely on what you observe in the transcript. Do not reference or comment on any self-ratings or written reflections the coach may have submitted separately."""

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
