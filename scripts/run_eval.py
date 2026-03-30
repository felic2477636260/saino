from __future__ import annotations

import argparse
import json
from pathlib import Path

from skills.evaluation import compare_reports, load_report, optional_llm_judge


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, help="Path to legacy/system baseline JSON.")
    parser.add_argument("--candidate", required=True, help="Path to optimized output JSON.")
    parser.add_argument("--external", help="Optional path to direct platform baseline JSON/MD.")
    parser.add_argument("--output", default="experiments/results/latest_eval.json")
    parser.add_argument("--with-llm-judge", action="store_true", help="Enable optional LLM judge comparison.")
    args = parser.parse_args()

    baseline = load_report(Path(args.baseline))
    candidate = load_report(Path(args.candidate))

    results = {
        "baseline_vs_candidate": compare_reports(candidate=candidate, baseline=baseline),
    }
    if args.with_llm_judge:
        results["llm_judge"] = optional_llm_judge(candidate=candidate, baseline=baseline)
    else:
        results["llm_judge"] = {"status": "skipped", "reason": "未启用 --with-llm-judge。"}
    if args.external:
        external = load_report(Path(args.external))
        results["external_vs_candidate"] = compare_reports(candidate=candidate, baseline=external)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"evaluation summary saved to {output_path}")


if __name__ == "__main__":
    main()
