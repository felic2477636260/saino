from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.core import SainoAgent
from agent.legacy import LegacySainoAgent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company-code", default="macro")
    parser.add_argument("--query", default="请生成企业体检报告")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--mode", choices=["legacy", "optimized"], default="legacy")
    args = parser.parse_args()

    agent = LegacySainoAgent() if args.mode == "legacy" else SainoAgent()
    result = agent.analyze(company_code=args.company_code, query=args.query, top_k=args.top_k)
    output_dir = Path("baselines/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.company_code}_{args.mode}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{args.mode} output saved to {output_path}")


if __name__ == "__main__":
    main()
