#!/usr/bin/env python3
"""NiceGUI workspace for local, desktop and self-hosted PDF generation."""

import argparse
import asyncio
import base64
import json
import logging
import math
import os
import secrets
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

from nicegui import app, ui

from dated_planner_config import DatedPlannerConfig, month_choices, month_label
import nicegui_preferences as preferences
from nicegui_jobs import cpu_job, shutdown_jobs
from nicegui_service import generate_artifact, parse_config, render_preview
from planner_manifest import build_manifest, preview_kinds
from planner_config import MEETING_LAYOUTS, PlannerConfig, TYPOGRAPHIES
from planner_formats import BRANDS, CUSTOM, DENSITIES, DEVICES, devices_of
from planner_layout import DEFAULT_TOOLBAR_MM, TOOLBAR_MM, TOOLBAR_SIDES
from planner_note_styles import NOTE_STYLES
from planner_i18n import LANGUAGES

ROOT = Path(__file__).resolve().parent
MODES = {'dated': 'Carnet daté', 'undated': 'Carnet libre'}
KIND_LABELS = {'home': 'Accueil', 'calendar': 'Calendrier', 'month-plan': 'Priorités',
               'week-overview': 'Sept jours', 'weekly': 'Semaine', 'week-review': 'Bilan',
               'meeting': 'Meeting', 'meeting-actions': 'Décisions',
               'task-list': 'Backlog', 'task-notes': 'Contexte',
               'projects-index': 'Projets', 'project': 'Fiche projet',
               'project-notes': 'Notes projet'}
UNDATED_LABELS = {'task-list': 'Liste TODO'}
CSS = '''
@font-face { font-family: Manrope; src: url('/planner-fonts/Manrope-Regular.ttf'); font-weight: 400; }
@font-face { font-family: Manrope; src: url('/planner-fonts/Manrope-Bold.ttf'); font-weight: 700; }
body { font-family: Manrope, sans-serif; color: #222c2a; background: #fafaf8; }
.nicegui-content { padding: 0; gap: 0; }
.shell { max-width: 1540px; margin: auto; padding: 30px 44px 50px; width: 100%; }
.masthead { width: 100%; align-items: center; justify-content: space-between; padding-bottom: 24px; border-bottom: 1px solid #dedfd9; }
.brand { font-size: 18px; font-weight: 700; letter-spacing: -.7px; }
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #667570; }
.intro { margin: 32px 0 26px; align-items: end; justify-content: space-between; width: 100%; }
.intro h1 { font-size: clamp(28px, 3vw, 40px); line-height: 1.2; letter-spacing: -1.6px; margin: 8px 0 12px; font-weight: 700; }
.muted { color: #68746e; font-size: 13px; line-height: 1.7; }
.workspace { display: grid; grid-template-columns: 355px minmax(0, 1fr); gap: 40px; width: 100%; align-items: start; }
.settings { width: 100%; gap: 20px; }
.section-title { font-size: 15px; font-weight: 700; margin-bottom: 14px; }
.settings .q-field { width: 100%; }
.settings .q-expansion-item { width: 100%; border-top: 1px solid #e0e3dc; }
.settings .q-item { padding-left: 0; }
.settings .q-expansion-item__content { padding: 8px 0 16px; }
.fields { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; width: 100%; }
.q-field--outlined .q-field__control { border-radius: 8px; background: #fff; }
.q-btn { border-radius: 8px; text-transform: none; font-weight: 700; letter-spacing: 0; }
.mode-switch .q-btn { font-size: 12px; padding: 9px 16px; }
.split-note { border-left: 2px solid #b8c4bd; padding-left: 10px; }
.slots { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; width: 100%; align-items: start; }
.slot { background: #fff; border: 1px solid #e0e3dc; border-radius: 12px; padding: 20px; gap: 12px; width: 100%; }
.slot .q-uploader { width: 100%; max-width: none; box-shadow: none; border: 1px dashed #c6cec8; border-radius: 8px; }
.pick { width: 100%; border: 1px solid #e0e3dc; border-radius: 12px; background: #fff; overflow: hidden; }
.pick .q-expansion-item { border-top: 1px solid #edefe9; }
.pick .q-expansion-item:first-child { border-top: none; }
.pick-head { width: 100%; align-items: center; justify-content: space-between; gap: 12px; }
.pick-count { font-size: 12px; color: #68746e; white-space: nowrap; }
.shots { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 16px; width: 100%; padding: 4px 0 10px; }
.shot { border: 1px solid #e4e7e0; border-radius: 10px; overflow: hidden; background: #fbfcfa; transition: border-color .15s, box-shadow .15s; }
.shot { cursor: pointer; }
.shot.on { border-color: #235c4f; box-shadow: 0 0 0 1px #235c4f; }
.shot.held { cursor: default; opacity: .55; }
.shot.held img { filter: grayscale(1); }
.shot img { width: 100%; display: block; background: #fff; }
.shot-foot { padding: 8px 10px; font-size: 11px; line-height: 1.5; color: #43514c; }
.shot-foot b { display: block; font-weight: 700; color: #222c2a; }
.journal { background: #212624; color: #dfe6e0; border-radius: 12px; padding: 18px 20px; width: 100%;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; line-height: 1.75;
  white-space: pre-wrap; min-height: 150px; max-height: 420px; overflow: auto; }
@media(max-width: 720px) { .slots { grid-template-columns: 1fr; } }
.chip { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: #43514c;
  background: #eceee8; border: 1px solid #dee2d8; border-radius: 999px; padding: 6px 13px; white-space: nowrap; }
.chip b { font-weight: 700; color: #222c2a; }
.metrics { display: grid; grid-template-columns: repeat(3, 1fr); border-block: 1px solid #dedfd9; padding: 18px 0; width: 100%; }
.metric-value { font-size: 23px; font-weight: 700; letter-spacing: -.8px; }
.preview-panel { background: #eceee8; border: 1px solid #e0e3dc; border-radius: 12px; padding: 22px; min-height: 680px; width: 100%; gap: 16px; }
.preview-toolbar { width: 100%; justify-content: space-between; align-items: center; gap: 12px; }
.preview-tabs { width: 100%; background: transparent; }
.preview-tabs .q-btn { font-size: 12px; padding: 8px 12px; }
.preview-actions { width: 100%; align-items: center; gap: 16px; flex-wrap: wrap; }
.preview-actions .q-btn { font-size: 12px; }
.paper-wrap { width: 100%; display: flex; align-items: center; justify-content: center; min-height: 480px; }
.paper { width: min(100%, 590px); background: white; box-shadow: 0 6px 24px #25352e14; }
.status { border-left: 3px solid #1c584c; padding: 10px 14px; background: #eff4ee; font-size: 13px; width: 100%; }
.error { color: #a3372c; background: #fff0ed; border-color: #a3372c; }
.profile-row { width: 100%; align-items: center; gap: 4px; flex-wrap: nowrap;
  border-bottom: 1px solid #e6e8e1; padding-bottom: 5px; }
.profile-name { flex: 1; min-width: 0; font-weight: 700; font-size: 13px; color: #1c584c;
  justify-content: flex-start; padding: 2px 4px; }
.profile-save { white-space: nowrap; flex: 0 0 auto; padding: 0 14px; height: 40px; }
.profile-save .q-btn__content { flex-wrap: nowrap; gap: 6px; }
.profile-mode { font-size: 10px; text-transform: uppercase; letter-spacing: 1.2px; color: #7a857f; }
.q-uploader { width: 100%; box-shadow: none; border: 1px dashed #bac6bb; }
.footer-note { border-top: 1px solid #dedfd9; margin-top: 30px; padding-top: 18px; width: 100%; }
@media(max-width: 950px) { .shell { padding: 22px; } .workspace { grid-template-columns: 310px minmax(0,1fr); gap: 22px; } .preview-panel { padding: 14px; } }
@media(max-width: 720px) { .workspace { grid-template-columns: 1fr; } .masthead { gap: 18px; } .intro { margin-top: 20px; } .preview-panel { min-height: 400px; } .shell { padding: 20px 16px; } }
'''


