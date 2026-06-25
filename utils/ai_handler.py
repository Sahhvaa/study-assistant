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

print(f"✅ AI Provider: {PROVIDER.upper()} | Model: {GROQ_MODEL if PROVIDER == 'groq' else GEMINI_MODEL}")


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

    payload = {'contents': [{'parts': parts}]}
    response = requests.post(GEMINI_URL, json=payload, timeout=120)
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
        # try up to 3 times
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
                # wait 20 seconds then retry
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
    Send text prompt along with multiple images to Gemini.
    Used when we extract diagrams from PDFs.
    """
    parts = [{'text': prompt}]

    # add each image (limit to 5 to avoid overloading)
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

    payload = {'contents': [{'parts': parts}]}
    response = requests.post(GEMINI_URL, json=payload, timeout=120)
    data = response.json()

    if 'error' in data:
        # fallback to text only if image sending fails
        print(f"Image API error — falling back to text only")
        return call_ai(prompt)

    return data['candidates'][0]['content']['parts'][0]['text']


# ─────────────────────────────────────────
# MAIN FUNCTIONS
# ─────────────────────────────────────────

def summarize(text=None, filepath=None, image_paths=None):
    """Generate comprehensive exam-ready study notes."""
    doc_content = text[:30000] if text else ""

    prompt = f"""You are a world-class university professor creating the most comprehensive exam study notes possible.

Your job is to make sure the student NEVER needs to open the original document again.
Cover EVERY SINGLE topic, definition, concept, formula, diagram, and comparison mentioned.

CRITICAL RULES:
- Do NOT skip any topic no matter how small
- Do NOT miss any definition — list ALL of them
- Create detailed comparison tables wherever two or more things are being compared
- Recreate any diagrams as ASCII art or structured text representations
- Use real-world examples for EVERY concept
- Write for a smart university student — detailed but clear

Structure your notes EXACTLY like this:

## 📌 Document Overview
What this document covers, why each topic matters, and real-world applications.

## 📚 Complete Topic Coverage

For EVERY topic in the document create a section:

### [Topic Name]
**📖 Definition:** Clear complete definition

**🔍 Detailed Explanation:**
Thorough explanation. How it works, why it exists, what problem it solves.

**💡 Real-World Example:**
A concrete example from everyday life or industry that makes this click.

**🔗 How It Connects:**
How this topic relates to other concepts in the document.

---

## 📊 Comparison Tables
For EVERY pair or group of concepts that can be compared, create a detailed table:

| Feature | Concept A | Concept B |
|---------|-----------|-----------|
| Definition | ... | ... |
| How it works | ... | ... |
| Use Case | ... | ... |
| Advantages | ... | ... |
| Disadvantages | ... | ... |
| Example | ... | ... |

Create a separate table for every comparison in the document.

## 🔷 Diagrams & Visual Representations
Recreate EVERY diagram, flowchart, or visual from the document.

For flowcharts use this format:
For hierarchies use indented lists:
## 🔑 Complete Definitions Glossary
EVERY term defined in the document:

| Term | Definition | Example |
|------|-----------|---------|
| ... | ... | ... |

## 📐 Formulas, Algorithms & Rules
For EVERY formula or algorithm:
- Write it clearly
- Explain each variable or component
- Show a complete worked example step by step
- State exactly when to use it

## ⚠️ Common Exam Mistakes
Specific mistakes students make on each topic with corrections.

## 🎯 Expected Exam Questions & Model Answers
10 likely exam questions covering ALL major topics with complete model answers.

## ✅ Complete Revision Checklist
Every single concept the student must know before the exam.

---
Document Content:
{doc_content}"""

    # use images if extracted from PDF
    if image_paths:
        return call_ai_with_images(prompt, image_paths)

    return call_ai(prompt, filepath=filepath)


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
    # reduced to 10000 to stay within rate limits

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
- Make it clear enough to teach the concept

Return ONLY a valid JSON array.
No extra text, no explanation, no markdown.
Start directly with [ and end with ]

[{{"question": "...", "answer": "..."}}]

Document Content:
{doc_content}"""

    raw = call_ai(prompt, filepath=filepath).strip()

    # clean markdown if AI wraps in code blocks
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]

    return json.loads(raw.strip())

def call_ai_with_images(prompt, image_paths):
    """Send text prompt along with multiple images to Gemini."""
    parts = [{'text': prompt}]

    # add each image
    for image_path in image_paths[:5]:
        # limit to 5 images to avoid overloading
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

    payload = {'contents': [{'parts': parts}]}
    response = requests.post(GEMINI_URL, json=payload, timeout=120)
    data = response.json()

    if 'error' in data:
        # fallback to text only if image sending fails
        print(f"Image API error: {data['error']['message']} — falling back to text only")
        return call_ai(prompt)

    return data['candidates'][0]['content']['parts'][0]['text']