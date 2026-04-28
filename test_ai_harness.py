"""
AI Test Harness for PawPal+
Runs the RAG-powered AI assistant against a set of predefined scenarios
and validates the responses against expected behaviors.

Run with:  python test_ai_harness.py
"""

from __future__ import annotations

import time
from typing import List, Dict, Callable, Any

from ai_assistant import generate_care_plan


# ---------- Test scenarios ----------
# Each scenario has:
#   - name: short label
#   - context: input string sent to the AI
#   - checks: list of (description, function) pairs that validate the AI output
SCENARIOS: List[Dict[str, Any]] = [
    {
        "name": "Senior dog with arthritis",
        "context": (
            "Owner has 90 minutes available. "
            "Pet: Max, a 9-year-old senior Labrador with arthritis. "
            "Tasks: morning walk (30min), feeding (10min), joint medication (5min), "
            "evening walk (30min)."
        ),
        "expected_keywords": ["senior", "arthritis", "medication"],
        "expected_sources": ["senior_pets"],
    },
    {
        "name": "Young cat with playtime needs",
        "context": (
            "Owner has 60 minutes available. "
            "Pet: Luna, a 2-year-old indoor cat. "
            "Tasks: feeding (10min), litter box cleaning (10min), play session (15min)."
        ),
        "expected_keywords": ["play", "cat", "litter"],
        "expected_sources": ["cat_care"],
    },
    {
        "name": "Multi-pet household",
        "context": (
            "Owner has 120 minutes available. "
            "Pets: Rex (3-year-old dog) and Whiskers (5-year-old cat). "
            "Tasks for Rex: walk (45min), feeding (10min). "
            "Tasks for Whiskers: feeding (10min), play (15min)."
        ),
        "expected_keywords": ["rex", "whiskers"],
        "expected_sources": ["dog_care", "cat_care"],
    },
    {
        "name": "Tight time budget (overbooked)",
        "context": (
            "Owner has only 30 minutes available. "
            "Pet: Buddy, a 4-year-old high-energy dog. "
            "Tasks: walk (60min), feeding (10min), grooming (20min). "
            "(Note: tasks total 90min but only 30min is available.)"
        ),
        "expected_keywords": ["time", "priority"],
        "expected_sources": ["dog_care"],
    },
    {
        "name": "Medication-heavy senior pet",
        "context": (
            "Owner has 75 minutes available. "
            "Pet: Bella, a 12-year-old senior cat with kidney disease. "
            "Tasks: morning meds (5min), feeding (10min), evening meds (5min), "
            "litter box (10min), gentle play (10min)."
        ),
        "expected_keywords": ["medication", "senior"],
        "expected_sources": ["medications"],
    },
]


# ---------- Validation helpers ----------
def check_no_error(result: Dict[str, Any]) -> bool:
    """Output is not an error message."""
    return not result["response"].startswith("ERROR")


def check_keywords_present(result: Dict[str, Any], keywords: List[str]) -> bool:
    """All expected keywords appear in the response (case-insensitive)."""
    text = result["response"].lower()
    return all(kw.lower() in text for kw in keywords)


def check_sources_used(result: Dict[str, Any], expected: List[str]) -> bool:
    """At least one of the expected source documents was retrieved."""
    return any(src in result["sources"] for src in expected)


def check_has_confidence(result: Dict[str, Any]) -> bool:
    """The AI reported a confidence level."""
    return result["confidence"] in {"high", "medium", "low"}


def check_reasonable_length(result: Dict[str, Any]) -> bool:
    """Response is not empty and not absurdly long (50-3000 chars)."""
    length = len(result["response"])
    return 50 <= length <= 3000


# ---------- Test runner ----------
def run_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Run one scenario and return its results dict."""
    print(f"\n--- Running: {scenario['name']} ---")
    start = time.time()
    result = generate_care_plan(scenario["context"])
    elapsed = time.time() - start

    checks = [
        ("No API error", check_no_error(result)),
        ("Reasonable response length", check_reasonable_length(result)),
        ("Confidence reported", check_has_confidence(result)),
        (
            f"Keywords present {scenario['expected_keywords']}",
            check_keywords_present(result, scenario["expected_keywords"]),
        ),
        (
            f"Relevant sources retrieved {scenario['expected_sources']}",
            check_sources_used(result, scenario["expected_sources"]),
        ),
    ]

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)

    for desc, ok in checks:
        symbol = "✅" if ok else "❌"
        print(f"  {symbol} {desc}")

    print(f"  ⏱  Took {elapsed:.2f}s | Confidence: {result['confidence']}")

    return {
        "name": scenario["name"],
        "passed": passed,
        "total": total,
        "confidence": result["confidence"],
        "elapsed": elapsed,
        "checks": checks,
    }


def main() -> None:
    print("=" * 60)
    print("PawPal+ AI Reliability Test Harness")
    print("=" * 60)
    print(f"Running {len(SCENARIOS)} scenarios...\n")

    results = []
    for scenario in SCENARIOS:
        results.append(run_scenario(scenario))
        time.sleep(1)  # gentle rate limiting

    # ---------- Summary report ----------
    print("\n" + "=" * 60)
    print("SUMMARY REPORT")
    print("=" * 60)

    total_passed = sum(r["passed"] for r in results)
    total_checks = sum(r["total"] for r in results)
    pass_rate = (total_passed / total_checks) * 100 if total_checks else 0

    print(f"\nOverall pass rate: {total_passed}/{total_checks} checks "
          f"({pass_rate:.1f}%)")
    print(f"Scenarios run: {len(results)}")

    # Confidence distribution
    confidence_counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0, "none": 0}
    for r in results:
        confidence_counts[r["confidence"]] = confidence_counts.get(r["confidence"], 0) + 1
    print(f"\nConfidence distribution:")
    for level, count in confidence_counts.items():
        if count > 0:
            print(f"  {level}: {count}")

    # Per-scenario breakdown
    print(f"\nPer-scenario results:")
    for r in results:
        status = "PASS" if r["passed"] == r["total"] else "PARTIAL"
        if r["passed"] == 0:
            status = "FAIL"
        print(f"  [{status}] {r['name']}: {r['passed']}/{r['total']} "
              f"({r['elapsed']:.1f}s)")

    avg_time = sum(r["elapsed"] for r in results) / len(results)
    print(f"\nAverage response time: {avg_time:.2f}s")
    print("=" * 60)
    # Save report to a file for the README
    from datetime import datetime
    report_lines = [
        "# AI Reliability Test Report",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        f"**Overall pass rate:** {total_passed}/{total_checks} checks ({pass_rate:.1f}%)",
        f"**Scenarios run:** {len(results)}",
        f"**Average response time:** {avg_time:.2f}s",
        "",
        "## Per-scenario results",
        "",
    ]
    for r in results:
        status = "✅ PASS" if r["passed"] == r["total"] else "⚠️ PARTIAL"
        if r["passed"] == 0:
            status = "❌ FAIL"
        report_lines.append(
            f"- {status} **{r['name']}** — {r['passed']}/{r['total']} "
            f"checks (confidence: {r['confidence']}, {r['elapsed']:.1f}s)"
        )

    report_lines.append("")
    report_lines.append("## Confidence distribution")
    report_lines.append("")
    for level, count in confidence_counts.items():
        if count > 0:
            report_lines.append(f"- {level}: {count}")

    with open("test_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print("\n📄 Report saved to test_report.md")


if __name__ == "__main__":
    main()