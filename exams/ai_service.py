"""
AI Service Layer for Question Generation
=========================================
This module abstracts the AI provider (Groq) for generating MCQ questions
from PDF course material.

Architecture: Service Layer Pattern
- Keeps AI logic separated from views.
- Easy to switch providers in the future.
"""

import os
import json
import re
import requests
import pdfplumber
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


# ============================================================
# Configuration
# ============================================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '').strip()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


# ============================================================
# Custom Exceptions
# ============================================================
class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass


class APIKeyMissingError(AIServiceError):
    """Raised when GROQ_API_KEY is not configured."""
    pass


class PDFExtractionError(AIServiceError):
    """Raised when PDF text extraction fails."""
    pass


class AIGenerationError(AIServiceError):
    """Raised when AI question generation fails."""
    pass


# ============================================================
# PDF Text Extraction
# ============================================================
def extract_text_from_pdf(pdf_file, max_pages=50):
    """
    Extract text content from an uploaded PDF file.

    Args:
        pdf_file: Django UploadedFile object.
        max_pages: Maximum number of pages to extract (safety limit).

    Returns:
        str: Extracted text content.

    Raises:
        PDFExtractionError: If PDF cannot be read or has no text.
    """
    try:
        text_parts = []
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(total_pages, max_pages)

            for page_num in range(pages_to_read):
                page = pdf.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        full_text = "\n\n".join(text_parts).strip()

        if not full_text:
            raise PDFExtractionError(
                "Could not extract any text from this PDF. "
                "The PDF may be image-based (scanned) or empty."
            )

        return full_text

    except PDFExtractionError:
        raise
    except Exception as e:
        raise PDFExtractionError(f"Failed to read PDF: {str(e)}")


# ============================================================
# Prompt Engineering
# ============================================================
def build_generation_prompt(course_text, num_questions, total_marks):
    """
    Build a structured prompt for the AI to generate MCQ questions.

    The prompt requests JSON output to ensure parseable, structured response.
    """
    marks_per_question = round(total_marks / num_questions, 2)

    prompt = f"""You are an expert exam question generator for university students.

TASK: Based on the course material below, generate exactly {num_questions} multiple-choice questions (MCQ).

REQUIREMENTS:
1. Each question must have exactly 4 options (A, B, C, D).
2. Only ONE option must be correct.
3. Wrong options (distractors) must be plausible but clearly incorrect.
4. Questions must cover different topics from the material.
5. Use clear, unambiguous language.
6. Each question is worth {marks_per_question} marks.
7. Respond ONLY in valid JSON format - no explanations, no markdown.

OUTPUT FORMAT (strict JSON):
{{
  "questions": [
    {{
      "question_text": "What is ...?",
      "option_a": "First option",
      "option_b": "Second option",
      "option_c": "Third option",
      "option_d": "Fourth option",
      "correct_option": "A",
      "marks": {marks_per_question}
    }}
  ]
}}

COURSE MATERIAL:
---
{course_text[:8000]}
---

Now generate {num_questions} questions in the JSON format above."""

    return prompt


# ============================================================
# Groq API Call
# ============================================================
def call_groq_api(prompt, timeout=60):
    """
    Send a prompt to Groq API and return the AI-generated response.

    Args:
        prompt: The user prompt to send.
        timeout: Request timeout in seconds.

    Returns:
        str: AI response text.

    Raises:
        APIKeyMissingError: If GROQ_API_KEY is not set.
        AIGenerationError: If the API call fails.
    """
    if not GROQ_API_KEY:
        raise APIKeyMissingError(
            "GROQ_API_KEY is not configured. "
            "Please add your API key to the .env file."
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates "
                           "exam questions in strict JSON format only."
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if response.status_code == 401:
            raise AIGenerationError(
                "Invalid GROQ_API_KEY. Please check your API key in .env."
            )

        if response.status_code == 429:
            raise AIGenerationError(
                "Rate limit exceeded. Please wait a moment and try again."
            )

        if response.status_code != 200:
            raise AIGenerationError(
                f"AI service returned error {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        ai_text = data['choices'][0]['message']['content']
        return ai_text

    except requests.Timeout:
        raise AIGenerationError(
            "AI service did not respond in time. Please try again."
        )
    except requests.RequestException as e:
        raise AIGenerationError(f"Network error: {str(e)}")
    except (KeyError, IndexError):
        raise AIGenerationError("Unexpected AI response format.")


# ============================================================
# JSON Parsing & Validation
# ============================================================
def parse_ai_response(ai_text, expected_count):
    """
    Parse AI's JSON response into a list of question dictionaries.
    Validates structure and content.

    Args:
        ai_text: Raw text from AI.
        expected_count: Expected number of questions.

    Returns:
        list: Validated list of question dicts.

    Raises:
        AIGenerationError: If parsing or validation fails.
    """
    # Extract JSON from response (handle markdown code fences if present)
    json_match = re.search(r'\{.*\}', ai_text, re.DOTALL)
    if not json_match:
        raise AIGenerationError("AI response did not contain valid JSON.")

    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        raise AIGenerationError(f"Failed to parse AI JSON: {str(e)}")

    questions = data.get('questions', [])
    if not isinstance(questions, list) or len(questions) == 0:
        raise AIGenerationError("AI did not return any questions.")

    validated = []
    required_fields = [
        'question_text', 'option_a', 'option_b',
        'option_c', 'option_d', 'correct_option'
    ]

    for idx, q in enumerate(questions):
        # Validate required fields
        missing = [f for f in required_fields if not q.get(f)]
        if missing:
            continue  # Skip malformed questions

        # Validate correct_option
        correct = str(q.get('correct_option', '')).strip().upper()
        if correct not in ['A', 'B', 'C', 'D']:
            continue

        # Validate marks
        try:
            marks = float(q.get('marks', 1))
        except (ValueError, TypeError):
            marks = 1.0

        validated.append({
            'question_text': str(q['question_text']).strip(),
            'option_a': str(q['option_a']).strip(),
            'option_b': str(q['option_b']).strip(),
            'option_c': str(q['option_c']).strip(),
            'option_d': str(q['option_d']).strip(),
            'correct_option': correct,
            'marks': marks,
        })

    if not validated:
        raise AIGenerationError(
            "AI returned questions but none were valid. "
            "Please try again with different parameters."
        )

    return validated


# ============================================================
# Main Public Function
# ============================================================
def generate_questions_from_pdf(pdf_file, num_questions, total_marks):
    """
    Main entry point: Generate MCQ questions from a PDF using Groq AI.

    Args:
        pdf_file: Django UploadedFile (PDF).
        num_questions: How many questions to generate.
        total_marks: Total marks (will be distributed equally).

    Returns:
        list: List of dicts with keys:
              question_text, option_a, option_b, option_c, option_d,
              correct_option, marks.

    Raises:
        APIKeyMissingError, PDFExtractionError, AIGenerationError
    """
    # Step 1: Extract text from PDF
    course_text = extract_text_from_pdf(pdf_file)

    # Step 2: Build prompt
    prompt = build_generation_prompt(course_text, num_questions, total_marks)

    # Step 3: Call Groq API
    ai_response = call_groq_api(prompt)

    # Step 4: Parse and validate
    questions = parse_ai_response(ai_response, num_questions)

    return questions