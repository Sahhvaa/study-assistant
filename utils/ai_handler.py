import requests
import json
import os
import base64
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
PROVIDER = os.getenv('AI_PROVIDER', 'groq').lower()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

GEMINI_MODEL = 'gemini-2.5-flash'
GROQ_MODEL = 'llama-3.3-70b-versatile'

GEMINI_URL = (
    f'https://generativelanguage.googleapis.com/v1beta/'
    f'models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}'
)
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'

print(f"✅ AI Provider: {PROVIDER.upper()} | Summarize: GEMINI | Chat/Cards: {GROQ_MODEL}")


# ─────────────────────────────────────────
# API CALLERS
# ─────────────────────────────────────────

def call_gemini(prompt, filepath=None):
    """Call Gemini — handles both text and images."""
    if filepath:
        with open(filepath, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        ext = Path(filepath).suffix.lower().lstrip('.')
        mime_type = 'image/jpeg' if ext == 'jpg' else f'image/{ext}'
        parts = [
            {'text': prompt},
            {'inline_data': {'mime_type': mime_type, 'data': image_data}}
        ]
    else:
        parts = [{'text': prompt}]

    payload = {
        'contents': [{'parts': parts}],
        'generationConfig': {
            'maxOutputTokens': 8192,
            'temperature': 0.3
        }
    }

    response = requests.post(GEMINI_URL, json=payload, timeout=180)
    data = response.json()

    if 'error' in data:
        raise Exception(f"Gemini Error: {data['error']['message']}")

    return data['candidates'][0]['content']['parts'][0]['text']


def call_groq(prompt):
    """Call Groq — fast, free, text only. Auto retries on rate limit."""
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': GROQ_MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 4096
    }

    for attempt in range(3):
        response = requests.post(
            GROQ_URL,
            json=payload,
            headers=headers,
            timeout=60
        )
        data = response.json()

        if 'error' in data:
            error_msg = data['error']['message']
            if 'rate limit' in error_msg.lower() and attempt < 2:
                print(f"⏳ Rate limit hit. Waiting 20s... (attempt {attempt + 2}/3)")
                time.sleep(20)
                continue
            raise Exception(f"Groq Error: {error_msg}")

        return data['choices'][0]['message']['content']


def call_ai(prompt, filepath=None):
    """
    Router — sends to the right AI.
    Images always go to Gemini (vision support).
    Text goes to Groq or Gemini based on .env setting.
    """
    if filepath:
        return call_gemini(prompt, filepath=filepath)
    elif PROVIDER == 'gemini':
        return call_gemini(prompt)
    else:
        return call_groq(prompt)


def call_ai_with_images(prompt, image_paths):
    """
    Send text prompt with multiple images to Gemini.
    Used when diagrams are extracted from PDFs.
    """
    parts = [{'text': prompt}]

    for image_path in image_paths[:5]:
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            ext = Path(image_path).suffix.lower().lstrip('.')
            mime_type = 'image/jpeg' if ext in ['jpg', 'jpeg'] else f'image/{ext}'
            parts.append({
                'inline_data': {
                    'mime_type': mime_type,
                    'data': image_data
                }
            })
        except Exception as e:
            print(f"Could not add image {image_path}: {e}")

    payload = {
        'contents': [{'parts': parts}],
        'generationConfig': {
            'maxOutputTokens': 8192,
            'temperature': 0.3
        }
    }
    response = requests.post(GEMINI_URL, json=payload, timeout=180)
    data = response.json()

    if 'error' in data:
        print(f"Image API error — falling back to text only")
        return call_gemini(prompt)

    return data['candidates'][0]['content']['parts'][0]['text']


# ─────────────────────────────────────────
# MAIN FUNCTIONS
# ─────────────────────────────────────────

