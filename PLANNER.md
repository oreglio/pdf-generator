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

## Support, confort et pages facultatives

Ces réglages valent pour les deux modes. Ils sont tous facultatifs : sans eux,
le carnet est exactement celui décrit plus bas.

### Format de la tablette

| Famille | Modèles | Surface utile |
| --- | --- | --- |
| Viwoods | AiPaper 10,65″, AiPaper Mini 8,2″ | 163 × 217 mm, 125 × 167 mm |
| BOOX | Go 10.3, Note Air4 C, Note Max 13,3″ | 157 × 210 mm, 157 × 210 mm, 203 × 271 mm |
| iPad | Pro 11″ (M4/M5), Pro 13″ (M4/M5) | 160 × 233 mm, 199 × 265 mm |
| Personnalisé | Largeur et hauteur en mm | 100 à 400 mm de large, 150 à 400 mm de haut |

Les dimensions viennent des fiches officielles
([Viwoods](https://viwoods.com/pages/compare-aipapermini),
[BOOX](https://shop.boox.com/products/notemax),
[Apple](https://support.apple.com/en-us/119891)) et sont converties en points
PDF avec la densité du panneau. Ce sont des **proportions et des surfaces
utiles**, pas un export raster : le PDF garde son texte et ses tracés
vectoriels. Les barres d’outils des lecteurs réduisent la surface visible :
tester en affichage pleine page. Le format personnalisé est portrait
uniquement ; la hauteur minimale de 150 mm est celle qui permet encore de
dessiner les blocs d’un Meeting au-dessus de la zone d’écriture.

Marges, barre latérale et pied de page gardent leur taille physique sur tous
les appareils ; seule la colonne d’écriture suit la page. Aucune déformation
anisotrope n’est appliquée.

```bash
venv/bin/python generate_planner.py --device boox-note-max
venv/bin/python generate_planner.py --device custom --custom-width-mm 150 --custom-height-mm 210
```

### Confort d’écriture et répartition sur plusieurs feuillets

`--density standard` (défaut) ou `--density comfortable`. Le mode aéré écarte
les lignes. Quand une liste ne tient plus, elle est **répartie sur plusieurs
feuillets équilibrés** plutôt que tronquée :

| Profil | Tâches par feuillet | 40 tâches |
| --- | --- | --- |
| AiPaper standard | 40 | 1 feuillet |
| AiPaper aéré | 32 | 2 feuillets de 20 |
| AiPaper Mini standard | 26 | 2 feuillets de 20 |
| Note Max standard | 52 | 1 feuillet |

Aucune ligne n’est perdue ni dupliquée et les numéros restent continus.
La première feuille garde la destination historique `list-1` ; les suivantes
deviennent `list-1-page-2`. Les onglets de liste ouvrent toujours la première
feuille ; les notes d’une tâche reviennent à la feuille portant sa ligne.

### Fonds d’écriture

`--meeting-note-style` et `--task-note-style` acceptent `lined`, `dots`, `grid`
et `blank`. Les défauts — `lined` pour les pages Notes, `dots` pour les pages de
contexte — reproduisent exactement le rendu historique. Le fond ne couvre que la
zone d’écriture : jamais un titre, un lien ni la barre latérale.

### Composition des Meetings

`--meeting-layout classic` (défaut) garde Objectives / Agenda / Notes.
`--meeting-layout notes_actions` donne des notes dominantes puis
**Décisions / Actions**, avec exactement les mêmes destinations.
Avec `both`, les pages Notes passeraient derrière la page Décisions : le
pied de page du Meeting reçoit donc un raccourci **Notes ›**, à côté de
**Décisions ›**. `--meeting-layout both` produit les **deux pages pour le même
Meeting** :
la page classique pour préparer, puis une page **Décisions & actions** pour
la clore, avant les pages Notes. La journée reste ouverte par `day-N` depuis
le calendrier, la semaine et l'index ; la seconde page porte l'ancre
`day-N-actions` et revient à la première.

### Fiches projet

`--project-count` (0 à 12, zéro par défaut) et `--project-notes-pages` (0 à 10).
À zéro, aucune page ni aucun lien de projet n’est produit. Sinon, un index
**Projets** puis une fiche par projet : objectif, cinq prochaines actions avec
une place fixe pour une référence backlog manuscrite, décisions et notes, puis
ses pages de notes. Ancres `projects`, `project-N` et `project-N-notes-P`.
Une fiche ne recopie pas les notes détaillées du backlog. Une barre horizontale de
pastilles **NOTES**, sur la ligne de l'œil-de-perdrix en haut à droite, ouvre
chaque page de notes du projet, depuis la fiche comme depuis n'importe
laquelle de ses notes ; la page ouverte y est marquée.

Quand les projets sont activés, la barre latérale gagne une section
**PROJETS** dont chaque pastille ouvre directement sa fiche, depuis
n'importe quelle page — Meeting compris. Si la colonne ne peut plus porter
ces pastilles, seul le libellé reste et il ouvre l'index. Les pages Meeting
reçoivent en contrepartie un champ **PROJET** sous leur titre, pour écrire à
la main le projet concerné : cette référence reste une annotation, elle ne
devient jamais un lien.

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

## Variante datée

Dans la barre latérale, choisir **Viwoods daté**. Le mode **Viwoods AiPaper**
reste le carnet non daté habituel, sélectionné par défaut. Les réglages,
téléchargements et aperçus des deux modes sont indépendants.

Choisir une **date de début**, une durée de **1, 2, 3, 6 ou 12 mois** — ou une
date de fin exacte — puis une à trois pages d’actions par semaine (jusqu’à 40
actions par page). Cliquer sur
**Appliquer et actualiser l’aperçu**, puis **Générer mon carnet daté**.
Les jours incluent les week-ends. La période va du début inclus à la veille de
la même date N mois plus tard : du 16 septembre au 15 décembre pour trois mois.
Si cette date n’existe pas dans le mois d’arrivée, elle est ramenée au dernier
jour du mois avant de retirer un jour (31 janvier → 27 février hors année bissextile).
La période exacte est affichée avant génération.

- Le calendrier mensuel ouvre chaque Meeting par sa date ; les numéros de
  semaine ouvrent les listes hebdomadaires. Les jours hors période sont grisés
  et ne possèdent aucun lien.
- Chaque semaine dispose de liens vers les Meetings de ses sept jours inclus.
  Les actions hebdomadaires n’ont pas de sous-pages de notes.
- Le backlog reprend les listes et contextes permanents du carnet non daté.
  Les onglets **Wxx** de chaque page ouvrent directement la semaine choisie.
- Les semaines suivent ISO 8601 (lundi–dimanche). L’année ISO figure dans leur
  en-tête ; par exemple, le 1er janvier 2027 appartient à **W53 / 2026**.
- À gauche, chaque action hebdomadaire suit **BKLG | # | Jour · Tâche** : le numéro de
  liste **02**, celui de la tâche **12**, le jour du mois **16**, puis le texte
  de l’action. Les trois champs courts ont la même largeur.
- À droite, les tâches simples disposent de toute la largeur de la colonne.
  Une référence comme **02-12** peut être ajoutée à la main si nécessaire.
  Le champ libre d’une tâche du backlog peut recevoir **W38**. Les références
  manuscrites ne créent pas de liens et aucun retour dynamique n’est simulé.
- Reporter une action signifie recopier son texte et sa référence vers une
  autre semaine. Les notes détaillées restent dans le backlog. La génération
  produit un carnet vierge et ne récupère pas les annotations d’un ancien PDF.

### Périodes longues et dates exactes

`--months` accepte les entiers de 1 à 12 ; les interfaces proposent les cinq
durées rapides 1, 2, 3, 6 et 12. Une période de douze mois commençant au milieu
d’un mois traverse **treize mois calendaires affichés**.

Au-delà de trois mois, la navigation change : la barre latérale indexe les
**mois** au lieu de toutes les semaines, l’accueil affiche une grille de mois
plutôt que l’index complet des semaines, les pages hebdomadaires gagnent un pas
**‹ W37  W39 ›** et les pages Notes une pastille vers les tâches de leur
semaine. L’année apparaît sous chaque onglet de mois dès que la période
traverse deux années. Les carnets d’un à trois mois conservent exactement la
navigation d’origine.

`--end-date AAAA-MM-JJ` fixe une fin **inclusive** et remplace alors le calcul
par mois. La période est limitée à 366 jours. Sont refusées, avec un message
permettant de corriger : une fin antérieure au début, une date illisible et une
période ne contenant aucune journée générable — par exemple un week-end seul
avec les week-ends exclus. Le choix de la navigation longue suit la période
effective, pas le seul nombre de mois.

### Pages hebdomadaires et mensuelles facultatives

| Option | Effet | Ancre |
| --- | --- | --- |
| `--monthly-priorities` | Une page Priorités après chaque calendrier | `month-plan-AAAA-MM` |
| `--weekly-overview` | Une vue « sept jours » avant les tâches de la semaine | `week-overview-AAAA-MM-JJ` |
| `--weekly-review` | Un bilan Terminé / À reporter / À retenir après les tâches | `week-review-AAAA-MM-JJ` |

Les trois pages d'une même semaine — **Sept jours**, **Semaine** et
**Bilan** — portent chacune les trois onglets, la page ouverte marquée : on
passe de l'une à l'autre sans repasser par les tâches. Les ancres
hebdomadaires portent la date du lundi ISO. Sur la vue « sept
jours », les jours hors période et les week-ends exclus restent visibles mais
n’ouvrent aucun Meeting inexistant. Une page Priorités d’un mois partiel affiche
la période réellement couverte, par exemple **16.09 — 30.09.2026**.

Commandes indépendantes du générateur non daté :

```bash
venv/bin/python generate_dated_planner.py --start-date 2026-09-16 --months 1
venv/bin/python generate_dated_planner.py --start-date 2026-09-16 --months 3 --language en
venv/bin/python generate_dated_planner.py --start-date 2026-09-16 --months 3 --week-pages 2 --weekly-tasks 40
venv/bin/python generate_dated_planner.py --config chemin/reglages-dates.json

# Une année sur un grand écran, avec les priorités mensuelles
venv/bin/python generate_dated_planner.py --start-date 2026-09-16 --months 12 \
    --device boox-note-max --monthly-priorities

# Dates exactes, fin incluse, avec la vue hebdomadaire et son bilan
venv/bin/python generate_dated_planner.py --start-date 2026-09-16 --end-date 2026-12-31 \
    --weekly-overview --weekly-review --meeting-layout notes_actions
```

Sans `--start-date`, la date du jour est utilisée. Les PDF et rapports sont dans
`output/pdf/dated/`, avec langue, date de début et date de fin dans le nom.
Les autres réglages utilisent la configuration JSON exportée par ce mode :

```json
{
  "start_date": "2026-09-16",
  "months": 3,
  "week_pages": 1,
  "weekly_tasks": 40,
  "base": {
    "language": "fr",
    "typography": "manrope",
    "list_count": 10,
    "tasks_per_list": 40,
    "detail_pages": 2,
    "notes_pages": 2
  }
}
```

`base.days` est ignoré dans ce mode : le nombre de jours vient des dates.
Les anciens JSON non datés restent destinés au mode non daté.
Les cinq pages d’aperçu (calendrier, semaine, Meeting, backlog, contexte) sont
visuelles ; les liens sont actifs dans le carnet complet.
Les exemples datés publiés sont dans `examples/dated/` et se régénèrent avec
`--start-date 2026-09-16 --months 3`, puis `--language en` pour l’anglais.

## Tests et fichiers

```bash
venv/bin/python -m pip install -r requirements-local.txt -r requirements-dev.txt
venv/bin/python -m unittest discover -s tests -v
```

`planner_config.py` contient les valeurs par défaut, `planner_pages.py` les
mises en page, `planner_pdf.py` l’assemblage, `generate_planner.py` la commande
et `planner_ui.py` l’interface.
`planner_formats.py` publie le catalogue d’appareils, `planner_layout.py` la
géométrie d’une instance de pages, `planner_manifest.py` la liste ordonnée des
pages d’un carnet — source unique du nombre de pages et des destinations —,
`planner_note_styles.py` les fonds d’écriture et `planner_project_pages.py` les
fiches projet. Les PDF sont vectoriels ; les grilles de points
réutilisent un seul Form XObject par police.
`planner_i18n.py` regroupe les traductions des textes du PDF.
La variante datée possède ses propres modules `dated_planner_config.py`,
`dated_planner_pages.py`, `dated_planner_pdf.py`, `dated_planner_ui.py` et sa
commande `generate_dated_planner.py`. Elle réutilise les primitives graphiques
et les fiches du backlog sans modifier le générateur non daté.

`requirements-local.txt` décrit l’environnement local validé. Le fichier
historique `requirements.txt` est conservé pour le déploiement existant.
Les scripts Docker/VPS historiques ne sont pas la procédure de lancement de ce
guide. Aucune commande ci-dessus ne déploie le projet.

Git exclut `venv/`, `output/`, `tmp/`, `archives/` et les configurations personnelles.
Les anciennes versions restent dans les archives locales, sans être publiées.
Les deux carnets de démonstration français et anglais sont versionnés dans
`examples/` et téléchargeables depuis le README. Les exemples des évolutions —
année complète, petit écran, toutes les options, grand écran aéré — sont dans
`examples/evolution/`, séparés des fichiers historiques. Pour les actualiser après une
modification des modèles, régénérer les deux langues, puis copier les PDF :

```bash
venv/bin/python generate_planner.py
venv/bin/python generate_planner.py --language en
cp output/pdf/aipaper-manrope-200j.pdf examples/
cp output/pdf/aipaper-manrope-en-200d.pdf examples/
```

## Centrage des onglets

Depuis le 17 septembre 2026, le texte des pastilles est centré sur la
**hauteur de capitale** de la police et non sur son cadratin : il était
auparavant 0,5 à 1 pt trop haut dans son onglet. Ce réglage touche toutes
les pastilles de toutes les pages, donc les quatre carnets publiés ont été
régénérés à cette occasion. Les comparaisons octet pour octet des tests
protègent désormais cette nouvelle référence.

## Repères de performance

Mesures sur un Mac Apple Silicon, carnet daté annuel du 16 septembre 2026 au
15 septembre 2027, backlog complet de 10 × 40 tâches :

| Carnet | Pages | Durée | Taille | Pic mémoire |
| --- | --- | --- | --- | --- |
| Annuel, réglages standard | 1 972 | 10,8 s | 17,8 Mo | 213 Mo |
| Annuel, toutes les options | 2 161 | 12,1 s | 19,8 Mo | 282 Mo |

Ces chiffres décrivent la génération, pas la fluidité de lecture : un carnet de
deux mille pages ne s’ouvre pas à la même vitesse dans tous les lecteurs PDF.
Sur un serveur partagé, prévoir cette durée et cette mémoire par génération.

## Ce qui est vérifié, et ce qui ne l’est pas

- **Vérifié automatiquement :** régénération des quatre carnets de référence,
  identique octet pour octet ; audit pypdf de 37 profils livrés — nombre de
  pages, clés uniques, destinations résolues, rectangles cliquables contenus
  dans leur page et taille de page conforme à l’appareil.
- **Vérifié visuellement :** rendus Poppler de l’accueil, d’un mois à six
  rangées, des semaines, des Meetings, des pages Notes, du backlog, des
  contextes et de toutes les pages facultatives, sur quatre formats
  représentatifs.
- **Non testé :** l’écriture au stylet et la précision tactile sur les
  tablettes autres que le Viwoods AiPaper. Ces profils sont **« format vérifié,
  usage sur appareil non testé »**.
