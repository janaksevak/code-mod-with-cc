#!/usr/bin/env python3
"""
Confidence Scorer — Computes a migration confidence score for a slice.

Score formula (0-100):
  50% — Byte-for-byte output match ratio (golden dataset tests)
  20% — Code path coverage (test cases / known code paths)
  15% — Quirks documentation completeness
  10% — Semantic equivalence after diff rules
   5% — Structural quality (clean compilation, no warnings)

Thresholds:
  >= 95  → Auto-approve (high confidence)
  80-94  → Human review recommended
  < 80   → Human review required (gate blocks commit)

Usage:
  python3 confidence_scorer.py --results test_results/validation.json --quirks empsal-quirks.md --output artifacts/score.json
  python3 confidence_scorer.py --results test_results/validation.json --threshold 95
"""

import argparse
import json
import os
import re
from datetime import datetime


class ConfidenceScorer:
    """Computes confidence score for a migration slice."""

    WEIGHTS = {
        "byte_match": 0.50,
        "coverage": 0.20,
        "quirks_documented": 0.15,
        "semantic_match": 0.10,
        "structural": 0.05,
    }

    THRESHOLDS = {
        "auto_approve": 95,
        "review_recommended": 80,
        "review_required": 0,  # Below 80
    }

    def __init__(self, config: dict = None):
        if config:
            self.WEIGHTS.update(config.get("weights", {}))
            self.THRESHOLDS.update(config.get("thresholds", {}))

    def score(
        self,
        test_results: dict = None,
        quirks_doc_path: str = None,
        semantic_diff_results: dict = None,
        build_clean: bool = True,
    ) -> dict:
        """Compute the confidence score."""
        components = {}

        # 1. Byte match ratio
        components["byte_match"] = self._score_byte_match(test_results)

        # 2. Coverage ratio
        components["coverage"] = self._score_coverage(test_results)

        # 3. Quirks documentation
        components["quirks_documented"] = self._score_quirks(quirks_doc_path, test_results)

        # 4. Semantic match
        components["semantic_match"] = self._score_semantic(semantic_diff_results)

        # 5. Structural quality
        components["structural"] = 100.0 if build_clean else 50.0

        # Weighted total
        total = sum(
            components[k] * self.WEIGHTS[k]
            for k in self.WEIGHTS
        )

        # Determine gate action
        if total >= self.THRESHOLDS["auto_approve"]:
            gate = "auto_approve"
            gate_message = "High confidence. Auto-approve eligible."
        elif total >= self.THRESHOLDS["review_recommended"]:
            gate = "review_recommended"
            gate_message = "Good confidence. Human review recommended before merge."
        else:
            gate = "review_required"
            gate_message = "Low confidence. Human review REQUIRED. Do not merge without approval."

        return {
            "score": round(total, 2),
            "gate": gate,
            "gate_message": gate_message,
            "components": {k: round(v, 2) for k, v in components.items()},
            "weights": dict(self.WEIGHTS),
            "thresholds": dict(self.THRESHOLDS),
            "scored_at": datetime.now().isoformat(),
        }

    def _score_byte_match(self, test_results: dict) -> float:
        if not test_results:
            return 0.0
        total = test_results.get("total_tests", 0)
        passed = test_results.get("passed", test_results.get("both_passed", 0))
        if total == 0:
            return 0.0
        return (passed / total) * 100.0

    def _score_coverage(self, test_results: dict) -> float:
        if not test_results:
            return 0.0

        # Coverage can be estimated from test case diversity
        total = test_results.get("total_tests", 0)
        categories = test_results.get("categories_covered", [])

        # Expected categories for a typical migration
        expected_categories = {"normal", "boundary", "overflow", "error", "empty"}

        if categories:
            covered = len(set(categories) & expected_categories)
            return (covered / len(expected_categories)) * 100.0

        # Fallback: estimate from test count
        if total >= 10:
            return 90.0
        elif total >= 5:
            return 70.0
        elif total >= 1:
            return 40.0
        return 0.0

    def _score_quirks(self, quirks_doc_path: str, test_results: dict) -> float:
        if not quirks_doc_path or not os.path.exists(quirks_doc_path):
            return 0.0

        try:
            with open(quirks_doc_path) as f:
                content = f.read()
        except OSError:
            return 0.0

        # Check for key sections that a good quirks doc should have
        expected_topics = [
            r"overflow",
            r"truncat",
            r"round",
            r"newline|line.?separator",
            r"padding|space.?fill",
            r"empty.?file|empty.?input",
        ]

        found = sum(1 for topic in expected_topics if re.search(topic, content, re.IGNORECASE))
        return (found / len(expected_topics)) * 100.0

    def _score_semantic(self, semantic_diff_results: dict) -> float:
        if not semantic_diff_results:
            return 100.0  # No semantic diff rules = assume pass

        total_rules = semantic_diff_results.get("total_rules", 0)
        passed_rules = semantic_diff_results.get("passed_rules", 0)

        if total_rules == 0:
            return 100.0
        return (passed_rules / total_rules) * 100.0


def load_test_results(path: str) -> dict:
    """Load test results from various formats."""
    if not path or not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Confidence Scorer")
    parser.add_argument("--results", help="Path to test results JSON")
    parser.add_argument("--quirks", help="Path to quirks documentation")
    parser.add_argument("--semantic-diff", help="Path to semantic diff results JSON")
    parser.add_argument("--build-clean", action="store_true", default=True)
    parser.add_argument("--no-build-clean", dest="build_clean", action="store_false")
    parser.add_argument("--threshold", type=float, help="Override auto-approve threshold")
    parser.add_argument("--output", help="Write score to JSON file")
    parser.add_argument("--config", help="Path to modernization.config.json")
    args = parser.parse_args()

    # Load config
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config) as f:
            full_config = json.load(f)
            config = full_config.get("scoring", {})

    if args.threshold:
        config.setdefault("thresholds", {})["auto_approve"] = args.threshold

    scorer = ConfidenceScorer(config)

    test_results = load_test_results(args.results)
    semantic_diff = load_test_results(args.semantic_diff) if args.semantic_diff else None

    result = scorer.score(
        test_results=test_results,
        quirks_doc_path=args.quirks,
        semantic_diff_results=semantic_diff,
        build_clean=args.build_clean,
    )

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Score written to {args.output}")

    # Display
    print(f"\n{'='*50}")
    print(f"  CONFIDENCE SCORE: {result['score']:.1f} / 100")
    print(f"  GATE: {result['gate'].upper()}")
    print(f"  {result['gate_message']}")
    print(f"{'='*50}")
    print(f"\n  Component breakdown:")
    for comp, value in result["components"].items():
        weight = result["weights"][comp]
        contribution = value * weight
        print(f"    {comp:20s}: {value:6.1f} x {weight:.2f} = {contribution:5.1f}")
    print()

    # Exit code based on gate
    if result["gate"] == "review_required":
        return 2
    elif result["gate"] == "review_recommended":
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
