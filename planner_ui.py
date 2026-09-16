"""Local Streamlit interface for the AiPaper planner."""

import io
import inspect
import json
from dataclasses import replace

import streamlit as st

from planner_config import PlannerConfig, TYPOGRAPHIES
from planner_i18n import LANGUAGES
from planner_pdf import generate_pdf, generate_samples


def render_planner_ui():
    st.title("Meetings & actions")
    st.markdown("Votre journée reste légère. Vos tâches gardent leur place.")
    st.caption("Viwoods AiPaper · 1 920 × 2 560 px · 300 ppp · portrait 162,56 × 216,75 mm")

    if "planner_config" not in st.session_state:
        st.session_state.planner_config = PlannerConfig().to_dict()
    config = PlannerConfig.from_dict(st.session_state.planner_config)

    with st.expander("Importer mes réglages"):
        uploaded = st.file_uploader("Configuration du carnet (.json)", type=["json"], key="planner_import_file")
        if st.button("Charger ces réglages", disabled=uploaded is None, key="planner_import"):
            try:
                config = PlannerConfig.from_dict(json.loads(uploaded.getvalue()))
            except (ValueError, TypeError, UnicodeDecodeError) as error:
                st.error(f"Configuration invalide : {error}")
            else:
                st.session_state.planner_config = config.to_dict()
                for key in list(st.session_state):
                    if key.startswith("planner_field_"):
                        del st.session_state[key]
                st.session_state.pop("planner_download", None)
                st.session_state.pop("planner_preview", None)
                st.success("Réglages chargés.")

    settings, preview = st.columns([1, 1.35], gap="large")
    with settings:
        st.subheader("Votre carnet")
        with st.form("planner_settings"):
            language = st.selectbox("Langue du PDF", options=list(LANGUAGES),
                                    index=list(LANGUAGES).index(config.language),
                                    format_func=LANGUAGES.get, key="planner_field_language")
            typography = st.selectbox("Typographie", options=list(TYPOGRAPHIES),
                                      index=list(TYPOGRAPHIES).index(config.typography),
                                      format_func=TYPOGRAPHIES.get, key="planner_field_typography")
            st.caption("Manrope contraste renforce les petits caractères sur l’écran e-ink.")
            days = st.number_input("Tableaux de bord non datés", min_value=1, max_value=400,
                                   value=config.days, key="planner_field_days")
            notes_pages = st.number_input("Pages Notes après chaque tableau de bord", min_value=0, max_value=3,
                                          value=config.notes_pages, key="planner_field_notes")
            c1, c2 = st.columns(2)
            with c1:
                lists = st.number_input("Listes TODO", min_value=1, max_value=10,
                                        value=config.list_count, key="planner_field_lists")
            with c2:
                tasks = st.number_input("Tâches par liste", min_value=1, max_value=40,
                                        value=config.tasks_per_list, key="planner_field_tasks")
            details = st.number_input("Pages de contexte par tâche", min_value=1, max_value=5,
                                      value=config.detail_pages, key="planner_field_details")
            with st.expander("Titre et noms des listes"):
                title = st.text_input("Titre du carnet", value=config.title, max_chars=48, key="planner_field_title")
                names = st.text_area("Un nom par ligne, dans l’ordre des listes",
                                     value='\n'.join(config.list_names), key="planner_field_names",
                                     help="Facultatif. Les listes sans nom restent numérotées. 24 caractères par nom.")
            applied = st.form_submit_button("Appliquer et actualiser l’aperçu", use_container_width=True)
        if applied:
            try:
                config = PlannerConfig(list_count=lists, tasks_per_list=tasks, detail_pages=details,
                                       days=days, notes_pages=notes_pages, typography=typography,
                                       title=title, list_names=tuple(names.splitlines()), language=language)
            except ValueError as error:
                config = PlannerConfig.from_dict(st.session_state.planner_config)
                st.error(str(error))
            else:
                st.session_state.planner_config = config.to_dict()
                st.session_state.pop("planner_download", None)
                st.session_state.pop("planner_preview", None)

        st.caption("Les générations utilisent les réglages appliqués. Cliquez sur Appliquer après une modification.")
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Journées", config.days)
        m2.metric("Tâches", config.task_count)
        m3.metric("Pages", f"{config.total_pages:,}".replace(',', ' '))
        short = st.checkbox("Carnet d’essai : seulement 3 journées", key="planner_short",
                            help="Toutes vos listes et fiches de tâches sont conservées, avec tous leurs liens.")
        output_config = replace(config, days=min(config.days, 3)) if short else config
        signature = "layout-30:" + json.dumps(output_config.to_dict(), sort_keys=True)
        download = st.session_state.get("planner_download")
        if download and download["signature"] != signature:
            del st.session_state.planner_download
            download = None
        if st.button("Générer mon PDF", type="primary", use_container_width=True, key="planner_generate"):
            with st.spinner(f"Création de {output_config.total_pages:,} pages et de leurs liens…"):
                buffer = io.BytesIO()
                generate_pdf(output_config, buffer)
                download = {"signature": signature, "data": buffer.getvalue(),
                            "name": output_config.pdf_filename}
                st.session_state.planner_download = download
        if download:
            st.success(f"Prêt · {output_config.total_pages:,} pages · {len(download['data']) / 1024**2:.2f} Mo")
            st.download_button("Télécharger le carnet", data=download["data"], file_name=download["name"],
                               mime="application/pdf", use_container_width=True, key="planner_download_button")
        st.download_button("Sauvegarder mes réglages", data=json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
                           file_name="aipaper-config.json" if config.language == "fr" else "aipaper-config-en.json",
                           mime="application/json", key="planner_export")

    with preview:
        st.subheader("Aperçu à l’échelle de la page")
        kind = st.radio("Type de page", ["Meetings", "Liste TODO", "Contexte"], horizontal=True,
                        label_visibility="collapsed", key="planner_preview_kind")
        key = "layout-30:" + json.dumps(config.to_dict(), sort_keys=True)
        cached = st.session_state.get("planner_preview")
        if cached is None or cached["key"] != key:
            buffer = io.BytesIO()
            generate_samples(config, buffer)
            cached = {"key": key, "pdf": buffer.getvalue(), "images": None}
            st.session_state.planner_preview = cached
        try:
            if cached["images"] is None:
                from pdf2image import convert_from_bytes
                from pdf2image.exceptions import (
                    PopplerNotInstalledError, PDFPageCountError,
                    PDFSyntaxError, PDFPopplerTimeoutError,
                )
                try:
                    pages = convert_from_bytes(cached["pdf"], dpi=110)
                except (PopplerNotInstalledError, PDFPageCountError,
                        PDFSyntaxError, PDFPopplerTimeoutError) as error:
                    raise OSError(str(error)) from error
                images = []
                for page in pages:
                    image = io.BytesIO()
                    page.save(image, format="PNG")
                    images.append(image.getvalue())
                cached["images"] = images
            width_option = "use_container_width" if "use_container_width" in inspect.signature(st.image).parameters else "use_column_width"
            st.image(cached["images"][["Meetings", "Liste TODO", "Contexte"].index(kind)], **{width_option: True})
        except (ImportError, OSError) as error:
            st.info("L’aperçu image nécessite Poppler. Le PDF d’aperçu reste disponible ci-dessous.")
            st.caption(str(error))
        st.caption("Aperçu visuel uniquement. Les liens sont actifs dans le carnet généré.")
        st.download_button("Télécharger ces 3 pages d’aperçu", data=cached["pdf"],
                           file_name="aipaper-apercu.pdf" if config.language == "fr" else "aipaper-preview-en.pdf",
                           mime="application/pdf", key="planner_preview_download")
        with st.expander("Comment retrouver mes tâches et ma journée ?"):
            st.markdown("Les onglets **01 à 10** ouvrent toujours les mêmes listes. "
                        "La flèche d’une tâche ouvre son contexte. Le bouton **Liste** vous y ramène.\n\n"
                        "**Journées** ouvre l’index : choisissez votre tableau de bord. "
                        "Les dates et les références comme **03-12** s’écrivent à la main. "
                        "Le PDF ne déplace ni ne synchronise vos annotations.")
