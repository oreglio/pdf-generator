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
from dataclasses import replace
from pathlib import Path

from nicegui import app, ui

from dated_planner_config import DatedPlannerConfig, month_choices, month_label
from nicegui_jobs import cpu_job, shutdown_jobs
from nicegui_service import generate_artifact, parse_config, render_preview
from planner_config import PlannerConfig, TYPOGRAPHIES
from planner_i18n import LANGUAGES

ROOT = Path(__file__).resolve().parent
MODES = {'dated': 'Carnet daté', 'undated': 'Carnet libre'}
KINDS = {'dated': ['Calendrier', 'Semaine', 'Meeting', 'Backlog', 'Contexte'],
         'undated': ['Meeting', 'Liste TODO', 'Contexte']}
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
.metrics { display: grid; grid-template-columns: repeat(3, 1fr); border-block: 1px solid #dedfd9; padding: 18px 0; width: 100%; }
.metric-value { font-size: 23px; font-weight: 700; letter-spacing: -.8px; }
.preview-panel { background: #eceee8; border: 1px solid #e0e3dc; border-radius: 12px; padding: 22px; min-height: 680px; width: 100%; gap: 16px; }
.preview-toolbar { width: 100%; justify-content: space-between; align-items: center; gap: 12px; }
.preview-tabs { width: 100%; background: transparent; }
.preview-tabs .q-btn { font-size: 12px; padding: 8px 12px; }
.paper-wrap { width: 100%; display: flex; align-items: center; justify-content: center; min-height: 480px; }
.paper { width: min(100%, 590px); background: white; box-shadow: 0 6px 24px #25352e14; }
.status { border-left: 3px solid #1c584c; padding: 10px 14px; background: #eff4ee; font-size: 13px; width: 100%; }
.error { color: #a3372c; background: #fff0ed; border-color: #a3372c; }
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
        self.fields = {}
        self.busy = False
        self.dirty = False
        self.short = False
        self.sample = None
        self.output = None
        self.images = {}
        self.kind = 0
        self.error = ''
        self.activity = ''
        self.revision = 0

    @property
    def config(self):
        return self.configs[self.mode]

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

    def number(self, key, label, value, minimum, maximum):
        return self.field(key, ui.number(label, value=value, min=minimum, max=maximum, step=1, precision=0))

    def read_config(self):
        base = self.config.base if self.mode == 'dated' else self.config
        payload = base.to_dict()
        for key in ('list_count', 'tasks_per_list', 'detail_pages', 'notes_pages', 'days'):
            if key in self.fields:
                value = self.fields[key].value
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value):
                    raise ValueError('Complétez les champs numériques avec des nombres entiers.')
                payload[key] = int(value)
        for key in ('language', 'typography', 'title'):
            payload[key] = self.fields[key].value
        payload['list_names'] = self.fields['list_names'].value.splitlines()
        if self.mode == 'dated':
            dated = self.config.to_dict()
            dated['base'] = payload
            dated['start_date'] = self.fields['start_date'].value
            dated['include_weekends'] = self.fields['include_weekends'].value
            for key in ('months', 'week_pages', 'weekly_tasks'):
                value = self.fields[key].value
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value):
                    raise ValueError('Complétez les champs numériques avec des nombres entiers.')
                dated[key] = int(value)
            return parse_config(self.mode, dated)
        return parse_config(self.mode, payload)

    def apply_draft(self):
        new_config = self.read_config()
        if new_config != self.config:
            self.configs[self.mode] = new_config
            self.sample = None
            self.images.clear()
            self.output = None
            self.preview_area.refresh()
        self.dirty = False
        self.error = ''
        self.metrics.refresh()

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

    @ui.refreshable
    def metrics(self):
        config = self.config
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
    def preview_area(self):
        with ui.element('div').classes('paper-wrap'):
            if self.kind in self.images:
                ui.image(self.images[self.kind]).props('no-spinner no-transition').classes('paper')
            else:
                with ui.column().classes('items-center p-12'):
                    ui.icon('description', size='48px').classes('text-gray-400')
                    ui.label('Votre aperçu apparaît ici').classes('muted')
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
        dated = self.mode == 'dated'
        config = self.config
        base = config.base if dated else config
        with ui.row().classes('intro'):
            with ui.column().classes('gap-0'):
                ui.label('VOTRE CARNET, À VOTRE MESURE').classes('eyebrow')
                ui.html('<h1>Une place pour chaque idée.</h1>', sanitize=False)
                ui.label('Calendrier, semaines et backlog reliés.' if dated else 'Des journées libres. Des listes qui gardent le contexte.').classes('muted')
            ui.label('Viwoods AiPaper · 1 920 × 2 560').classes('muted')
        with ui.element('div').classes('workspace'):
            with ui.column().classes('settings'):
                with ui.column().classes('w-full gap-3'):
                    ui.label('01 / Votre rythme').classes('section-title')
                    if dated:
                        with ui.element('div').classes('fields'):
                            self.field('start_date', ui.input('À partir du', value=config.start_date)).props('type=date')
                            self.field('months', ui.select(
                                {value: month_label(value) for value in month_choices(config.months)},
                                value=config.months, label='Durée'))
                            self.number('week_pages', 'Listes / semaine', config.week_pages, 1, 3)
                            self.number('weekly_tasks', 'Actions / liste', config.weekly_tasks, 1, 40)
                        self.field('include_weekends', ui.checkbox('Inclure les week-ends', value=config.include_weekends))
                        ui.label('Sans week-ends : moins de pages Meeting et Notes. Le calendrier reste complet.').classes('muted')
                        ui.label('Au-delà de trois mois, la barre latérale indexe les mois ; chaque calendrier ouvre ses semaines et ses journées.').classes('muted')
                    else:
                        self.number('days', 'Journées non datées', base.days, 1, 400)
                    self.number('notes_pages', 'Pages Notes après chaque Meeting', base.notes_pages, 0, 3)
                with ui.expansion('02 / Backlog & contexte' if dated else '02 / Listes & contexte', value=True):
                    with ui.column().classes('w-full gap-4'):
                        with ui.element('div').classes('fields'):
                            self.number('list_count', 'Listes', base.list_count, 1, 10)
                            self.number('tasks_per_list', 'Tâches / liste', base.tasks_per_list, 1, 40)
                        self.number('detail_pages', 'Pages de contexte / tâche', base.detail_pages, 1, 5)
                with ui.expansion('03 / Style & langue', value=True):
                    with ui.column().classes('w-full gap-4'):
                        self.field('language', ui.select(LANGUAGES, value=base.language, label='Langue du PDF'))
                        self.field('typography', ui.select(TYPOGRAPHIES, value=base.typography, label='Typographie'))
                        ui.label('Manrope contraste renforce les petits caractères sur écran e-ink.').classes('muted')
                with ui.expansion('Titre & noms des listes'):
                    with ui.column().classes('w-full gap-4'):
                        self.field('title', ui.input('Titre du carnet', value=base.title)).props('maxlength=48')
                        self.field('list_names', ui.textarea('Noms des listes', value='\n'.join(base.list_names))).props('rows=4')
                        ui.label('Un nom par ligne, 24 caractères maximum. Facultatif.').classes('muted')
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
                ui.toggle(dict(enumerate(KINDS[self.mode])), value=self.kind, on_change=self.change_kind).props('unelevated toggle-color=primary color=transparent text-color=grey-8').classes('preview-tabs').bind_enabled_from(self, 'busy', backward=lambda value: not value)
                self.preview_area()
                ui.label('Les liens sont actifs dans le carnet complet. L’aperçu sert à vérifier la mise en page.').classes('muted')
                with ui.expansion('Se repérer dans le carnet').classes('w-full'):
                    ui.label(('Meeting → semaine → backlog : notez la liste et le numéro de tâche dans la semaine, puis W38 dans le backlog pour retrouver votre semaine. ' if dated else 'Les onglets ouvrent vos listes ; la flèche d’une tâche ouvre son contexte. « Journées » vous ramène à l’index. ') + 'Les références manuscrites restent des annotations ; elles ne créent pas de liens automatiques.').classes('muted p-2')

    def render(self):
        self.client = ui.context.client
        with ui.column().classes('shell'):
            with ui.row().classes('masthead'):
                ui.label('Folio').classes('brand')
                self.mode_control = ui.toggle(MODES, value=self.mode, on_change=self.switch_mode).props('unelevated toggle-color=primary color=white text-color=grey-8').classes('mode-switch').bind_enabled_from(self, 'busy', backward=lambda value: not value)
            self.body()
            ui.label('Votre atelier PDF · Réglages exportables · Français & English').classes('footer-note muted')
        ui.timer(0.1, self.refresh_preview, once=True)


app.add_static_files('/planner-fonts', ROOT / 'assets/fonts/Manrope')
app.on_shutdown(shutdown_jobs)


@ui.page('/')
def index():
    ui.colors(primary='#235c4f', secondary='#dfe8da', accent='#235c4f')
    ui.add_css(CSS)
    PlannerWorkspace().render()


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
