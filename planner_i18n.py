"""English PDF labels; French source labels preserve the original edition."""

LANGUAGES = {"fr": "Français", "en": "English"}

ENGLISH = {
    "JOURS": "DAYS",
    "Accueil": "Home",
    "Journées": "Days",
    "Journees": "Days",
    "Jour": "Day",
    "Jour precedent": "Previous day",
    "Jour suivant": "Next day",
    "Precedent": "Previous",
    "Suite": "Next",
    "Début": "Start",
    "Liste": "List",
    "Liste {number:02d}": "List {number:02d}",
    "Mes listes": "My lists",
    "Mes journées": "My days",
    "Première journée >": "First day >",
    "Premiere journee": "First day",
    "Journees {label}": "Days {label}",
    "Journées {first:03d}-{last:03d}": "Days {first:03d}-{last:03d}",
    "VIWOODS AIPAPER / CARNET NON DATÉ": "VIWOODS AIPAPER / UNDATED NOTEBOOK",
    "INDEX DES JOURNÉES": "DAY INDEX",
    "JOURNÉE {day:03d}": "DAY {day:03d}",
    "Date / période": "Date / period",
    "Date / sujet": "Date / subject",
    "Sujet": "Subject",
    "TODO / LISTE {number:02d}": "TODO / LIST {number:02d}",
    "Retour aux listes": "Back to lists",
    "Retour liste {number:02d}": "Back to list {number:02d}",
    "Tache {number:02d}-{item:02d}": "Task {number:02d}-{item:02d}",
    "{count} tâches / liste": "{count} tasks / list",
    "{count} tâches": "{count} tasks",
    "Meetings non datés et tâches partagées - Viwoods AiPaper":
        "Undated meetings and shared tasks - Viwoods AiPaper",
    "Décisions": "Decisions",
    "Décisions & actions": "Decisions & actions",
    "Projets": "Projects",
    "PROJETS": "PROJECTS",
    "PROJET": "PROJECT",
    "< Projets": "< Projects",
    "Projet": "Project",
    "Projet {number:02d}": "Project {number:02d}",
    "PROJET {number:02d}": "PROJECT {number:02d}",
    "Retour aux projets": "Back to projects",
    "Objectif": "Goal",
    "Prochaines actions": "Next actions",
    "{count} fiches": "{count} sheets",
    "Actions": "Actions",
    "Aperçu - ": "Preview - ",
    "AiPaper - comparaison des polices": "AiPaper - font comparison",
    "VIWOODS AIPAPER / ESSAI TYPOGRAPHIQUE": "VIWOODS AIPAPER / FONT COMPARISON",
    "Trois façons de lire.": "Three ways to read.",
    "Même format. Même contenu. Trois rendus.": "Same format. Same content. Three styles.",
    "Pages 2 à 4 / fin et équilibré.": "Pages 2 to 4 / light and balanced.",
    "Manrope contraste": "Manrope contrast",
    "Pages 5 à 7 / traits plus présents.": "Pages 5 to 7 / stronger strokes.",
    "Pages 8 à 10 / lettres très différenciées.": "Pages 8 to 10 / distinctive letterforms.",
    "Sur la tablette": "On your tablet",
    "Affichez une page entière, avec le même zoom pour les trois essais.":
        "View a full page at the same zoom for all three samples.",
    "Comparez les petits numéros, les onglets et les lignes d’écriture.":
        "Compare the small numbers, tabs and writing lines.",
    "Ces pages comparent le rendu : leurs onglets ne sont pas actifs.":
        "These pages compare appearance; their tabs are not active.",
    "Pour tester les liens, ouvrez l’un des trois carnets complets.":
        "To test the links, open one of the three complete notebooks.",
}


def translate(language, source, **values):
    template = ENGLISH.get(source, source) if language == "en" else source
    return template.format(**values) if values else template
