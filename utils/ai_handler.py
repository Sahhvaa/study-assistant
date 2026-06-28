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

def summarize(text=None, filepath=None, image_paths=None, syllabus=None):
    """Generate comprehensive exam-ready study notes using Gemini."""
    doc_content = text[:80000] if text else ""

    # build syllabus section
    if syllabus and syllabus.strip():
        syllabus_section = f"""
SYLLABUS TO FOLLOW:
ONLY cover topics mentioned in this syllabus.
Ignore everything in the document NOT in the syllabus.
Give the most attention to topics that appear most prominently in the syllabus.

{syllabus}

---"""
    else:
        syllabus_section = ""

    prompt = f"""You are an expert, empathetic AI Study Assistant designed to help students learn complex material easily. Your task is to analyze the provided source document and generate comprehensive, highly readable, and structured study notes.

{syllabus_section}

Follow these strict structural and formatting guidelines:

1. TONE AND COMPLEXITY:
   - Write in a clear, engaging, and easy-to-understand tone, as if explaining to a student who is new to the topic.
   - Do not make the notes too short or summarized. Retain critical technical details, definitions, and explanations, but simplify the language.

2. STRUCTURE AND VISUALS:
   - Use a clear hierarchy with Markdown headings (##, ###).
   - Use bullet points, bold text for key terms, and horizontal rules (---) to separate major concepts to ensure maximum scannability.
   - DIAGRAMS/GRAPHS: If the source document contains or heavily references specific diagrams, charts, or graphs, describe them vividly in a structured blockquote block explaining what the visual represents and its key data points.
   - Format diagram descriptions like this:
     > [Diagram Name]: Description of what it shows and its key components.

3. COMPARATIVE ANALYSIS (CRITICAL):
   - Identify the most crucial comparable topics, theories, or mechanisms within the text.
   - Create a Markdown comparison table contrasting these elements based on relevant criteria such as Purpose, Mechanism, Pros/Cons, and Complexity.

4. WORKED PROBLEMS:
   - If the document contains solved problems or numerical examples, include them fully with all steps shown clearly.
   - Format like this:
     Problem: [statement]
     Given: [values]
     Solution: step by step
     Answer: [final answer]

5. DEFINITIONS GLOSSARY:
   - At the end, include a table of ALL key terms and their definitions.
   - Format:
     | Term | Definition |
     |------|-----------|
     | term | definition |

6. EXAM PREPARATION:
   - After the glossary, add a section called "What Will Come in the Exam" listing likely questions per topic.
   - End with a "Must-Know Before the Exam" bullet checklist of the most critical points.

7. GUARDRAILS:
   - Rely ONLY on the clear facts directly mentioned in the provided context. Do not assume, extrapolate, or bring in outside information.
   - Anything not directly mentioned in the context is considered completely untruthful and unsupported.

---
Document Content:
{doc_content}"""

    if image_paths:
        return call_ai_with_images(prompt, image_paths)

    # always use Gemini for summarization
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
- End with a "Key Takeaway" that summarizes the core point in one line

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