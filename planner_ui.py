"""Local Streamlit interface for the AiPaper planner."""

import io
import inspect
import json
from dataclasses import replace

import streamlit as st

from planner_config import MEETING_LAYOUTS, PlannerConfig, TYPOGRAPHIES
from planner_formats import BRANDS, CUSTOM, DENSITIES, DEVICES
from planner_note_styles import NOTE_STYLES
from planner_i18n import LANGUAGES
from planner_manifest import build_manifest, preview_kinds
from planner_pdf import generate_pdf, generate_samples


PREVIEW_LABELS = {"meeting": "Meetings", "task-list": "Liste TODO", "task-notes": "Contexte",
                  "projects-index": "Projets", "project": "Fiche projet",
                  "project-notes": "Notes projet"}


def device_options():
    labels = {key: f"{BRANDS[device.brand]} · {device.label}"
              for key, device in DEVICES.items()}
    labels[CUSTOM] = "Personnalisé · dimensions en mm"
    return labels


def device_form(config, prefix):
    """Shared Support & format block for both Streamlit workspaces."""
    labels = device_options()
    keys = list(labels)
    device = st.selectbox("Modèle de tablette", keys, index=keys.index(config.device),
                          format_func=labels.get, key=f"{prefix}_field_device")
    density = st.selectbox("Confort d’écriture", list(DENSITIES),
                           index=list(DENSITIES).index(config.density),
                           format_func=DENSITIES.get, key=f"{prefix}_field_density")
    st.caption("Aéré écrit plus au large. Une liste qui ne tient plus se poursuit "
               "sur un feuillet suivant : aucune tâche n’est retirée.")
    c1, c2 = st.columns(2)
    with c1:
        width = st.number_input("Largeur (mm)", min_value=100, max_value=400,
                                value=int(config.custom_width_mm or 163), step=1,
                                key=f"{prefix}_field_width_mm",
                                help="Utilisée uniquement par le format personnalisé.")
    with c2:
        height = st.number_input("Hauteur (mm)", min_value=150, max_value=400,
                                 value=int(config.custom_height_mm or 217), step=1,
                                 key=f"{prefix}_field_height_mm",
                                 help="Portrait uniquement : hauteur au moins égale à la largeur.")
    layout_choice = st.selectbox("Composition des Meetings", list(MEETING_LAYOUTS),
                                 index=list(MEETING_LAYOUTS).index(config.meeting_layout),
                                 format_func=MEETING_LAYOUTS.get, key=f"{prefix}_field_meeting_layout")
    st.markdown("**Fonds d’écriture**")
    c1, c2 = st.columns(2)
    with c1:
        meeting_style = st.selectbox("Pages Notes", list(NOTE_STYLES),
                                     index=list(NOTE_STYLES).index(config.meeting_note_style),
                                     format_func=NOTE_STYLES.get, key=f"{prefix}_field_meeting_style")
    with c2:
        task_style = st.selectbox("Pages de contexte", list(NOTE_STYLES),
                                  index=list(NOTE_STYLES).index(config.task_note_style),
                                  format_func=NOTE_STYLES.get, key=f"{prefix}_field_task_style")
    st.caption("Le fond ne couvre que la zone d’écriture ; titres, liens et barre latérale "
               "restent nets.")
    return {"device": device, "density": density, "meeting_layout": layout_choice,
            "meeting_note_style": meeting_style, "task_note_style": task_style,
            "custom_width_mm": float(width) if device == CUSTOM else None,
            "custom_height_mm": float(height) if device == CUSTOM else None}


def render_planner_ui():
    st.title("Meetings & actions")
    st.markdown("Votre journée reste légère. Vos tâches gardent leur place.")
    st.caption("Votre carnet, au format de votre tablette · portrait · texte et tracés vectoriels")

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
            with st.expander("Support & format", expanded=True):
                surface = device_form(config, "planner")
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
            with st.expander("Fiches projet"):
                c1, c2 = st.columns(2)
                with c1:
                    project_count = st.number_input("Fiches projet", min_value=0, max_value=12,
                                                    value=config.project_count,
                                                    key="planner_field_projects")
                with c2:
                    project_notes = st.number_input("Pages Notes par projet", min_value=0, max_value=4,
                                                    value=config.project_notes_pages,
                                                    key="planner_field_project_notes")
                project_names = st.text_area("Noms des projets : un par ligne",
                                             value="\n".join(config.project_names),
                                             key="planner_field_project_names",
                                             help="Facultatif. 24 caractères maximum par nom.")
                st.caption("Zéro fiche : aucune page ni aucun lien de projet.")
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
                                       title=title, list_names=tuple(names.splitlines()),
                                       language=language, project_count=project_count,
                                       project_notes_pages=project_notes,
                                       project_names=tuple(project_names.splitlines())[:project_count],
                                       **surface)
            except ValueError as error:
                config = PlannerConfig.from_dict(st.session_state.planner_config)
                st.error(str(error))
            else:
                st.session_state.planner_config = config.to_dict()
                st.session_state.pop("planner_download", None)
                st.session_state.pop("planner_preview", None)

        st.caption("Les générations utilisent les réglages appliqués. Cliquez sur Appliquer après une modification.")
        st.divider()
        st.caption(f"{config.layout.device.label} · {config.layout.device.summary} · "
                   f"{config.layout.backlog_capacity} tâches par feuillet")
        m1, m2, m3 = st.columns(3)
        m1.metric("Journées", config.days)
        m2.metric("Tâches", config.task_count)
        m3.metric("Pages", f"{config.total_pages:,}".replace(',', ' '))
        short = st.checkbox("Carnet d’essai : seulement 3 journées", key="planner_short",
                            help="Toutes vos listes et fiches de tâches sont conservées, avec tous leurs liens.")
        output_config = replace(config, days=min(config.days, 3)) if short else config
        signature = "layout-33:" + json.dumps(output_config.to_dict(), sort_keys=True)
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
        labels = tuple(PREVIEW_LABELS.get(kind, kind)
                       for kind in preview_kinds(build_manifest(config), "undated"))
        kind = st.radio("Type de page", labels, horizontal=True,
                        label_visibility="collapsed", key="planner_preview_kind")
        key = "layout-33:" + json.dumps(config.to_dict(), sort_keys=True)
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
            st.image(cached["images"][labels.index(kind) if kind in labels else 0],
                     **{width_option: True})
        except (ImportError, OSError) as error:
            st.info("L’aperçu image nécessite Poppler. Le PDF d’aperçu reste disponible ci-dessous.")
            st.caption(str(error))
        st.caption("Aperçu visuel uniquement. Les liens sont actifs dans le carnet généré.")
        st.download_button(f"Télécharger ces {len(labels)} pages d’aperçu", data=cached["pdf"],
                           file_name="aipaper-apercu.pdf" if config.language == "fr" else "aipaper-preview-en.pdf",
                           mime="application/pdf", key="planner_preview_download")
        with st.expander("Comment retrouver mes tâches et ma journée ?"):
            st.markdown("Les onglets **01 à 10** ouvrent toujours les mêmes listes. "
                        "La flèche d’une tâche ouvre son contexte. Le bouton **Liste** vous y ramène.\n\n"
                        "**Journées** ouvre l’index : choisissez votre tableau de bord. "
                        "Les dates et les références comme **03-12** s’écrivent à la main. "
                        "Le PDF ne déplace ni ne synchronise vos annotations.")
