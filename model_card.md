# Model Card — PawPal+ Applied AI System

A short, structured reflection on the AI system in this project.

---

## 1. System Overview

**Name:** PawPal+ AI Care Plan Generator
**Type:** Retrieval-Augmented Generation (RAG) system + automated reliability test harness
**Base model:** `llama-3.3-70b-versatile` via the [Groq API](https://groq.com)
**Knowledge base:** 5 markdown documents covering dog care, cat care, senior pets, medications, and daily routines (~250 lines of guidelines total)
**Use case:** Generates a personalized daily pet care plan grounded in the knowledge base, given an owner's context (pets, tasks, available time, optional notes).

---

## 2. Intended Use

### Intended users
- Pet owners using PawPal+ to plan their day
- Students/educators studying applied RAG systems

### In-scope tasks
- Suggesting a daily routine based on the user's pets and available time
- Citing which guidelines were used (transparency)
- Flagging risky scheduling decisions (over-budget time, conflicts)

### Out-of-scope tasks
- ❌ Veterinary diagnosis or medical advice
- ❌ Emergency triage
- ❌ Drug-interaction guidance
- ❌ Behavioral diagnosis (e.g., aggression, severe anxiety)

The UI and prompt both reinforce that this is a **planning aid**, not medical advice.

---

## 3. Data

### Knowledge base
The knowledge base was hand-written for this project based on widely-available, general best-practice pet care guidance (exercise, feeding frequency, grooming intervals, etc.). It was authored with deliberately broad, low-risk recommendations — nothing breed-specific or medication-specific that would require veterinary expertise.

### User data
- Owner name, pet names, ages, species, special needs, and tasks are entered through the Streamlit UI.
- Data is stored locally in `data.json`. Nothing is uploaded to any external service except the prompt sent to Groq when the user clicks "Generate AI Care Plan."
- The API key is loaded from `.env` and is **not** committed to the repository (`.env` is in `.gitignore`).

---

## 4. Limitations and Biases

| Limitation | Why it matters |
|---|---|
| Small knowledge base (5 docs) | Cannot answer questions outside what's documented. |
| Keyword retrieval (no embeddings) | Misses semantic matches — e.g., "throwing up" wouldn't match a doc that says "vomiting". |
| LLM hallucination risk | Even with guardrails, the model can produce plausible-sounding but unsupported advice. |
| English only | The knowledge base and prompt are English-only; non-English input is not validated. |
| Generalist guidance | Knowledge base reflects general best practices, not breed- or condition-specific veterinary protocols. |
| No persistent user feedback loop | The system does not learn from corrections; every session is fresh. |

### Bias considerations
- The guidelines are general-purpose and may underweight rare or breed-specific needs (e.g., brachycephalic dog breathing concerns, hairless cats' temperature sensitivity).
- The model's training data may skew toward mainstream Western pet care norms.
- The "confidence" signal is self-reported by the LLM, which is known to be poorly calibrated — the user should treat it as a flag, not a guarantee.

---

## 5. Guardrails

The system implements four guardrails:

1. **Logging** — All retrieval steps, prompt lengths, and API outcomes are logged to the console (`pawpal_ai` logger).
2. **Error handling** — `try/except` around the LLM call returns a graceful error message instead of crashing the UI.
3. **Source transparency** — The UI shows which knowledge base documents were retrieved, so the user can verify the AI's grounding.
4. **Self-reported confidence** — The prompt asks the model to label its confidence as high/medium/low. The Python code parses this and surfaces it to the user.

---

## 6. Reliability Testing

A custom test harness (`test_ai_harness.py`) runs the AI on **5 predefined scenarios** with **5 validators each = 25 checks total**.

### Most recent test run
- **Pass rate:** 23/25 (92%)
- **Average response time:** ~1.6 seconds per scenario
- **Confidence distribution:** 1 high, 4 medium

### Validators
| Validator | What it checks |
|---|---|
| `check_no_error` | Response is not an API error string |
| `check_reasonable_length` | Response is between 50 and 3000 characters |
| `check_has_confidence` | The model self-reported a confidence level |
| `check_keywords_present` | Expected keywords for the scenario appear in the response |
| `check_sources_used` | At least one expected document was retrieved |

### Failures observed
- **"Tight time budget" scenario** — keyword `priority` was not always present in the response; the model often used synonyms like "important" or "essential."
- **"Medication-heavy senior pet" scenario** — `medications.md` was not retrieved because the keyword scorer favored docs that contained more total keyword hits (`cat_care.md` and `senior_pets.md`).

These failures are real findings, not bugs in the harness. They informed the "Limitations" section above.

---

## 7. Reflection on AI Collaboration

I used Claude as a coding pair-programmer for this project.

### A helpful suggestion
When I was deciding how to test the AI, Claude recommended **a custom validator-based harness instead of pytest**, because LLM outputs are non-deterministic and pytest's strict pass/fail model doesn't capture "partial pass" results well. This turned out to be the right call — the harness's pass/partial/fail report is much more informative than a pytest failure stack trace would be, and it's easy for a non-technical reader to skim.

### A flawed suggestion
Early on, Claude suggested using `gemini-2.0-flash` as the model. When I tried it, my Gemini API key returned a 404 because my Google Cloud project didn't have access to the model — and even after switching to `gemini-1.5-flash`, the only models available to me were specialized preview models (robotics, computer-use, deep research). I had to switch the entire SDK from `google-generativeai` to `groq` and rewrite the API call.

**Lesson:** AI-suggested model names and SDK choices need to be verified against your *actual* environment and account permissions, not just trusted blindly. The error message and the resulting fix taught me more about API quota and model availability than the original "happy-path" code would have.

### What surprised me about reliability
I expected the LLM itself to be the weak link. In practice, **the keyword retriever was the weaker component** — when retrieval pulled the wrong documents, even a strong LLM produced grounded-sounding but less-relevant advice. This shifted my thinking: in a small RAG system, retrieval quality often matters more than model quality.

---

## 8. Ethical Considerations

### Could this system be misused?
A user could over-rely on the AI for situations that genuinely need a vet (signs of illness, medication dosing, emergencies). The system mitigates this through:
- Explicit "out-of-scope" framing in this model card
- A prompt that asks the AI to flag risky scenarios
- Visible confidence scores and source attribution
- A README disclaimer that this is a planning aid, not medical advice

### What I would add with more time
- A semantic embeddings retriever (replacing keyword scoring) to fix the medication-doc miss case.
- A "this looks like a vet question — please consult a professional" classifier as a pre-filter.
- A larger, more diverse knowledge base, including breed-specific notes.
- Persistent feedback collection so the system can be evaluated on real user-rated outputs over time.

---

_End of model card._