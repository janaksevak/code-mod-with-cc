#!/usr/bin/env python3
"""
Semantic Diff Engine — Compares outputs with configurable exception rules.

Byte-for-byte comparison is the gold standard, but sometimes known differences
are acceptable (whitespace normalization, date format changes, decimal precision).
Semantic diff rules let users define these exceptions so the scorer can
distinguish real failures from expected differences.

Rules are defined in artifacts/semantic-diff-rules.json:
{
  "rules": [
    {
      "id": "trailing-spaces",
      "description": "Allow trailing space differences",
      "type": "regex_replace",
      "pattern": " +$",
      "replacement": "",
      "apply_to": "both"
    },
    {
      "id": "date-format",
      "description": "COBOL uses YYYYMMDD, Java uses YYYY-MM-DD",
      "type": "field_transform",
      "field_offset": 30,
      "field_length": 10,
      "transform": "strip_dashes"
    },
    {
      "id": "decimal-tolerance",
      "description": "Allow 0.01 tolerance on commission field",
      "type": "numeric_tolerance",
      "field_offset": 60,
      "field_length": 9,
      "tolerance": 0.01
    }
  ]
}

Usage:
  python3 semantic_diff.py --cobol output_cobol.dat --java output_java.dat --rules artifacts/semantic-diff-rules.json
  python3 semantic_diff.py --cobol-dir golden_dataset/ --java-dir java_outputs/ --rules artifacts/semantic-diff-rules.json
"""

import argparse
import json
import os
import re
from datetime import datetime


class SemanticDiffEngine:
    """Applies semantic diff rules to normalize outputs before comparison."""

    def __init__(self, rules_path: str = None):
        self.rules = []
        if rules_path and os.path.exists(rules_path):
            with open(rules_path) as f:
                data = json.load(f)
                self.rules = data.get("rules", [])

    def compare(self, cobol_bytes: bytes, java_bytes: bytes) -> dict:
        """Compare two outputs with semantic diff rules applied."""
        # First: raw byte comparison
        raw_identical = cobol_bytes == java_bytes

        if raw_identical:
            return {
                "identical": True,
                "raw_identical": True,
                "semantic_identical": True,
                "rules_applied": [],
                "remaining_differences": [],
            }

        # Apply rules to normalize both sides
        cobol_normalized = cobol_bytes
        java_normalized = java_bytes
        rules_applied = []

        for rule in self.rules:
            rule_type = rule.get("type")
            apply_to = rule.get("apply_to", "both")

            if rule_type == "regex_replace":
                result = self._apply_regex_replace(
                    cobol_normalized, java_normalized, rule, apply_to
                )
            elif rule_type == "field_transform":
                result = self._apply_field_transform(
                    cobol_normalized, java_normalized, rule, apply_to
                )
            elif rule_type == "numeric_tolerance":
                result = self._apply_numeric_tolerance(
                    cobol_normalized, java_normalized, rule
                )
            else:
                continue

            if result["applied"]:
                rules_applied.append(rule["id"])
                cobol_normalized = result["cobol"]
                java_normalized = result["java"]

        # Post-normalization comparison
        semantic_identical = cobol_normalized == java_normalized

        # Find remaining differences
        remaining = []
        if not semantic_identical:
            min_len = min(len(cobol_normalized), len(java_normalized))
            for i in range(min_len):
                if cobol_normalized[i] != java_normalized[i]:
                    remaining.append({
                        "position": i,
                        "cobol_byte": cobol_normalized[i],
                        "java_byte": java_normalized[i],
                        "cobol_char": chr(cobol_normalized[i]) if 32 <= cobol_normalized[i] < 127 else f"0x{cobol_normalized[i]:02x}",
                        "java_char": chr(java_normalized[i]) if 32 <= java_normalized[i] < 127 else f"0x{java_normalized[i]:02x}",
                    })
            if len(cobol_normalized) != len(java_normalized):
                remaining.append({
                    "position": min_len,
                    "type": "length_mismatch",
                    "cobol_length": len(cobol_normalized),
                    "java_length": len(java_normalized),
                })

        return {
            "identical": semantic_identical,
            "raw_identical": raw_identical,
            "semantic_identical": semantic_identical,
            "rules_applied": rules_applied,
            "remaining_differences": remaining[:50],  # Cap at 50
        }

    def _apply_regex_replace(self, cobol: bytes, java: bytes, rule: dict, apply_to: str) -> dict:
        pattern = rule["pattern"].encode()
        replacement = rule.get("replacement", "").encode()
        applied = False

        cobol_out = cobol
        java_out = java

        if apply_to in ("both", "cobol"):
            new = re.sub(pattern, replacement, cobol)
            if new != cobol:
                applied = True
                cobol_out = new

        if apply_to in ("both", "java"):
            new = re.sub(pattern, replacement, java)
            if new != java:
                applied = True
                java_out = new

        return {"cobol": cobol_out, "java": java_out, "applied": applied}

    def _apply_field_transform(self, cobol: bytes, java: bytes, rule: dict, apply_to: str) -> dict:
        offset = rule["field_offset"]
        length = rule["field_length"]
        transform = rule.get("transform", "identity")

        cobol_out = bytearray(cobol)
        java_out = bytearray(java)
        applied = False

        if transform == "strip_dashes":
            if apply_to in ("both", "java"):
                field = java_out[offset:offset + length]
                stripped = field.replace(b"-", b"")
                # Pad to original length
                stripped = stripped.ljust(length, b" ")
                java_out[offset:offset + length] = stripped[:length]
                applied = True

        return {"cobol": bytes(cobol_out), "java": bytes(java_out), "applied": applied}

    def _apply_numeric_tolerance(self, cobol: bytes, java: bytes, rule: dict) -> dict:
        offset = rule["field_offset"]
        length = rule["field_length"]
        tolerance = rule.get("tolerance", 0.0)

        cobol_out = bytearray(cobol)
        java_out = bytearray(java)
        applied = False

        try:
            cobol_val = float(cobol[offset:offset + length].strip())
            java_val = float(java[offset:offset + length].strip())

            if abs(cobol_val - java_val) <= tolerance:
                # Normalize java field to match cobol field
                java_out[offset:offset + length] = cobol[offset:offset + length]
                applied = True
        except (ValueError, IndexError):
            pass

        return {"cobol": bytes(cobol_out), "java": bytes(java_out), "applied": applied}

    def validate_rules(self) -> dict:
        """Check rules file for common issues."""
        issues = []
        for rule in self.rules:
            if "id" not in rule:
                issues.append({"rule": rule, "issue": "Missing 'id' field"})
            if "type" not in rule:
                issues.append({"rule": rule.get("id", "?"), "issue": "Missing 'type' field"})
            if rule.get("type") == "regex_replace" and "pattern" not in rule:
                issues.append({"rule": rule.get("id", "?"), "issue": "regex_replace requires 'pattern'"})
            if rule.get("type") == "numeric_tolerance" and "tolerance" not in rule:
                issues.append({"rule": rule.get("id", "?"), "issue": "numeric_tolerance requires 'tolerance'"})

        return {
            "total_rules": len(self.rules),
            "valid": len(issues) == 0,
            "issues": issues,
        }


