#!/usr/bin/env python3
"""Generate a separate AiPaper dated planner with calendars, weekly tasks and backlog."""

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

from dated_planner_config import DatedPlannerConfig
from dated_planner_pdf import generate_dated_pdf
from planner_config import TYPOGRAPHIES
from planner_i18n import LANGUAGES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, help='Configuration JSON du carnet daté')
    parser.add_argument('--start-date', help='Première journée, au format YYYY-MM-DD')
    parser.add_argument('--months', type=int, choices=[1, 2, 3], help='Durée en mois calendaires')
    parser.add_argument('--week-pages', type=int, choices=[1, 2, 3], help='Listes de tâches par semaine')
    parser.add_argument('--weekly-tasks', type=int, help='Actions par liste hebdomadaire, de 1 à 40')
    parser.add_argument('--language', choices=LANGUAGES, help='Langue du PDF (fr par défaut)')
    parser.add_argument('--font', choices=TYPOGRAPHIES)
    parser.add_argument('--output-dir', type=Path,
                        default=Path(__file__).resolve().parent / 'output/pdf/dated')
    args = parser.parse_args()
    try:
        config = DatedPlannerConfig.from_dict(json.loads(args.config.read_text())) if args.config else DatedPlannerConfig()
        overrides = {name: getattr(args, name) for name in ('start_date', 'months', 'week_pages', 'weekly_tasks')
                     if getattr(args, name) is not None}
        base_overrides = {}
        if args.language is not None:
            base_overrides['language'] = args.language
        if args.font is not None:
            base_overrides['typography'] = args.font
        config = replace(config, base=replace(config.base, **base_overrides), **overrides)
    except (ValueError, TypeError, OSError) as error:
        parser.error(str(error))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / config.pdf_filename
    start = time.perf_counter()
    count = generate_dated_pdf(config, target)
    result = {'file': str(target), 'pages': count, 'bytes': target.stat().st_size,
              'seconds': round(time.perf_counter() - start, 3), 'config': config.to_dict()}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    report = target.with_suffix('.report.json')
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
