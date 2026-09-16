# Meetings & actions — Viwoods AiPaper

## Installer une fois

Depuis la racine du dépôt, avec Python 3.11 ou plus récent (vérifié avec 3.13) :

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements-local.txt
```

Pour l’aperçu image, installer aussi Poppler : `brew install poppler` sur macOS,
ou `sudo apt-get install poppler-utils` sur Debian/Ubuntu. Sans Poppler, la
création et le téléchargement du PDF restent disponibles.

Pour **uniquement générer en ligne de commande**, remplacer l’installation des
dépendances ci-dessus par `venv/bin/python -m pip install -r requirements-pdf.txt`.
Streamlit et Poppler ne sont pas nécessaires dans ce cas. Les polices et leurs
licences sont incluses dans `assets/fonts/` : aucun téléchargement supplémentaire.

## Lancer l’interface locale

Double-cliquer sur **ouvrir-planner.command** sur macOS, ou lancer :

```bash
venv/bin/python -m streamlit run pdf_generator_ui.py --server.address=127.0.0.1
```

Ouvrir http://127.0.0.1:8501. Arrêter avec `Ctrl+C` dans le terminal.
Choisir les réglages, cliquer sur **Appliquer et actualiser l’aperçu**, puis
**Générer mon PDF**. Le mode Viwoods est sélectionné au démarrage ; le générateur
historique reste accessible à gauche. Les réglages s’importent et s’exportent en
JSON depuis l’interface.
Le champ **Langue du PDF** propose **Français** (par défaut) et **English**.
L’aperçu suit la langue appliquée ; l’interface reste en français.

## Régénérer sans interface

Pour retrouver le carnet Manrope validé pendant les essais :

```bash
venv/bin/python generate_planner.py
```

Résultat : **output/pdf/aipaper-manrope-200j.pdf** (1 416 pages).
Un rapport de durée, taille et nombre de pages est écrit à côté dans
`generation-report.json`. Les fichiers portant le même nom sont remplacés ;
conserver séparément les carnets annotés sur la tablette.

Autres commandes :

```bash
# Version anglaise, à côté du carnet français conservé
venv/bin/python generate_planner.py --language en

# Garder une nouvelle version dans un dossier distinct
venv/bin/python generate_planner.py --output-dir output/mon-essai

# Carnet plus court (les 400 tâches et leurs contextes restent présents)
venv/bin/python generate_planner.py --days 3 --output-dir output/essai-3j

# Les trois variantes et le comparatif visuel de 10 pages
venv/bin/python generate_planner.py --all-variants --comparison

# Reprendre les réglages exportés par l’interface
venv/bin/python generate_planner.py --config chemin/mes-reglages.json

# Voir toutes les options
venv/bin/python generate_planner.py --help
```

Les polices proposées sont `manrope`, `manrope-contrast` et `atkinson`.
La commande anglaise produit `output/pdf/aipaper-manrope-en-200d.pdf`, également
de 1 416 pages, avec son rapport `generation-report-en.json`. Les deux langues
partagent la mise en page et les destinations des liens. Les titres et noms de
listes personnalisés sont conservés tels quels, sans traduction automatique.
`--language en --comparison` produit aussi `aipaper-font-comparison-en.pdf`.
Pour changer les autres options sans interface, utiliser un JSON, par exemple :

```json
{
  "days": 200,
  "notes_pages": 2,
  "list_count": 10,
  "tasks_per_list": 40,
  "detail_pages": 2,
  "typography": "manrope",
  "language": "fr",
  "title": "Meetings & actions",
  "list_names": []
}
```

Les paramètres absents prennent leur valeur par défaut. Les limites et les
valeurs sont validées avant génération. `--days`, `--font` et `--language` remplacent leurs
valeurs JSON ; `--all-variants` génère les trois polices.

## Contenu et navigation

- Format AiPaper : **1 920 × 2 560 px à 300 ppp**, soit 162,56 × 216,75 mm.
  [Spécifications Viwoods](https://viwoods.com/products/viwoods-aipaper/).
- 200 Meetings non datés : cinq Objectives, Agenda libre, Notes et deux pages
  de notes supplémentaires. **‹ Jour ›** saute directement au Meeting voisin.
- Sur les pages Notes, **‹ Meeting 003** revient au tableau de bord correspondant.
  **MEETING 003** dans l’en-tête est également cliquable et ouvre ce même Meeting.
  **Notes 2 ›** et **‹ Notes 1** naviguent entre les notes ; **Jour suivant ›**
  ouvre le prochain Meeting. Sur la dernière journée, **Index ›** ramène à son index.
- 10 listes de 40 tâches avec deux pages de contexte chacune.
  En bas de ces notes : **‹ Liste 01** revient à la liste, **Notes 2 ›** et
  **‹ Notes 1** naviguent entre les pages de contexte de la même tâche.
- 1 accueil et 5 index de 40 journées, ordonnées de gauche à droite.
- À droite : les cinq groupes **JOURS**, puis les dix **TODO**. Depuis une tâche,
  groupe de journées → numéro de journée permet le retour en deux clics.
- Le titre **TODO** de la barre et l’en-tête **TODO / LISTE** ouvrent l’accueil.
  Sur le contexte, **LISTE 01 — NOTES 01/02** ramène à la liste correspondante.
- Dans une liste, le champ avant **· 02** permet d’écrire la journée d’origine.
  **001 · 02** désigne la tâche 02 de cette liste, liée à la journée 001.
  L’identifiant de sa fiche, par exemple **03-02**, reste liste 03 / tâche 02.

Les références manuscrites ne deviennent pas des liens. Le PDF ne mémorise pas
la dernière journée consultée et ne synchronise pas les annotations. Régénérer
crée un carnet vierge, sans reprendre les notes écrites sur un précédent PDF.
Le comparatif et les trois pages d’aperçu sont visuels ; les carnets complets
contiennent les liens actifs.

## Tests et fichiers

```bash
venv/bin/python -m pip install -r requirements-local.txt -r requirements-dev.txt
venv/bin/python -m unittest discover -s tests -v
```

`planner_config.py` contient les valeurs par défaut, `planner_pages.py` les
mises en page, `planner_pdf.py` l’assemblage, `generate_planner.py` la commande
et `planner_ui.py` l’interface. Les PDF sont vectoriels ; les grilles de points
réutilisent un seul Form XObject par police.
`planner_i18n.py` regroupe les traductions des textes du PDF.

`requirements-local.txt` décrit l’environnement local validé. Le fichier
historique `requirements.txt` est conservé pour le déploiement existant.
Les scripts Docker/VPS historiques ne sont pas la procédure de lancement de ce
guide. Aucune commande ci-dessus ne déploie le projet.

Git exclut `venv/`, `output/`, `tmp/`, `archives/` et les configurations personnelles.
Les anciennes versions restent dans les archives locales, sans être publiées.
Les deux carnets de démonstration français et anglais sont versionnés dans
`examples/` et téléchargeables depuis le README. Pour les actualiser après une
modification des modèles, régénérer les deux langues, puis copier les PDF :

```bash
venv/bin/python generate_planner.py
venv/bin/python generate_planner.py --language en
cp output/pdf/aipaper-manrope-200j.pdf examples/
cp output/pdf/aipaper-manrope-en-200d.pdf examples/
```
