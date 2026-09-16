#!/usr/bin/env python3
"""Build a reproducible AiPaper planner or its font comparison sheets."""

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

from planner_config import PlannerConfig, TYPOGRAPHIES
from planner_i18n import LANGUAGES
from planner_pdf import generate_comparison, generate_pdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Configuration JSON exportée depuis l’interface")
    parser.add_argument("--font", choices=TYPOGRAPHIES)
    parser.add_argument("--language", choices=LANGUAGES, help="Langue du PDF (fr par défaut)")
    parser.add_argument("--days", type=int)
    parser.add_argument("--all-variants", action="store_true")
    parser.add_argument("--comparison", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "output/pdf")
    args = parser.parse_args()
    config = PlannerConfig.from_dict(json.loads(args.config.read_text())) if args.config else PlannerConfig()
    if args.days is not None:
        config = replace(config, days=args.days)
    if args.font is not None:
        config = replace(config, typography=args.font)
    if args.language is not None:
        config = replace(config, language=args.language)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for font in TYPOGRAPHIES if args.all_variants else [config.typography]:
        current = replace(config, typography=font)
        target = args.output_dir / current.pdf_filename
        start = time.perf_counter()
        count = generate_pdf(current, target)
        result = {"file": str(target), "pages": count, "bytes": target.stat().st_size,
                  "seconds": round(time.perf_counter() - start, 3)}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.comparison:
        target = args.output_dir / ("aipaper-comparatif-polices.pdf" if config.language == "fr"
                                    else "aipaper-font-comparison-en.pdf")
        generate_comparison(config, target)
        results.append({"file": str(target), "pages": 10, "bytes": target.stat().st_size})
        print(json.dumps(results[-1], ensure_ascii=False))
    report = "generation-report.json" if config.language == "fr" else "generation-report-en.json"
    (args.output_dir / report).write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')


if __name__ == "__main__":
    main()
