import requests
import json
import os
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

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



def call_gemini(prompt, filepath=None):
    """Call Gemini — handles both text and images."""
    if filepath:
        # convert image to base64
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
    response = requests.post(GEMINI_URL, json=payload, timeout=60)
    data = response.json()

    if 'error' in data:
        raise Exception(f"Gemini Error: {data['error']['message']}")

    return data['candidates'][0]['content']['parts'][0]['text']


def call_groq(prompt):
    """Call Groq — fast, free, text only."""
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': GROQ_MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 4096
    }
    response = requests.post(
        GROQ_URL,
        json=payload,
        headers=headers,
        timeout=60
    )
    data = response.json()

    if 'error' in data:
        raise Exception(f"Groq Error: {data['error']['message']}")

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


def summarize(text=None, filepath=None):
    """Generate detailed exam-ready study notes."""
    doc_content = text[:20000] if text else ""

    prompt = f"""You are an expert university tutor creating exam-ready study notes.

Your goal is to help a student deeply understand this topic and score well in their exam.

Write like a brilliant senior student explaining to a classmate:
- Be detailed and thorough — not oversimplified
- Always include real-world examples that make abstract concepts click
- Use analogies where helpful
- Cover everything a student needs to know for their exam

Structure your notes EXACTLY like this:

## 📌 What This Is About
A clear introduction explaining what this topic covers, its importance, and real-world applications.

## 📚 Core Concepts — Deep Explanation

For EACH major concept:
### [Concept Name]
**What it is:** Clear, detailed explanation

**How it works:** Step-by-step breakdown if needed

**Real-world example:** A concrete example from everyday life, industry, or science that makes this concept easy to visualize and remember

**What you must remember:** The key insight about this concept

## 🔑 Key Terms & Definitions
List every important term with a clear definition and a one-line example.

## 📐 Formulas, Rules & Theorems
(Skip if not applicable)
For each formula/rule:
- Write it clearly
- Explain what each variable/component means
- Show a worked example
- State when to use it

## 🔗 How Concepts Connect
Explain how the different topics in this document relate to each other. Draw connections a student might miss.

## ⚠️ Common Exam Mistakes
List specific mistakes students make and how to avoid them.

## 🎯 Expected Exam Questions & Model Answers
Give 5 likely exam questions with thorough model answers that would score full marks.

## ✅ Last-Minute Revision Checklist
Bullet list of the absolute must-know points before walking into the exam.

---
Document Content:
{doc_content}"""

    return call_ai(prompt, filepath=filepath)


def chat(question, text=None, filepath=None):
    """Answer a question about the document like an expert tutor."""
    doc_content = text[:20000] if text else ""

    prompt = f"""You are an expert tutor helping a student understand their study material.

Answer this question thoroughly and clearly:

Question: {question}

Guidelines for your answer:
- Give a detailed explanation — not just a one-line answer
- Use a real-world example or analogy to make it memorable
- If it involves calculation or steps, show them clearly
- If it is a conceptual question, explain the WHY behind it
- End with a one-line "Key Takeaway" that summarizes the core point

---
Document Content:
{doc_content}"""

    return call_ai(prompt, filepath=filepath)


def generate_flashcards(text=None, filepath=None):
    """Generate exam-focused flashcards."""
    doc_content = text[:20000] if text else ""

    prompt = f"""You are an exam preparation expert creating flashcards for a university student.

Create 15 high-quality flashcards from this document.

Focus on:
- Key definitions that must be memorized
- Important concepts and how they work
- Formulas or rules with brief explanations
- Common exam topics and tricky questions
- Concepts that are commonly misunderstood

Rules for answers:
- Make answers detailed enough to actually teach the concept
- 2-4 sentences per answer — not too short, not too long
- Include a mini example in the answer where helpful

Return ONLY a valid JSON array.
No extra text, no explanation, no markdown formatting whatsoever.
Start directly with [ and end with ]

[{{"question": "...", "answer": "..."}}]

Document Content:
{doc_content}"""

    raw = call_ai(prompt, filepath=filepath).strip()

   
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]

    return json.loads(raw.strip())