def compare_files(cobol_path: str, java_path: str, rules_path: str = None) -> dict:
    """Compare two output files."""
    engine = SemanticDiffEngine(rules_path)

    with open(cobol_path, "rb") as f:
        cobol_bytes = f.read()
    with open(java_path, "rb") as f:
        java_bytes = f.read()

    return engine.compare(cobol_bytes, java_bytes)


def compare_directories(cobol_dir: str, java_dir: str, rules_path: str = None) -> dict:
    """Compare all matching files in two directories."""
    engine = SemanticDiffEngine(rules_path)
    results = {"tests": [], "total": 0, "passed": 0, "failed": 0}

    cobol_files = {f for f in os.listdir(cobol_dir) if f.endswith(".dat")}
    java_files = {f for f in os.listdir(java_dir) if f.endswith(".dat")}

    matched = cobol_files & java_files
    results["total"] = len(matched)

    for fname in sorted(matched):
        cobol_path = os.path.join(cobol_dir, fname)
        java_path = os.path.join(java_dir, fname)

        with open(cobol_path, "rb") as f:
            cobol_bytes = f.read()
        with open(java_path, "rb") as f:
            java_bytes = f.read()

        result = engine.compare(cobol_bytes, java_bytes)
        result["test_case"] = fname

        if result["identical"]:
            results["passed"] += 1
        else:
            results["failed"] += 1

        results["tests"].append(result)

    # Summary for confidence scorer
    results["passed_rules"] = results["passed"]
    results["total_rules"] = results["total"]

    return results


def main():
    parser = argparse.ArgumentParser(description="Semantic Diff Engine")
    parser.add_argument("--cobol", help="COBOL output file")
    parser.add_argument("--java", help="Java output file")
    parser.add_argument("--cobol-dir", help="COBOL outputs directory")
    parser.add_argument("--java-dir", help="Java outputs directory")
    parser.add_argument("--rules", help="Semantic diff rules JSON")
    parser.add_argument("--output", help="Write results to JSON")
    parser.add_argument("--validate-rules", action="store_true", help="Validate rules file only")
    args = parser.parse_args()

    if args.validate_rules:
        engine = SemanticDiffEngine(args.rules)
        validation = engine.validate_rules()
        print(json.dumps(validation, indent=2))
        return

    if args.cobol_dir and args.java_dir:
        results = compare_directories(args.cobol_dir, args.java_dir, args.rules)
    elif args.cobol and args.java:
        results = compare_files(args.cobol, args.java, args.rules)
    else:
        print("ERROR: Provide --cobol/--java or --cobol-dir/--java-dir")
        return

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)

    # Display summary
    if "tests" in results:
        print(f"\nSemantic Diff Results: {results['passed']}/{results['total']} passed")
        for t in results["tests"]:
            status = "PASS" if t["identical"] else "FAIL"
            rules = f" (rules: {', '.join(t['rules_applied'])})" if t["rules_applied"] else ""
            print(f"  [{status}] {t['test_case']}{rules}")
    else:
        status = "IDENTICAL" if results["identical"] else "DIFFERENT"
        print(f"Result: {status}")
        if results["rules_applied"]:
            print(f"Rules applied: {', '.join(results['rules_applied'])}")
        if results["remaining_differences"]:
            print(f"Remaining differences: {len(results['remaining_differences'])}")


if __name__ == "__main__":
    main()
