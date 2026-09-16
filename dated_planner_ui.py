"""Independent Streamlit workspace for the dated weekly planner."""

import inspect
import io
import json
from datetime import date

import streamlit as st

from dated_planner_config import DatedPlannerConfig, month_choices, month_label
from dated_planner_pdf import generate_dated_pdf, generate_dated_samples
from planner_config import PlannerConfig, TYPOGRAPHIES
from planner_i18n import LANGUAGES


PREVIEW_KINDS = ('Calendrier', 'Semaine', 'Meeting', 'Backlog', 'Contexte')
LAYOUT_VERSION = 'dated-12:'


def render_dated_planner_ui():
    st.title('Meetings & actions · daté')
    st.markdown('Une semaine pour agir. Un backlog pour garder le contexte.')
    st.caption('Viwoods AiPaper · 1 920 × 2 560 px · calendrier, semaines et journées reliés')

    if 'dated_config' not in st.session_state:
        st.session_state.dated_config = DatedPlannerConfig().to_dict()
    config = DatedPlannerConfig.from_dict(st.session_state.dated_config)

    with st.expander('Importer mes réglages datés'):
        uploaded = st.file_uploader('Configuration du carnet daté (.json)', type=['json'], key='dated_import_file')
        if st.button('Charger ces réglages', disabled=uploaded is None, key='dated_import'):
            try:
                config = DatedPlannerConfig.from_dict(json.loads(uploaded.getvalue()))
            except (ValueError, TypeError, UnicodeDecodeError) as error:
                st.error(f'Configuration invalide : {error}')
            else:
                st.session_state.dated_config = config.to_dict()
                for key in list(st.session_state):
                    if key.startswith('dated_field_'):
                        del st.session_state[key]
                st.session_state.pop('dated_download', None)
                st.session_state.pop('dated_preview', None)
                st.success('Réglages chargés.')

    settings, preview = st.columns([1, 1.35], gap='large')
    with settings:
        st.subheader('Votre période')
        with st.form('dated_settings'):
            c1, c2 = st.columns(2)
            with c1:
                start = st.date_input('À partir du', value=date.fromisoformat(config.start_date),
                                      min_value=date.min, max_value=date.max,
                                      format='DD/MM/YYYY', key='dated_field_start')
            with c2:
                durations = month_choices(config.months)
                months = st.selectbox('Durée', durations, index=durations.index(config.months),
                                      format_func=month_label, key='dated_field_months')
            include_weekends = st.checkbox('Inclure les week-ends', value=config.include_weekends,
                                           key='dated_field_include_weekends')
            st.caption('Sans week-ends : moins de pages Meeting et Notes. Le calendrier reste complet.')
            st.caption('Au-delà de trois mois, la barre latérale indexe les mois ; '
                       'chaque calendrier ouvre ses semaines et ses journées.')
            st.markdown('**Vos actions de la semaine**')
            c1, c2 = st.columns(2)
            with c1:
                week_pages = st.number_input('Listes par semaine', min_value=1, max_value=3,
                                              value=config.week_pages, key='dated_field_week_pages')
            with c2:
                weekly_tasks = st.number_input('Actions par liste', min_value=1, max_value=40,
                                                value=config.weekly_tasks, key='dated_field_weekly_tasks')
            st.caption('Des lignes à reporter librement. Les notes détaillées restent dans le backlog.')
            with st.expander('Backlog permanent et pages Notes'):
                c1, c2 = st.columns(2)
                with c1:
                    lists = st.number_input('Listes du backlog', min_value=1, max_value=10,
                                            value=config.base.list_count, key='dated_field_lists')
                with c2:
                    tasks = st.number_input('Tâches par liste', min_value=1, max_value=40,
                                            value=config.base.tasks_per_list, key='dated_field_tasks')
                details = st.number_input('Pages de contexte par tâche', min_value=1, max_value=5,
                                          value=config.base.detail_pages, key='dated_field_details')
                notes = st.number_input('Pages Notes après chaque Meeting', min_value=0, max_value=3,
                                        value=config.base.notes_pages, key='dated_field_notes')
            with st.expander('Langue, typographie et titres'):
                language = st.selectbox('Langue du PDF', list(LANGUAGES),
                                         index=list(LANGUAGES).index(config.base.language),
                                         format_func=LANGUAGES.get, key='dated_field_language')
                typography = st.selectbox('Typographie', list(TYPOGRAPHIES),
                                           index=list(TYPOGRAPHIES).index(config.base.typography),
                                           format_func=TYPOGRAPHIES.get, key='dated_field_typography')
                title = st.text_input('Titre du carnet', value=config.base.title, max_chars=48,
                                      key='dated_field_title')
                names = st.text_area('Noms des listes du backlog : un par ligne',
                                     value='\n'.join(config.base.list_names), key='dated_field_names',
                                     help='Facultatif. 24 caractères maximum par nom.')
            applied = st.form_submit_button('Appliquer et actualiser l’aperçu', use_container_width=True)
        if applied:
            try:
                base = PlannerConfig(list_count=lists, tasks_per_list=tasks, detail_pages=details,
                                     notes_pages=notes, typography=typography, title=title,
                                     list_names=tuple(names.splitlines()), language=language)
                config = DatedPlannerConfig(base=base, start_date=start.isoformat(), months=months,
                                            week_pages=week_pages, weekly_tasks=weekly_tasks,
                                            include_weekends=include_weekends)
            except ValueError as error:
                config = DatedPlannerConfig.from_dict(st.session_state.dated_config)
                st.error(str(error))
            else:
                st.session_state.dated_config = config.to_dict()
                st.session_state.pop('dated_download', None)
                st.session_state.pop('dated_preview', None)

        st.caption('Appliquez vos modifications pour actualiser la période, l’aperçu et le PDF.')
        st.divider()
        st.markdown(f"**Du {date.fromisoformat(config.start_date):%d/%m/%Y} au {config.end_date:%d/%m/%Y}**")
        m1, m2, m3 = st.columns(3)
        m1.metric('Journées', len(config.dates))
        m2.metric('Semaines', len(config.weeks))
        m3.metric('Pages', f'{config.total_pages:,}'.replace(',', ' '))
        signature = LAYOUT_VERSION + json.dumps(config.to_dict(), sort_keys=True)
        download = st.session_state.get('dated_download')
        if download and download['signature'] != signature:
            st.session_state.pop('dated_download', None)
            download = None
        if st.button('Générer mon carnet daté', type='primary', use_container_width=True, key='dated_generate'):
            with st.spinner(f'Création de {config.total_pages:,} pages et de leurs liens…'):
                buffer = io.BytesIO()
                generate_dated_pdf(config, buffer)
                download = {'signature': signature, 'data': buffer.getvalue(), 'name': config.pdf_filename}
                st.session_state.dated_download = download
        if download:
            st.success(f"Prêt · {config.total_pages:,} pages · {len(download['data']) / 1024**2:.2f} Mo")
            st.download_button('Télécharger le carnet daté', data=download['data'], file_name=download['name'],
                               mime='application/pdf', use_container_width=True, key='dated_download_button')
        st.download_button('Sauvegarder mes réglages datés',
                           data=json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
                           file_name=f'aipaper-dated-config-{config.base.language}.json',
                           mime='application/json', key='dated_export')

    with preview:
        st.subheader('Votre carnet, page par page')
        kind = st.radio('Type de page', PREVIEW_KINDS, horizontal=True, label_visibility='collapsed',
                        key='dated_preview_kind')
        cached = st.session_state.get('dated_preview')
        if cached is None or cached['key'] != signature:
            buffer = io.BytesIO()
            generate_dated_samples(config, buffer)
            cached = {'key': signature, 'pdf': buffer.getvalue(), 'images': None}
            st.session_state.dated_preview = cached
        try:
            if cached['images'] is None:
                from pdf2image import convert_from_bytes
                from pdf2image.exceptions import (
                    PopplerNotInstalledError, PDFPageCountError,
                    PDFSyntaxError, PDFPopplerTimeoutError,
                )
                try:
                    pages = convert_from_bytes(cached['pdf'], dpi=110)
                except (PopplerNotInstalledError, PDFPageCountError,
                        PDFSyntaxError, PDFPopplerTimeoutError) as error:
                    raise OSError(str(error)) from error
                images = []
                for page in pages:
                    image = io.BytesIO()
                    page.save(image, format='PNG')
                    images.append(image.getvalue())
                cached['images'] = images
            width_option = 'use_container_width' if 'use_container_width' in inspect.signature(st.image).parameters else 'use_column_width'
            st.image(cached['images'][PREVIEW_KINDS.index(kind)], **{width_option: True})
        except (ImportError, OSError) as error:
            st.info('L’aperçu image nécessite Poppler. Le PDF d’aperçu reste disponible ci-dessous.')
            st.caption(str(error))
        st.caption('Les liens sont actifs dans le carnet complet. Ces cinq pages servent à vérifier la mise en page.')
        st.download_button('Télécharger les 5 pages d’aperçu', data=cached['pdf'],
                           file_name=f'aipaper-dated-preview-{config.base.language}.pdf',
                           mime='application/pdf', key='dated_preview_download')
        with st.expander('Du Meeting au backlog, et retour'):
            st.markdown('**Meeting → semaine → backlog** : vos actions restent près de vos journées ; '
                        'leur contexte reste au même endroit.\n\n'
                        'Dans la semaine, écrivez **02-12** pour retrouver la tâche 12 de la liste 02. '
                        'Dans le backlog, notez **W38** dans le champ libre ; l’onglet de cette semaine '
                        'permet d’y revenir directement.\n\n'
                        'Les références manuscrites ne deviennent pas des liens. Les actions inachevées '
                        'se reportent à la main ; les notes détaillées restent dans le backlog.')