class PlannerWorkspace:
    """Each page connection owns its drafts and generated documents."""

    def __init__(self, initial_mode='dated'):
        self.mode = initial_mode
        self.configs = {'dated': DatedPlannerConfig(), 'undated': PlannerConfig()}
        self.family = None
        self.exact_dates = None
        self.preferences = preferences.empty()
        self.storage_off = False
        self.profile_name = None
        self.fields = {}
        self.busy = False
        self.dirty = False
        self.short = False
        self.sample = None
        self.output = None
        self.images = {}
        self.kind = 0
        self.kind_control = None
        self.error = ''
        self.activity = ''
        self.revision = 0

    @property
    def config(self):
        return self.configs[self.mode]

    # --- browser preferences ------------------------------------------------
    def read_storage(self):
        try:
            return app.storage.user.get(preferences.STORAGE_KEY)
        except Exception:  # No request context: desktop window, tests, previews.
            self.storage_off = True
            logging.debug('Preferences storage unavailable', exc_info=True)
            return None

    def write_storage(self):
        if self.storage_off:
            return
        try:
            app.storage.user[preferences.STORAGE_KEY] = self.preferences
        except Exception:
            self.storage_off = True
            logging.debug('Preferences storage unavailable', exc_info=True)

    def restore(self):
        """Start from the last valid settings of this browser, never from a draft."""
        self.preferences, message = preferences.load(self.read_storage())
        restored = False
        for mode in ('dated', 'undated'):
            stored = self.preferences['last_valid'][mode]
            if stored is not None:
                self.configs[mode] = parse_config(mode, stored)
                restored = True
        if restored:  # A first visit keeps the mode the workspace opened with.
            self.mode = self.preferences['active_mode']
        self.error = message

    def persist(self):
        try:
            self.preferences = preferences.remember(self.preferences, self.mode,
                                                    self.config.to_dict())
        except ValueError:
            return
        self.write_storage()

    def mark_dirty(self, _=None):
        self.revision += 1
        self.dirty = True
        self.output = None
        self.download_area.refresh()

    def field(self, key, control):
        self.fields[key] = control
        control.on_value_change(self.mark_dirty)
        control.bind_enabled_from(self, 'busy', backward=lambda value: not value)
        return control.props('outlined dense').classes('w-full')

    def number(self, key, label, value, minimum, maximum, **props):
        return self.field(key, ui.number(label, value=value, min=minimum, max=maximum,
                                         step=1, precision=0, **props))

    def base_config(self):
        return self.config.base if self.mode == 'dated' else self.config

    def preview_tabs(self):
        """One tab per section the applied configuration actually produces."""
        kinds = preview_kinds(build_manifest(self.config), self.mode)
        labels = dict(KIND_LABELS, **(UNDATED_LABELS if self.mode == 'undated' else {}))
        return [labels.get(kind, kind) for kind in kinds]

    def whole(self, value, message='Complétez les champs numériques avec des nombres entiers.'):
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value != int(value):
            raise ValueError(message)
        return int(value)

    def read_config(self):
        base = self.config.base if self.mode == 'dated' else self.config
        payload = base.to_dict()
        for key in ('list_count', 'tasks_per_list', 'detail_pages', 'notes_pages', 'days',
                    'project_count', 'project_notes_pages'):
            if key in self.fields:
                payload[key] = self.whole(self.fields[key].value)
        for key in ('language', 'typography', 'title', 'meeting_layout',
                    'meeting_note_style', 'task_note_style'):
            payload[key] = self.fields[key].value
        payload['density'] = self.fields['density'].value
        payload['toolbar'] = self.fields['toolbar'].value
        band = self.fields['toolbar_mm'].value  # Hidden and cleared: keep the default.
        payload['toolbar_mm'] = float(band) if isinstance(band, (int, float)) \
            and not isinstance(band, bool) else DEFAULT_TOOLBAR_MM
        device = self.fields['device'].value if 'device' in self.fields else CUSTOM
        payload['device'] = device
        payload['custom_width_mm'] = payload['custom_height_mm'] = None
        if device == CUSTOM:
            for key, side in (('custom_width_mm', 'largeur'), ('custom_height_mm', 'hauteur')):
                payload[key] = float(self.whole(
                    self.fields[key].value if key in self.fields else None,
                    f'Indiquez la {side} du format personnalisé, en millimètres entiers.'))
        payload['list_names'] = self.fields['list_names'].value.splitlines()
        payload['project_names'] = self.fields['project_names'].value.splitlines()[
            :int(payload.get('project_count') or 0)]
        if self.mode == 'dated':
            dated = self.config.to_dict()
            dated['base'] = payload
            dated['start_date'] = self.fields['start_date'].value
            dated['include_weekends'] = self.fields['include_weekends'].value
            for key in ('monthly_priorities', 'weekly_overview', 'weekly_review'):
                dated[key] = self.fields[key].value
            for key in ('week_pages', 'weekly_tasks'):
                dated[key] = self.whole(self.fields[key].value)
            field = self.fields.get('end_date_override')
            chosen_end = field.value if field is not None else None
            dated['end_date_override'] = chosen_end or None
            if not chosen_end:
                dated['months'] = self.whole(self.fields['months'].value)
            return parse_config(self.mode, dated)
        return parse_config(self.mode, payload)

    def apply_draft(self):
        new_config = self.read_config()
        if new_config != self.config:
            self.configs[self.mode] = new_config
            self.sample = None
            self.images.clear()
            self.output = None
            self.kind = min(self.kind, len(self.preview_tabs()) - 1)
            self.preview_tabs_area.refresh()
            self.preview_area.refresh()
        self.dirty = False
        self.error = ''
        self.persist()
        self.metrics.refresh()
        self.format_chip.refresh()

    async def switch_mode(self, event):
        if self.busy:
            self.mode_control.set_value(self.mode)
            return
        if event.value == self.mode:
            return
        self.mode = event.value
        self.sample = self.output = None
        self.images.clear()
        self.kind = 0
        self.error = ''
        self.dirty = False
        self.busy = True
        try:
            await self.body.refresh()
        finally:
            self.busy = False
        await self.refresh_preview()

    async def import_config(self, event):
        if self.busy:
            return
        self.busy = True
        try:
            payload = json.loads(await event.file.read())
            mode = 'dated' if isinstance(payload, dict) and 'base' in payload else 'undated'
            config = parse_config(mode, payload)
            self.mode = mode
            self.configs[mode] = config
            self.mode_control.set_value(mode)
            self.sample = self.output = None
            self.images.clear()
            self.kind = 0
            self.dirty = False
            self.error = ''
            await self.body.refresh()
        except (ValueError, TypeError, UnicodeError) as error:
            self.error = f'Configuration invalide : {error}'
            self.download_area.refresh()
            return
        finally:
            self.busy = False
            self.download_area.refresh()
        with self.client:
            ui.notify('Réglages importés.', type='positive')
            await self.refresh_preview()

    def export_config(self):
        try:
            config = self.read_config()
        except (ValueError, TypeError) as error:
            self.error = str(error)
            self.download_area.refresh()
            return
        base = config.base if self.mode == 'dated' else config
        name = (f'aipaper-dated-config-{base.language}.json' if self.mode == 'dated' else
                'aipaper-config.json' if base.language == 'fr' else 'aipaper-config-en.json')
        ui.download(json.dumps(config.to_dict(), ensure_ascii=False, indent=2).encode(), name, 'application/json')

    async def preview_image(self):
        if self.sample is None:
            self.preview_area.refresh()
            return
        if self.kind not in self.images:
            try:
                png = await cpu_job(render_preview, self.sample.pdf_bytes, self.kind + 1)
                self.images[self.kind] = 'data:image/png;base64,' + base64.b64encode(png).decode()
            except Exception:
                logging.exception('Preview image rendering failed')
                self.error = 'Aperçu image indisponible. Installez Poppler ; le PDF d’aperçu reste téléchargeable.'
        self.preview_area.refresh()

    async def change_kind(self, event):
        if self.busy:
            # The enabled binding travels asynchronously: put the tab back so
            # the panel never shows one page under another page's name.
            if self.kind_control is not None:
                self.kind_control.set_value(self.kind)
            return
        self.kind = event.value
        self.busy = True
        try:
            await self.preview_image()
        finally:
            self.busy = False
            self.download_area.refresh()

    async def refresh_preview(self):
        if self.busy:
            return
        self.busy = True
        self.activity = 'Préparation de l’aperçu…'
        self.download_area.refresh()
        try:
            self.apply_draft()
            if self.sample is None:
                self.sample = await cpu_job(generate_artifact, self.mode, self.config.to_dict(), samples=True)
            await self.preview_image()
        except (ValueError, TypeError) as error:
            self.error = str(error)
        except Exception:
            logging.exception('Preview generation failed')
            self.error = 'L’aperçu n’a pas pu être créé. Vos réglages sont conservés ; vous pouvez réessayer.'
        finally:
            self.busy = False
            self.activity = ''
            self.download_area.refresh()

    async def generate(self):
        if self.busy:
            return
        self.busy = True
        self.activity = 'Création du carnet et de ses liens…'
        self.download_area.refresh()
        try:
            self.apply_draft()
            revision = self.revision
            artifact = await cpu_job(generate_artifact, self.mode, self.config.to_dict(),
                                     short=self.short if self.mode == 'undated' else False)
            if revision == self.revision:
                self.output = artifact
                ui.notify('Votre carnet est prêt.', type='positive')
        except (ValueError, TypeError) as error:
            self.error = str(error)
        except Exception:
            logging.exception('PDF generation failed')
            self.error = 'Le PDF n’a pas pu être créé. Vos réglages sont conservés ; vous pouvez réessayer.'
        finally:
            self.busy = False
            self.activity = ''
            self.download_area.refresh()

    def control(self, element):
        return element.props('outlined dense').classes('w-full') \
            .bind_enabled_from(self, 'busy', backward=lambda value: not value)

    def change_period(self, event):
        if self.busy:
            return
        self.exact_dates = bool(event.value)
        self.period_fields.refresh()
        self.mark_dirty()

    @ui.refreshable
    def period_fields(self):
        config = self.config
        for key in ('start_date', 'months', 'end_date_override'):
            self.fields.pop(key, None)
        exact = (config.end_date_override is not None if self.exact_dates is None
                 else self.exact_dates)
        with ui.element('div').classes('fields'):
            self.field('start_date', ui.input('À partir du', value=config.start_date)).props('type=date')
            if exact:
                self.field('end_date_override', ui.input(
                    'Jusqu’au (inclus)',
                    value=config.end_date_override or config.end_date.isoformat())).props('type=date')
            else:
                self.field('months', ui.select(
                    {value: month_label(value) for value in month_choices(config.months)},
                    value=config.months, label='Durée'))
        self.control(ui.checkbox('Choisir une date de fin exacte', value=exact,
                                 on_change=self.change_period)).props('dense')
        if exact:
            ui.label('La date de fin est incluse et remplace la durée. 366 jours au maximum.').classes('muted')

    def change_family(self, event):
        if self.busy:
            return
        self.family = event.value
        self.device_fields.refresh()
        self.mark_dirty()

    @ui.refreshable
    def device_fields(self):
        base = self.base_config()
        for key in ('device', 'density', 'custom_width_mm', 'custom_height_mm',
                    'toolbar', 'toolbar_mm'):
            self.fields.pop(key, None)
        family = self.family or (CUSTOM if base.device == CUSTOM else DEVICES[base.device].brand)
        with ui.element('div').classes('fields'):
            self.control(ui.select(BRANDS, value=family, label='Famille',
                                   on_change=self.change_family))
            if family != CUSTOM:
                models = {device.key: device.label for device in devices_of(family)}
                chosen = base.device if base.device in models else next(iter(models))
                self.field('device', ui.select(models, value=chosen, label='Modèle'))
            else:
                self.field('density', ui.select(DENSITIES, value=base.density,
                                                label='Confort d’écriture'))
        if family == CUSTOM:
            with ui.element('div').classes('fields'):
                self.number('custom_width_mm', 'Largeur', base.custom_width_mm or 163,
                            100, 400, suffix='mm')
                self.number('custom_height_mm', 'Hauteur', base.custom_height_mm or 217,
                            150, 400, suffix='mm')
            ui.label('Portrait uniquement pour cette livraison : la largeur reste '
                     'inférieure ou égale à la hauteur.').classes('muted')
        else:
            self.field('density', ui.select(DENSITIES, value=base.density,
                                            label='Confort d’écriture'))
        ui.label('Aéré écrit plus au large : une liste qui ne tient plus se poursuit '
                 'sur un feuillet suivant, sans perdre une seule tâche.').classes('muted')
        with ui.element('div').classes('fields'):
            side = self.field('toolbar', ui.select(TOOLBAR_SIDES, value=base.toolbar,
                                                   label='Barre d’outils de la tablette'))
            width = self.field('toolbar_mm',
                               ui.number('Largeur de la barre', value=float(base.toolbar_mm),
                                         min=TOOLBAR_MM[0], max=TOOLBAR_MM[1],
                                         step=0.5, precision=1, suffix='mm'))
            width.bind_visibility_from(side, 'value', backward=lambda value: value != 'none')
        ui.label('La barre intégrée flotte au-dessus de la page : à droite elle masque la '
                 'navigation, à gauche le début des lignes. Folio laisse sa bande libre et '
                 'pose tout le reste juste à côté.').classes('muted')

    # --- named profiles -----------------------------------------------------
    async def ask(self, title, message, choices):
        with ui.dialog() as dialog, ui.card().classes('gap-3').style('min-width:320px'):
            ui.label(title).classes('text-base font-bold')
            ui.label(message).classes('muted')
            with ui.row().classes('justify-end w-full gap-2'):
                for label, value, primary in choices:
                    button = ui.button(label, on_click=lambda v=value: dialog.submit(v))
                    if not primary:
                        button.props('flat')
        try:
            return await dialog
        finally:
            dialog.delete()

    async def save_profile(self):
        if self.busy:
            return
        try:
            name = preferences.clean_name(self.profile_name.value if self.profile_name else '')
            config = self.read_config()
        except (ValueError, TypeError) as error:
            self.error = str(error)
            self.download_area.refresh()
            return
        existing = next((profile for profile in self.preferences['profiles']
                         if profile['name'].casefold() == name.casefold()), None)
        identifier = None
        if existing is not None:
            answer = await self.ask(
                f'Remplacer « {existing["name"]} » ?',
                'Ce profil porte déjà ce nom. Vous pouvez le remplacer ou en créer un second.',
                (('Annuler', None, False), ('Créer un second', 'new', False),
                 ('Remplacer', 'replace', True)))
            if answer is None:
                return
            identifier = existing['id'] if answer == 'replace' else None
        try:
            self.preferences, _ = preferences.save_profile(
                self.preferences, name, self.mode, config.to_dict(), identifier)
        except ValueError as error:
            self.error = str(error)
            self.download_area.refresh()
            return
        self.write_storage()
        self.profile_name.set_value('')
        self.error = ''
        self.profiles_area.refresh()
        self.download_area.refresh()
        ui.notify(f'Profil « {name} » enregistré.', type='positive')

    async def rename_profile(self, identifier):
        profile = preferences.find(self.preferences, identifier)
        if self.busy or profile is None:
            return
        with ui.dialog() as dialog, ui.card().classes('gap-3').style('min-width:320px'):
            ui.label('Renommer ce profil').classes('text-base font-bold')
            field = ui.input('Nom', value=profile['name']).props('outlined dense autofocus') \
                .props(f'maxlength={preferences.NAME_LIMIT}').classes('w-full')
            with ui.row().classes('justify-end w-full gap-2'):
                ui.button('Annuler', on_click=lambda: dialog.submit(None)).props('flat')
                ui.button('Renommer', on_click=lambda: dialog.submit(field.value))
        try:
            name = await dialog
        finally:
            dialog.delete()
        if name is None:
            return
        try:
            self.preferences = preferences.rename_profile(self.preferences, identifier, name)
        except ValueError as error:
            self.error = str(error)
            self.download_area.refresh()
            return
        self.write_storage()
        self.profiles_area.refresh()

    async def delete_profile(self, identifier):
        profile = preferences.find(self.preferences, identifier)
        if self.busy or profile is None:
            return
        confirmed = await self.ask(
            f'Supprimer « {profile["name"]} » ?',
            'Ce profil sera retiré de ce navigateur. Vos carnets déjà téléchargés ne bougent pas.',
            (('Annuler', False, False), ('Supprimer', True, True)))
        if not confirmed:
            return
        self.preferences = preferences.delete_profile(self.preferences, identifier)
        self.write_storage()
        self.profiles_area.refresh()

    async def load_profile(self, identifier):
        profile = preferences.find(self.preferences, identifier)
        if self.busy or profile is None:
            return
        self.busy = True
        try:
            config = parse_config(profile['mode'], profile['config'])
            self.mode = profile['mode']
            self.configs[self.mode] = config
            self.mode_control.set_value(self.mode)
            self.sample = self.output = None
            self.images.clear()
            self.kind = 0
            self.dirty = False
            self.error = ''
            await self.body.refresh()
        except (ValueError, TypeError) as error:
            self.error = f'Profil illisible : {error}'
            self.download_area.refresh()
            return
        finally:
            self.busy = False
            self.download_area.refresh()
        with self.client:
            ui.notify(f'Profil « {profile["name"]} » chargé.', type='positive')
            await self.refresh_preview()

    @ui.refreshable
    def profiles_area(self):
        for profile in self.preferences['profiles']:
            with ui.row().classes('profile-row'):
                ui.button(profile['name'],
                          on_click=lambda identifier=profile['id']: self.load_profile(identifier)) \
                    .props('flat dense no-caps').classes('profile-name') \
                    .bind_enabled_from(self, 'busy', backward=lambda value: not value)
                ui.label(MODES[profile['mode']]).classes('profile-mode')
                for icon, handler in (('edit', self.rename_profile), ('delete_outline', self.delete_profile)):
                    ui.button(icon=icon,
                              on_click=lambda identifier=profile['id'], call=handler: call(identifier)) \
                        .props('flat dense round size=sm color=grey-8') \
                        .bind_enabled_from(self, 'busy', backward=lambda value: not value)
        if not self.preferences['profiles']:
            ui.label('Aucun profil pour l’instant. Nommez vos réglages actuels pour les '
                     'retrouver au prochain passage.').classes('muted')
        with ui.row().classes('w-full items-center gap-2 no-wrap pt-1'):
            self.profile_name = ui.input(placeholder='Travail · trimestre') \
                .props(f'outlined dense maxlength={preferences.NAME_LIMIT}').classes('grow') \
                .bind_enabled_from(self, 'busy', backward=lambda value: not value)
            ui.button('Enregistrer', icon='bookmark_add', on_click=self.save_profile) \
                .props('outline no-caps').classes('profile-save') \
                .bind_enabled_from(self, 'busy', backward=lambda value: not value)

    @ui.refreshable
    def format_chip(self):
        layout = self.base_config().layout
        ui.html(f'<span class="chip">{layout.device.label} · {layout.device.summary}</span>',
                sanitize=False)

    @staticmethod
    def sheet_note(count, sheets, plural):
        """Say out loud when a list no longer fits on one sheet."""
        if sheets < 2:
            return None
        return f'{count} {plural} → {sheets} feuillets de {-(-count // sheets)}'

    @ui.refreshable
    def metrics(self):
        config = self.config
        base = self.base_config()
        layout = base.layout
        ui.label(f'Format appliqué · {layout.device.label} · '
                 f'{layout.device.summary}').classes('muted')
        notes = [self.sheet_note(base.tasks_per_list, base.list_sheets, 'tâches par liste')]
        if self.mode == 'dated':
            notes.append(self.sheet_note(config.weekly_tasks, config.week_sheets,
                                         'actions par semaine'))
        notes = [note for note in notes if note]
        if notes:
            ui.label(' · '.join(notes) + f'. Ce format en tient '
                     f'{layout.backlog_capacity} par feuillet en confort '
                     f'{DENSITIES[layout.density].lower()} ; aucune tâche n’est retirée.'
                     ).classes('muted split-note')
        if self.mode == 'dated':
            ui.label(f'{config.start_date} → {config.end_date:%Y-%m-%d}').classes('muted')
            values = [(len(config.dates), 'journées'), (len(config.weeks), 'semaines'), (config.total_pages, 'pages')]
        else:
            effective = replace(config, days=min(3, config.days)) if self.short else config
            values = [(effective.days, 'journées'), (config.task_count, 'tâches'), (effective.total_pages, 'pages')]
        with ui.element('div').classes('metrics'):
            for value, label in values:
                with ui.column().classes('gap-0'):
                    ui.label(f'{value:,}'.replace(',', ' ')).classes('metric-value')
                    ui.label(label).classes('muted')

    @ui.refreshable
    def download_area(self):
        if self.error:
            ui.label(self.error).classes('status error').props('role=alert')
        if self.busy:
            with ui.row().classes('items-center'):
                ui.spinner(size='sm')
                ui.label(self.activity or 'Chargement…').classes('muted')
        elif self.dirty:
            ui.label('Réglages modifiés. L’aperçu sera actualisé avec vos nouveaux choix.').classes('muted')
        if self.output:
            artifact = self.output
            ui.label(f'{artifact.pages:,} pages · {len(artifact.pdf_bytes) / 1024**2:.1f} Mo · prêt à télécharger'.replace(',', ' ')).classes('status')
            ui.button('Télécharger le carnet', icon='download',
                      on_click=lambda: self.download_pdf(artifact)).classes('w-full').bind_enabled_from(self, 'busy', backward=lambda value: not value)

    async def download_pdf(self, artifact):
        window = app.native.main_window
        if window is None:
            ui.download(artifact.pdf_bytes, artifact.filename, 'application/pdf')
            return
        if self.busy:
            return
        self.busy = True
        try:
            from webview import FileDialog
            selected = await window.create_file_dialog(
                dialog_type=FileDialog.SAVE, save_filename=artifact.filename,
                file_types=('PDF (*.pdf)',),
            )
            if not selected:
                return
            target = Path(selected if isinstance(selected, str) else selected[0])
            await asyncio.to_thread(target.write_bytes, artifact.pdf_bytes)
            ui.notify(f'PDF enregistré : {target.name}', type='positive')
        except Exception:
            logging.exception('Native PDF save failed')
            ui.notify('Le PDF n’a pas pu être enregistré. Vous pouvez réessayer et choisir un autre emplacement.',
                      type='negative')
        finally:
            self.busy = False

    @ui.refreshable
    def preview_tabs_area(self):
        self.kind_control = ui.toggle(dict(enumerate(self.preview_tabs())), value=self.kind,
                                      on_change=self.change_kind) \
            .props('unelevated toggle-color=primary color=transparent text-color=grey-8') \
            .classes('preview-tabs') \
            .bind_enabled_from(self, 'busy', backward=lambda value: not value)

    @ui.refreshable
    def preview_area(self):
        with ui.element('div').classes('paper-wrap'):
            if self.kind in self.images:
                ui.image(self.images[self.kind]).props('no-spinner no-transition').classes('paper')
            else:
                with ui.column().classes('items-center p-12'):
                    ui.icon('description', size='48px').classes('text-gray-400')
                    ui.label('Votre aperçu apparaît ici').classes('muted')
        with ui.row().classes('preview-actions'):
            ui.button('Actualiser l’aperçu', icon='refresh', on_click=self.refresh_preview) \
                .props('outline dense no-caps') \
                .bind_enabled_from(self, 'busy', backward=lambda value: not value)
            if self.sample:
                sample = self.sample
                ui.button(f'Télécharger les {sample.pages} pages d’aperçu', icon='file_download',
                          on_click=lambda: self.download_pdf(sample)).props('flat dense').bind_enabled_from(self, 'busy', backward=lambda value: not value)

    def short_changed(self, event):
        self.revision += 1
        self.short = event.value
        self.output = None
        self.metrics.refresh()
        self.download_area.refresh()

    @ui.refreshable
    def body(self):
        self.fields = {}
        self.family = self.exact_dates = None
        dated = self.mode == 'dated'
        config = self.config
        base = config.base if dated else config
        with ui.row().classes('intro'):
            with ui.column().classes('gap-0'):
                ui.label('VOTRE CARNET, À VOTRE MESURE').classes('eyebrow')
                ui.html('<h1>Une place pour chaque idée.</h1>', sanitize=False)
                ui.label('Calendrier, semaines et backlog reliés.' if dated else 'Des journées libres. Des listes qui gardent le contexte.').classes('muted')
            self.format_chip()
        with ui.element('div').classes('workspace'):
            with ui.column().classes('settings'):
                with ui.column().classes('w-full gap-3'):
                    ui.label('01 / Support & format').classes('section-title')
                    self.device_fields()
                with ui.column().classes('w-full gap-3 pt-2'):
                    ui.label('02 / Votre rythme').classes('section-title')
                    if dated:
                        self.period_fields()
                        with ui.element('div').classes('fields'):
                            self.number('week_pages', 'Pages de tâches / semaine', config.week_pages, 1, 3)
                            self.number('weekly_tasks', 'Actions / liste', config.weekly_tasks, 1, 40)
                        self.field('include_weekends', ui.checkbox('Inclure les week-ends', value=config.include_weekends))
                        ui.label('Sans week-ends : moins de pages Meeting et Notes. Le calendrier reste complet.').classes('muted')
                        ui.label('Au-delà de trois mois, la barre latérale indexe les mois ; chaque calendrier ouvre ses semaines et ses journées.').classes('muted')
                        self.field('monthly_priorities', ui.checkbox(
                            'Une page Priorités après chaque calendrier', value=config.monthly_priorities))
                        ui.label('Trois priorités, leurs échéances et un espace libre, reliés au '
                                 'calendrier du mois et à ses semaines.').classes('muted')
                        self.field('weekly_overview', ui.checkbox(
                            'Une vue « sept jours » avant les tâches', value=config.weekly_overview))
                        self.field('weekly_review', ui.checkbox(
                            'Un bilan après les tâches de la semaine', value=config.weekly_review))
                        ui.label('Terminé / À reporter / À retenir, avec un retour aux tâches et '
                                 'un accès à la semaine suivante.').classes('muted')
                    else:
                        self.number('days', 'Journées non datées', base.days, 1, 400)
                    self.number('notes_pages', 'Pages Notes après chaque Meeting', base.notes_pages, 0, 3)
                with ui.expansion('03 / Backlog & contexte' if dated else '03 / Listes & contexte', value=True):
                    with ui.column().classes('w-full gap-4'):
                        with ui.element('div').classes('fields'):
                            self.number('list_count', 'Listes', base.list_count, 1, 10)
                            self.number('tasks_per_list', 'Tâches / liste', base.tasks_per_list, 1, 40)
                        self.number('detail_pages', 'Pages de contexte / tâche', base.detail_pages, 1, 5)
                with ui.expansion('04 / Style & langue', value=True):
                    with ui.column().classes('w-full gap-4'):
                        self.field('language', ui.select(LANGUAGES, value=base.language, label='Langue du PDF'))
                        self.field('typography', ui.select(TYPOGRAPHIES, value=base.typography, label='Typographie'))
                        ui.label('Manrope contraste renforce les petits caractères sur écran e-ink.').classes('muted')
                        self.field('meeting_layout', ui.select(
                            MEETING_LAYOUTS, value=base.meeting_layout, label='Composition des Meetings'))
                        with ui.element('div').classes('fields'):
                            self.field('meeting_note_style', ui.select(
                                NOTE_STYLES, value=base.meeting_note_style, label='Fond des Notes'))
                            self.field('task_note_style', ui.select(
                                NOTE_STYLES, value=base.task_note_style, label='Fond des contextes'))
                        ui.label('Le fond ne change que la zone d’écriture : titres, liens et '
                                 'barre latérale restent nets.').classes('muted')
                with ui.expansion('05 / Projets'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.element('div').classes('fields'):
                            self.number('project_count', 'Fiches projet', base.project_count, 0, 12)
                            self.number('project_notes_pages', 'Pages Notes / projet',
                                        base.project_notes_pages, 0, 10)
                        self.field('project_names', ui.textarea(
                            'Noms des projets', value='\n'.join(base.project_names))).props('rows=3')
                        ui.label('Un nom par ligne ; les noms au-delà du nombre de fiches ne sont '
                                 'pas utilisés. Zéro fiche : aucune page ni aucun lien de projet. '
                                 'Une fiche garde objectif, prochaines actions, décisions et notes, '
                                 'avec une place fixe pour votre référence backlog écrite à la '
                                 'main.').classes('muted')
                with ui.expansion('Titre & noms des listes'):
                    with ui.column().classes('w-full gap-4'):
                        self.field('title', ui.input('Titre du carnet', value=base.title)).props('maxlength=48')
                        self.field('list_names', ui.textarea('Noms des listes', value='\n'.join(base.list_names))).props('rows=4')
                        ui.label('Un nom par ligne, 24 caractères maximum. Facultatif.').classes('muted')
                with ui.expansion('Mes profils de réglages'):
                    with ui.column().classes('w-full gap-3'):
                        ui.label('Folio rouvre vos derniers réglages valides, séparément pour '
                                 'chaque mode. Un profil garde en plus une combinaison nommée.').classes('muted')
                        self.profiles_area()
                with ui.expansion('Importer / sauvegarder mes réglages'):
                    with ui.column().classes('w-full gap-3'):
                        ui.upload(label='Importer un fichier JSON', on_upload=self.import_config, auto_upload=True,
                                  max_file_size=65536, on_rejected=lambda: ui.notify('Choisissez un fichier JSON de moins de 64 Ko.', type='negative')).props('accept=.json').bind_enabled_from(self, 'busy', backward=lambda value: not value)
                        ui.button('Sauvegarder les réglages', icon='save_alt', on_click=self.export_config).props('flat').bind_enabled_from(self, 'busy', backward=lambda value: not value)
                self.metrics()
                if not dated:
                    ui.checkbox('Essai : seulement 3 journées', value=self.short, on_change=self.short_changed).bind_enabled_from(self, 'busy', backward=lambda value: not value)
                    ui.label('Toutes les listes et leurs notes restent incluses.').classes('muted')
                ui.button('Actualiser l’aperçu', on_click=self.refresh_preview, icon='refresh').props('outline').classes('w-full').bind_enabled_from(self, 'busy', backward=lambda value: not value)
                ui.button('Générer mon carnet', on_click=self.generate, icon='auto_stories').classes('w-full py-2').bind_enabled_from(self, 'busy', backward=lambda value: not value)
                self.download_area()
            with ui.column().classes('preview-panel'):
                with ui.row().classes('preview-toolbar'):
                    ui.label('Votre carnet, page par page').classes('text-base font-bold')
                    ui.label('APERÇU').classes('eyebrow')
                self.preview_tabs_area()
                self.preview_area()
                ui.label('Les liens sont actifs dans le carnet complet. L’aperçu sert à vérifier la mise en page.').classes('muted')
                with ui.expansion('Se repérer dans le carnet').classes('w-full'):
                    ui.label(('Meeting → semaine → backlog : notez la liste et le numéro de tâche dans la semaine, puis W38 dans le backlog pour retrouver votre semaine. ' if dated else 'Les onglets ouvrent vos listes ; la flèche d’une tâche ouvre son contexte. « Journées » vous ramène à l’index. ') + 'Les références manuscrites restent des annotations ; elles ne créent pas de liens automatiques.').classes('muted p-2')

    def render(self):
        self.client = ui.context.client
        self.restore()
        with ui.column().classes('shell'):
            with ui.row().classes('masthead'):
                ui.label('Folio').classes('brand')
                ui.button('Reprendre mon écriture', icon='draw',
                          on_click=lambda: ui.navigate.to('/transfert')).props('flat')
                self.mode_control = ui.toggle(MODES, value=self.mode, on_change=self.switch_mode).props('unelevated toggle-color=primary color=white text-color=grey-8').classes('mode-switch').bind_enabled_from(self, 'busy', backward=lambda value: not value)
            self.body()
            ui.label('Votre atelier PDF · Réglages exportables · Français & English').classes('footer-note muted')
        ui.timer(0.1, self.refresh_preview, once=True)


class TransferWorkspace:
    """Carry the handwriting of a written notebook onto a freshly generated one.

    Nothing is kept: both files land in a directory of their own, which goes
    away with the tab that created it.
    """

    SOURCE = {'suffix': ('.note', '.pdf'),
              'label': 'Mon carnet écrit · .note ou PDF',
              'hint': ('L’archive .note de la tablette garde l’encre sur un calque à part : '
                       'c’est la meilleure source. Un PDF exporté marche aussi, en '
                       'reconstituant l’encre par soustraction.')}
    TARGET = {'suffix': ('.pdf', '.note'),
              'label': 'Mon nouveau carnet · PDF ou .note',
              'hint': ('Un PDF reçoit votre écriture comme une image. Pour garder des '
                       'tracés que la gomme reprend, importez d’abord ce PDF dans la '
                       'tablette, réexportez-le en .note vide, et déposez ce .note ici.')}
    SLOTS = (('source', SOURCE), ('target', TARGET))
    LIMIT = 400 * 1024 * 1024
    MISSING = ('La reprise d’écriture demande des bibliothèques supplémentaires : '
               'pip install -r requirements-transfer.txt, puis Ghostscript '
               '(brew install ghostscript).')

    @staticmethod
    def available():
        """The generator must keep working when the transfer extras are absent."""
        try:
            import transfer_ink
        except ImportError:
            return None
        return transfer_ink

    def __init__(self):
        self.folder = Path(tempfile.mkdtemp(prefix='folio-transfert-'))
        self.files = {}
        self.status = {}
        self.result = None
        self.busy = False
        self.lines = []
        self.sections, self.chosen, self.previews, self.kept = [], set(), {}, set()
        self.unfolded, self.offset, self.where = set(), (0, 0), {}
        self.lost = set()

    def close(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    @property
    def keeps_strokes(self):
        """A `.note` destination is a notebook the tablet has just made."""
        target = self.files.get('target')
        return bool(target and target.suffix.lower() == '.note')

    async def take_stock(self):
        """List what the written notebook holds, once both files are in."""
        self.sections, self.chosen, self.previews, self.kept = [], set(), {}, set()
        self.unfolded, self.offset, self.where = set(), (0, 0), {}
        self.lost = set()
        if not ({'source', 'target'} <= set(self.files) and self.keeps_strokes
                and self.files['source'].suffix.lower() == '.note'):
            return
        try:
            module = self.available()
            if module is None:
                return
            self.sections = await cpu_job(module.inventory,
                                          self.files['source'])
            self.chosen = {page for _, rows in self.sections for page, _, _ in rows}
        except Exception as error:  # noqa: BLE001 — the message belongs on screen
            self.lines = [f'Lecture du carnet écrit impossible : {error}']

    def toggle_page(self, page, value=None):
        if page in self.kept or page in self.lost:
            return
        taken = (page not in self.chosen) if value is None else value
        self.chosen.add(page) if taken else self.chosen.discard(page)
        self.picker.refresh()

    def toggle_section(self, rows, value):
        for page, _, _ in rows:
            if page in self.kept or page in self.lost:
                continue
            self.chosen.add(page) if value else self.chosen.discard(page)
        self.picker.refresh()

    def choose_all(self, value):
        self.chosen = ({page for _, rows in self.sections for page, _, _ in rows
                        if page not in self.kept and page not in self.lost}
                       if value else set())
        self.picker.refresh()

    async def show_section(self, section, rows, opened):
        """Draw the handwriting of one section, the first time it is opened.

        Which sections are open is remembered here, because a refresh rebuilds
        them all: without it, a section would fold itself shut at the very
        moment its thumbnails arrived.
        """
        self.unfolded.add(section) if opened else self.unfolded.discard(section)
        if not opened:
            return
        missing = [page for page, _, _ in rows if page not in self.previews]
        if missing:
            module = self.available()
            arrivals = {page: self.where.get(page, (None, page))[1] for page in missing}
            self.previews.update(await cpu_job(
                module.page_previews, self.files['source'], missing,
                self.files['target'], self.offset, 320, arrivals))
            self.picker.refresh()

    @ui.refreshable
    def picker(self):
        if not self.sections:
            return
        total = sum(len(rows) for _, rows in self.sections)
        with ui.row().classes('items-center justify-between w-full'):
            ui.label(f'{total} pages écrites · {len(self.sections)} sections') \
                .classes('text-sm font-bold')
            with ui.row().classes('gap-1'):
                ui.button('Tout', on_click=lambda: self.choose_all(True)).props('flat dense')
                ui.button('Rien', on_click=lambda: self.choose_all(False)).props('flat dense')
        with ui.column().classes('pick'):
            for section, rows in self.sections:
                free = [page for page, _, _ in rows
                        if page not in self.kept and page not in self.lost]
                taken = sum(1 for page in free if page in self.chosen)
                with ui.expansion(value=section in self.unfolded,
                                  on_value_change=lambda event, s=section, r=rows:
                                  self.show_section(s, r, event.value)) \
                        .classes('w-full') as panel:
                    with panel.add_slot('header'):
                        with ui.row().classes('pick-head'):
                            ui.checkbox(section, value=bool(free) and taken == len(free),
                                        on_change=lambda event, r=rows:
                                        self.toggle_section(r, event.value)) \
                                .on('click.stop').set_enabled(bool(free))
                            ui.label(f'{taken}/{len(rows)}').classes('pick-count')
                    with ui.element('div').classes('shots'):
                        for page, label, share in rows:
                            held = page in self.kept or page in self.lost
                            classes = 'shot gap-0' + (' on' if page in self.chosen else '')
                            with ui.column().classes(classes + (' held' if held else '')) \
                                    .on('click', lambda p=page: self.toggle_page(p)):
                                shot = self.previews.get(page)
                                if shot:
                                    ui.html(f'<img src="{shot}" alt="page {page}">')
                                with ui.column().classes('shot-foot gap-1'):
                                    if page in self.lost:
                                        ui.html(f'<b>Page {page}</b><span>Cette section '
                                                'n’existe plus dans le nouveau '
                                                'carnet</span>')
                                    elif held:
                                        ui.html(f'<b>Page {page}</b>'
                                                '<span>Déjà écrite dans le nouveau '
                                                'carnet — elle est conservée</span>')
                                    else:
                                        ui.checkbox(f'Page {page}',
                                                    value=page in self.chosen,
                                                    on_change=lambda event, p=page:
                                                    self.toggle_page(p, event.value)) \
                                            .on('click.stop')
                                    arrival = self.where.get(page, (None, page))[1]
                                    moved = ('' if arrival in (None, page)
                                             else f' → page {arrival}')
                                    ui.html(f'<span>{label} · {share:.1f} % d’encre'
                                            f'{moved}</span>')

    def destination(self, slot, spec, name):
        """Where an uploaded file lands, or None when its suffix is wrong."""
        clean = Path(name).name
        if not clean.lower().endswith(spec['suffix']):
            return None
        return self.folder / f'{slot}-{clean}'

    def accept(self, slot, spec):
        async def handler(event):
            # NiceGUI streams a large upload straight to disk, so `save` moves
            # tens of megabytes without ever holding them in memory. Only the
            # actions refresh: rebuilding the slots would delete the other
            # uploader while its own file is still on its way.
            try:
                upload = event.file
                path = self.destination(slot, spec, upload.name)
                if path is None:
                    self.status[slot].set_text('Ce format n’est pas accepté ici : '
                                               + ' ou '.join(spec['suffix']) + '.')
                    return
                await upload.save(path)
                self.files[slot] = path
                self.result = None
                self.status[slot].set_text(
                    f'{path.name.split("-", 1)[-1]} · {path.stat().st_size / 1e6:.1f} Mo')
                await self.take_stock()
            except Exception as error:  # noqa: BLE001 — a swallowed upload is a dead button
                self.lines = [f'Import impossible : {error}']
                self.status[slot].set_text('Ce fichier n’a pas pu être lu.')
            finally:
                self.picker.refresh()
                self.actions.refresh()
        return handler

    def slots(self):
        """Built once and left alone: the uploaders own their own feedback."""
        with ui.element('div').classes('slots'):
            for slot, spec in self.SLOTS:
                with ui.column().classes('slot'):
                    ui.label(spec['label']).classes('text-sm font-bold')
                    ui.upload(label='Déposer le fichier', auto_upload=True,
                              max_file_size=self.LIMIT,
                              on_upload=self.accept(slot, spec),
                              on_rejected=lambda: ui.notify(
                                  'Fichier trop lourd : 400 Mo au maximum.',
                                  type='negative')) \
                        .props(f'accept={",".join(spec["suffix"])}') \
                        .bind_enabled_from(self, 'busy',
                                           backward=lambda value: not value)
                    self.status[slot] = ui.label('Aucun fichier pour l’instant.') \
                        .classes('muted')
                    ui.label(spec['hint']).classes('muted')

    @ui.refreshable
    def actions(self):
        ready = {'source', 'target'} <= set(self.files) and not self.busy
        if self.sections:
            ready = ready and bool(self.chosen)
        if self.keeps_strokes:
            ui.label('Vos tracés restent des tracés : le carnet que la tablette vient '
                     'de créer garde ses identifiants et ses octets, votre écriture '
                     'vient s’y ajouter. Gomme et déplacement fonctionnent encore.'
                     ).classes('muted')
        else:
            ui.label('Votre écriture arrive comme une image : elle s’ouvre partout, et '
                     'vous écrivez par-dessus, sans pouvoir la reprendre trait par '
                     'trait. Déposez un .note en destination pour garder les tracés.'
                     ).classes('muted')
        ui.button('Reporter mon écriture', icon='draw', on_click=self.run) \
            .classes('py-2').set_enabled(ready)
        if self.lines:
            ui.html('<div class="journal">'
                    + '\n'.join(line.replace('&', '&amp;').replace('<', '&lt;')
                                for line in self.lines) + '</div>')
        if self.result:
            kind = ('application/pdf' if self.result.suffix == '.pdf'
                    else 'application/octet-stream')
            ui.button(f'Télécharger {self.result.name}', icon='download',
                      on_click=lambda: ui.download(self.result.read_bytes(),
                                                   self.result.name, kind)) \
                .props('outline')

    async def run(self):
        if self.busy or not {'source', 'target'} <= set(self.files):
            return
        self.busy, self.result = True, None
        self.lines = ['Lecture du carnet écrit, calage, report de l’encre…',
                      'Comptez une vingtaine de secondes pour un carnet complet.']
        self.actions.refresh()
        target = self.files['target']
        stem = target.name.split('-', 1)[-1].removesuffix('.pdf').removesuffix('.note')
        suffix = '-repris.pdf.note' if self.keeps_strokes else '-repris.pdf'
        output = self.folder / (stem.removesuffix('.pdf') + suffix)
        pages = sorted(self.chosen) if self.sections else None
        try:
            _, lines = await cpu_job(self.available().transfer_report,
                                     self.files['source'], target, output, None, pages)
            self.lines, self.result = lines, output
            ui.notify('Écriture reportée.', type='positive')
        except Exception as error:  # noqa: BLE001 — the message belongs on screen
            self.lines = [str(error) or error.__class__.__name__]
            ui.notify('Le transfert a échoué : voyez le journal.', type='negative')
        finally:
            self.busy = False
            self.actions.refresh()

    def render(self):
        ui.context.client.on_disconnect(self.close)
        with ui.column().classes('shell'):
            with ui.row().classes('masthead'):
                ui.label('Folio').classes('brand')
                ui.button('Retour à l’atelier', icon='arrow_back',
                          on_click=lambda: ui.navigate.to('/')).props('flat')
            with ui.column().classes('intro w-full items-start'):
                ui.label('REPRENDRE MON ÉCRITURE').classes('eyebrow')
                ui.html('<h1>Votre carnet écrit, reporté sur la nouvelle édition</h1>')
                ui.label('Folio lit les pages que vous avez écrites, mesure le décalage '
                         'entre les deux éditions et repose votre encre exactement sur '
                         'ses lignes. Rien n’est envoyé ailleurs : tout se passe ici, et '
                         'les fichiers disparaissent avec cet onglet.').classes('muted')
            if self.available() is None:
                ui.label(self.MISSING).classes('muted')
                return
            self.slots()
            self.picker()
            with ui.column().classes('w-full gap-3'):
                self.actions()


app.add_static_files('/planner-fonts', ROOT / 'assets/fonts/Manrope')
app.on_shutdown(shutdown_jobs)


@ui.page('/')
def index():
    ui.colors(primary='#235c4f', secondary='#dfe8da', accent='#235c4f')
    ui.add_css(CSS)
    PlannerWorkspace().render()


@ui.page('/transfert')
def transfer_page():
    ui.colors(primary='#235c4f', secondary='#dfe8da', accent='#235c4f')
    ui.add_css(CSS)
    TransferWorkspace().render()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default=None)
    parser.add_argument('--port', type=int, default=8080)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--native', action='store_true', help='Open a desktop window (requires requirements-native.txt)')
    modes.add_argument('--web', action='store_true', help='Listen on all interfaces for hosting')
    parser.add_argument('--no-open', action='store_true', help='Do not open a browser automatically')
    args = parser.parse_args()
    storage_secret = os.environ.get('NICEGUI_STORAGE_SECRET')
    if not storage_secret:
        secret_path = Path('.nicegui/storage-secret')
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            storage_secret = secret_path.read_text().strip()
        else:
            storage_secret = secrets.token_urlsafe(48)
            with os.fdopen(descriptor, 'w') as secret_file:
                secret_file.write(storage_secret)
    if args.native:
        try:
            import webview  # noqa: F401
        except ImportError:
            parser.error('Le mode fenêtre nécessite : pip install -r requirements-native.txt')
        app.native.settings['ALLOW_DOWNLOADS'] = True
        webview_storage = Path('.nicegui/webview').resolve()
        webview_storage.mkdir(parents=True, exist_ok=True)
        app.native.start_args.update(private_mode=False, storage_path=str(webview_storage))
        icon = ROOT / 'assets/app/folio.png'
        if icon.is_file():
            app.native.start_args['icon'] = str(icon)
    ui.run(host=args.host or ('0.0.0.0' if args.web else '127.0.0.1'), port=args.port,
           native=args.native, window_size=(1400, 1000) if args.native else None,
           title='Folio', favicon='📖', language='fr', reload=False,
           storage_secret=storage_secret, show=not args.web and not args.no_open)


if __name__ == '__main__':
    main()
