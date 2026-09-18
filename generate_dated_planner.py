#!/usr/bin/env python3
"""Generate a separate AiPaper dated planner with calendars, weekly tasks and backlog."""

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

from dated_planner_config import MONTH_RANGE, DatedPlannerConfig
import pdf_compact
from dated_planner_pdf import generate_dated_pdf
from planner_config import MEETING_LAYOUTS, TYPOGRAPHIES
from planner_formats import CUSTOM, DENSITIES, DEVICES
from planner_layout import TOOLBAR_SIDES
from planner_note_styles import NOTE_STYLES
from planner_i18n import LANGUAGES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, help='Configuration JSON du carnet daté')
    parser.add_argument('--start-date', help='Première journée, au format YYYY-MM-DD')
    parser.add_argument('--months', type=int, choices=range(MONTH_RANGE[0], MONTH_RANGE[1] + 1),
                        metavar='{1..12}', help='Durée en mois calendaires, de 1 à 12')
    parser.add_argument('--week-pages', type=int, choices=[1, 2, 3], help='Listes de tâches par semaine')
    parser.add_argument('--weekly-tasks', type=int, help='Actions par liste hebdomadaire, de 1 à 40')
    parser.add_argument('--include-weekends', action=argparse.BooleanOptionalAction, default=None,
                        help='Inclure les Meeting/Notes du week-end (par défaut oui ; --no-include-weekends pour les exclure)')
    parser.add_argument('--device', choices=list(DEVICES) + [CUSTOM],
                        help='Modèle de tablette ; custom demande les deux dimensions en mm')
    parser.add_argument('--density', choices=DENSITIES, help='Confort d’écriture : standard ou comfortable')
    parser.add_argument('--toolbar', choices=TOOLBAR_SIDES,
                        help='Côté de la barre d’outils intégrée de la tablette ; la bande correspondante reste libre')
    parser.add_argument('--toolbar-mm', type=float,
                        help='Largeur de la barre d’outils intégrée, en mm (4 à 30)')
    parser.add_argument('--custom-width-mm', type=float, help='Largeur du format personnalisé, en mm')
    parser.add_argument('--custom-height-mm', type=float, help='Hauteur du format personnalisé, en mm')
    parser.add_argument('--end-date', dest='end_date_override',
                        help='Dernier jour inclus, AAAA-MM-JJ ; remplace la durée en mois')
    parser.add_argument('--project-count', type=int, help='Nombre de fiches projet, de 0 à 12')
    parser.add_argument('--project-notes-pages', type=int, help='Pages Notes par fiche projet')
    parser.add_argument('--meeting-layout', choices=MEETING_LAYOUTS,
                        help='Composition des pages Meeting')
    parser.add_argument('--weekly-overview', action=argparse.BooleanOptionalAction, default=None,
                        help='Ajouter une vue « sept jours » avant les tâches de la semaine')
    parser.add_argument('--weekly-review', action=argparse.BooleanOptionalAction, default=None,
                        help='Ajouter un bilan après les tâches de la semaine')
    parser.add_argument('--meeting-note-style', choices=NOTE_STYLES, help='Fond des pages Notes')
    parser.add_argument('--task-note-style', choices=NOTE_STYLES, help='Fond des pages de contexte')
    parser.add_argument('--monthly-priorities', action=argparse.BooleanOptionalAction, default=None,
                        help='Ajouter une page Priorités après chaque calendrier')
    parser.add_argument('--language', choices=LANGUAGES, help='Langue du PDF (fr par défaut)')
    parser.add_argument('--font', choices=TYPOGRAPHIES)
    parser.add_argument('--compact', action='store_true',
                        help='Repaquetter le PDF : deux à trois fois plus léger à '
                             'lire pour la tablette, rendu identique (qpdf requis)')
    parser.add_argument('--output-dir', type=Path,
                        default=Path(__file__).resolve().parent / 'output/pdf/dated')
    args = parser.parse_args()
    try:
        config = DatedPlannerConfig.from_dict(json.loads(args.config.read_text())) if args.config else DatedPlannerConfig()
        overrides = {name: getattr(args, name) for name in ('start_date', 'months', 'week_pages', 'weekly_tasks', 'include_weekends', 'monthly_priorities',
                                                           'weekly_overview', 'weekly_review',
                                                           'end_date_override')
                     if getattr(args, name) is not None}
        base_overrides = {}
        if args.language is not None:
            base_overrides['language'] = args.language
        if args.font is not None:
            base_overrides['typography'] = args.font
        base_overrides.update({name: getattr(args, name) for name in
                               ('device', 'density', 'toolbar', 'toolbar_mm',
                                'custom_width_mm', 'custom_height_mm',
                                'meeting_note_style', 'task_note_style', 'meeting_layout',
                                'project_count', 'project_notes_pages')
                               if getattr(args, name) is not None})
        config = replace(config, base=replace(config.base, **base_overrides), **overrides)
    except (ValueError, TypeError, OSError) as error:
        parser.error(str(error))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / config.pdf_filename
    start = time.perf_counter()
    count = generate_dated_pdf(config, target)
    if args.compact:
        target.write_bytes(pdf_compact.compact(target.read_bytes()))
    result = {'file': str(target), 'pages': count, 'bytes': target.stat().st_size,
              'seconds': round(time.perf_counter() - start, 3), 'config': config.to_dict()}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    report = target.with_suffix('.report.json')
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
