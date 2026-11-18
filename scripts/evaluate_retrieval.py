#!/usr/bin/env python3
"""Small retrieval evaluation against seeded fictional sample documents.

Usage (API must be running, preferably in local demo mode with samples seeded):

    python scripts/evaluate_retrieval.py
    python scripts/evaluate_retrieval.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import httpx

CASES: list[dict[str, Any]] = [
    {
        "id": "pto_accrual",
        "question": "How many PTO days do employees accrue in their first two years?",
        "expected_filenames": ["pto_policy.md"],
        "department": None,
        "category": None,
    },
    {
        "id": "mfa_vpn",
        "question": "Is multi-factor authentication required for VPN access?",
        "expected_filenames": ["security_policy.md"],
        "department": "Security",
        "category": None,
    },
    {
        "id": "meal_allowance",
        "question": "What is the daily meal allowance for domestic travel?",
        "expected_filenames": ["travel_expense_policy.md"],
        "department": "Finance",
        "category": "Expenses",
    },
    {
        "id": "core_hours",
        "question": "What are core collaboration hours for remote employees?",
        "expected_filenames": ["remote_work_policy.md"],
        "department": None,
        "category": "Workplace",
    },
    {
        "id": "onboarding_security",
        "question": "What must new hires complete before production system access?",
        "expected_filenames": ["onboarding_checklist.txt", "security_policy.md"],
        "department": None,
        "category": None,
    },
    {
        "id": "insufficient",
        "question": "What is the cafeteria sushi menu for next Thursday?",
        "expected_filenames": [],
        "expect_abstain": True,
        "department": None,
        "category": None,
    },
]


def run(base_url: str) -> int:
    base = base_url.rstrip("/")
    passed = 0
    failed = 0

    with httpx.Client(timeout=60.0) as client:
        health = client.get(f"{base}/api/health")
        health.raise_for_status()
        print("Health:", health.json())

        for case in CASES:
            payload = {
                "question": case["question"],
                "department": case.get("department"),
                "category": case.get("category"),
            }
            res = client.post(f"{base}/api/query", json=payload)
            res.raise_for_status()
            data = res.json()
            sources = data.get("sources") or []
            filenames = {s.get("filename") for s in sources}
            expect_abstain = bool(case.get("expect_abstain"))
            expected = set(case.get("expected_filenames") or [])

            if expect_abstain:
                ok = bool(data.get("abstained")) and len(sources) == 0
                detail = "abstained with no sources" if ok else (
                    f"abstained={data.get('abstained')} sources={sorted(filenames)}"
                )
            else:
                # Pass when at least one expected source is retrieved (and we did not abstain).
                ok = bool(expected & filenames) and not data.get("abstained")
                detail = (
                    f"expected one of {sorted(expected)}; got {sorted(filenames)}; "
                    f"abstained={data.get('abstained')}"
                )

            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {case['id']}: {detail}")
            if not ok:
                print("  answer preview:", (data.get("answer") or "")[:180].replace("\n", " "))
                failed += 1
            else:
                passed += 1

    print(json.dumps({"passed": passed, "failed": failed, "total": passed + failed}))
    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality for sample docs")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Running API base URL",
    )
    args = parser.parse_args()
    sys.exit(run(args.base_url))


if __name__ == "__main__":
    main()