def summarize(text=None, filepath=None, image_paths=None):
    """Generate comprehensive exam-ready study notes using Gemini."""
    doc_content = text[:80000] if text else ""

    prompt = f"""You are a brilliant senior student who just finished reading this entire document.
You are now writing study notes for your classmates who have NO time to read the original.

YOUR MISSION:
Go through this document topic by topic and write notes that:
- Cover EVERY SINGLE topic, EVERY definition, EVERY concept — absolutely nothing gets skipped
- Are simplified enough to understand quickly but detailed enough to write correct exam answers
- Include ALL diagrams, figures, charts, and tables recreated in text form
- Feel like handwritten notes from the smartest student in class

STRICT RULES:
- Do NOT skip any topic — even small ones can appear in exams
- Do NOT write "the document says..." — just write the content directly
- Keep all technical terms but explain them clearly
- ALWAYS give a real-world example for each concept
- Cover ALL worked problems and examples from the document with full solutions

---

Use this format for each topic:

## [Topic Name]

[Write 2-4 paragraphs explaining this topic clearly. Keep all technical details but explain them in a way that is easy to understand and write in an exam.]

**In simple terms:** [One sentence that captures the core idea]

**Real-world example:** [A concrete relatable example]

**Key definition to memorize:**
> [Exact definition formatted as a blockquote]

[Cover each subtopic with the same level of detail]

---

When you find a DIAGRAM or FIGURE recreate it:

**📊 Figure: [Name]**
[ASCII or text representation of the diagram]

*What this shows: [Brief explanation of what the diagram means]*

---

When items are COMPARED create a table:

**📊 Comparison: [Topic]**

| Feature | [Option A] | [Option B] |
|---------|-----------|-----------|
| Definition | ... | ... |
| How it works | ... | ... |
| When to use | ... | ... |
| Advantages | ... | ... |
| Disadvantages | ... | ... |
| Example | ... | ... |

---

When you find FORMULAS or ALGORITHMS:

**📐 Formula: [Name]**

[Formula written clearly]

Variables:
- [Variable 1] = [what it means]
- [Variable 2] = [what it means]

**Example:** [Worked example step by step]

---

When you find WORKED PROBLEMS include them fully:

**✏️ Problem: [Title]**

Given: [what is given]

Solution:
- Step 1: [...]
- Step 2: [...]

Answer: [final answer]

---

After covering ALL topics add these final sections:

## 📝 All Definitions at a Glance

| Term | Definition |
|------|-----------|
| [every single term from document] | [clear definition] |

## 🎯 What Will Definitely Come in the Exam
[For each major topic write what type of question is likely to be asked]

## ✅ Must-Know Before the Exam
[Bullet list of the most critical points — one line each]

---
Document Content:
{doc_content}"""

    # always use Gemini for summarization
    # Gemini has bigger context window and larger output than Groq
    if image_paths:
        return call_ai_with_images(prompt, image_paths)

    return call_gemini(prompt)


def chat(question, text=None, filepath=None):
    """Answer a question about the document like an expert tutor."""
    doc_content = text[:20000] if text else ""

    prompt = f"""You are an expert university tutor helping a student understand their study material.

Answer this question thoroughly and clearly:

Question: {question}

Guidelines:
- Give a detailed explanation — not just a one-line answer
- Use a real-world example or analogy to make it memorable
- If it involves calculation or steps, show them clearly
- If it is conceptual, explain the WHY behind it
- If relevant, mention how this connects to other topics
- End with a "💡 Key Takeaway" that summarizes the core point in one line

---
Document Content:
{doc_content}"""

    return call_ai(prompt, filepath=filepath)


def generate_flashcards(text=None, filepath=None):
    """Generate exam-focused flashcards."""
    doc_content = text[:10000] if text else ""

    prompt = f"""You are an exam preparation expert creating flashcards for a university student.

Create 10 high-quality flashcards from this document.

Focus on:
- Key definitions that must be memorized
- Important concepts and how they work
- Formulas or rules with brief explanations
- Topics most likely to appear in exams
- Concepts commonly misunderstood

Rules for answers:
- 2-3 sentences maximum per answer
- Include a mini example where helpful
- Make it clear enough to actually teach the concept

IMPORTANT: Return ONLY a valid JSON array.
No extra text before or after.
No markdown code blocks.
No explanation.
Start your response with [ and end with ]

[{{"question": "...", "answer": "..."}}]

Document Content:
{doc_content}"""

    raw = call_ai(prompt, filepath=filepath).strip()

    # remove markdown code blocks if present
    if '```' in raw:
        parts = raw.split('```')
        for part in parts:
            part = part.strip()
            if part.startswith('json'):
                part = part[4:].strip()
            if part.startswith('['):
                raw = part
                break

    # find the JSON array in the response
    start = raw.find('[')
    end = raw.rfind(']') + 1
    if start != -1 and end > start:
        raw = raw[start:end]

    return json.loads(raw)