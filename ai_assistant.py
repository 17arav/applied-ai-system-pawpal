"""
AI Assistant module for PawPal+
Uses Retrieval-Augmented Generation (RAG) with Groq (Llama 3) to generate
personalized pet care plans grounded in a knowledge base of care guidelines.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

from groq import Groq
from dotenv import load_dotenv

# ---------- Setup ----------
load_dotenv()  # Load API key from .env

# Configure logging (guardrail #1: observability)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("pawpal_ai")

# Configure Groq
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    logger.warning("GROQ_API_KEY not found in .env file.")
    client = None
else:
    client = Groq(api_key=API_KEY)

MODEL_NAME = "llama-3.3-70b-versatile"  # Fast, free, capable
KNOWLEDGE_BASE_DIR = Path(__file__).parent / "knowledge_base"


# ---------- Retrieval (the "R" in RAG) ----------
def load_knowledge_base() -> Dict[str, str]:
    """Load all .md files from the knowledge_base/ folder into a dict."""
    kb = {}
    if not KNOWLEDGE_BASE_DIR.exists():
        logger.error("Knowledge base folder not found: %s", KNOWLEDGE_BASE_DIR)
        return kb
    for md_file in KNOWLEDGE_BASE_DIR.glob("*.md"):
        try:
            kb[md_file.stem] = md_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("Failed to read %s: %s", md_file.name, e)
    logger.info("Loaded %d knowledge base documents.", len(kb))
    return kb


def retrieve_relevant_docs(query: str, kb: Dict[str, str], top_k: int = 3) -> List[Tuple[str, str]]:
    """
    Simple keyword-based retrieval.
    Scores each doc by how many query keywords appear in it, returns top_k.
    """
    if not kb:
        return []

    keywords = [w.lower() for w in query.split() if len(w) > 2]
    scored = []
    for name, content in kb.items():
        content_lower = content.lower()
        score = sum(content_lower.count(kw) for kw in keywords)
        scored.append((score, name, content))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored[0][0] == 0:
        logger.info("No keyword matches; returning all docs as fallback.")
        return [(name, content) for _, name, content in scored[:top_k]]

    top = scored[:top_k]
    logger.info("Retrieved docs: %s", [name for _, name, _ in top])
    return [(name, content) for _, name, content in top]


# ---------- Generation (the "G" in RAG) ----------
def build_prompt(user_context: str, retrieved_docs: List[Tuple[str, str]]) -> str:
    """Build a prompt that includes retrieved knowledge + user context."""
    knowledge_section = "\n\n".join(
        f"### {name.replace('_', ' ').title()}\n{content}"
        for name, content in retrieved_docs
    )

    prompt = f"""You are PawPal+, a helpful and responsible pet care assistant.
Use ONLY the pet care guidelines below to inform your advice.
If the user's situation isn't covered by the guidelines, say so honestly.

==== PET CARE GUIDELINES (retrieved from knowledge base) ====
{knowledge_section}

==== USER'S CURRENT SITUATION ====
{user_context}

==== YOUR TASK ====
Generate a clear, friendly daily care plan recommendation. Your response must:
1. Reference specific guidelines you used (cite by section name).
2. Be realistic about the owner's available time.
3. Flag anything risky (missed meds, conflicts, unsafe activities).
4. End with a short "Confidence" line: high / medium / low, and why.

Keep your response under 400 words. Be practical, not preachy.
"""
    return prompt


def generate_care_plan(user_context: str) -> Dict[str, Any]:
    """
    Main RAG pipeline: retrieve relevant docs, build prompt, call LLM, return result.
    Returns a dict with 'response', 'sources', and 'confidence' fields.
    """
    if client is None:
        return {
            "response": "ERROR: Groq API key not configured. Add GROQ_API_KEY to your .env file.",
            "sources": [],
            "confidence": "none",
        }

    # 1. Retrieve
    kb = load_knowledge_base()
    retrieved = retrieve_relevant_docs(user_context, kb, top_k=3)
    sources = [name for name, _ in retrieved]

    # 2. Build prompt
    prompt = build_prompt(user_context, retrieved)
    logger.info("Prompt built. Length: %d chars.", len(prompt))

    # 3. Generate (guardrail: try/except)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=800,
        )
        response_text = completion.choices[0].message.content
        logger.info("Groq call successful.")
    except Exception as e:
        logger.error("Groq API error: %s", e)
        return {
            "response": f"ERROR: AI call failed — {e}",
            "sources": sources,
            "confidence": "none",
        }

    # 4. Extract self-reported confidence (guardrail #2: confidence scoring)
    confidence = "unknown"
    for line in response_text.lower().splitlines():
        if "confidence" in line:
            if "high" in line:
                confidence = "high"
            elif "medium" in line:
                confidence = "medium"
            elif "low" in line:
                confidence = "low"
            break

    return {
        "response": response_text,
        "sources": sources,
        "confidence": confidence,
    }


# ---------- Quick manual test ----------
if __name__ == "__main__":
    test_context = (
        "Owner has 90 minutes available today. "
        "Pet: Max, a 9-year-old senior Labrador with arthritis. "
        "Tasks needed: morning walk (30 min), feeding (10 min), "
        "joint medication (5 min), evening walk (30 min)."
    )
    result = generate_care_plan(test_context)
    print("=" * 60)
    print("AI CARE PLAN")
    print("=" * 60)
    print(result["response"])
    print("\n--- Sources used:", result["sources"])
    print("--- Confidence:", result["confidence"])