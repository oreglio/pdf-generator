# Folio — plan d’évolution PDF et application

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Une demande de plan n’autorise pas son exécution, un commit, un push ou un déploiement.

**Goal:** Faire évoluer Folio vers des carnets adaptés à plusieurs tablettes, des périodes jusqu’à un an et des pages facultatives, en préservant exactement les carnets actuels.

**Architecture:** Conserver les moteurs ReportLab et isoler le catalogue d’appareils, la géométrie, la pagination et les préférences de l’application. La configuration validée détermine les pages et leurs destinations avant le dessin ; NiceGUI, Streamlit et les commandes utilisent les mêmes règles.

**Tech Stack:** Python, ReportLab, NiceGUI, Streamlit existant, pywebview pour macOS, pdf2image/Poppler et pypdf pour les contrôles.

**Spec:** La [spécification produit](#spécification-produit) de ce document rassemble les propositions discutées. Les détails marqués « recommandation » sont des choix proposés, pas des fonctionnalités déjà réalisées.

## Contraintes globales

- Conserver le français et l’anglais dans les PDF.
- Conserver les PDF datés et non datés actuels, identiques octet pour octet avec leurs réglages d’origine.
- Le profil Viwoods AiPaper actuel reste le défaut ; aucun nouveau module de page activé par défaut.
- Conserver l’option week-ends, les liens internes, les références backlog/tâche/jour et les noms personnalisés.
- Charger les anciens JSON sans intervention ; les nouveaux champs prennent leurs valeurs par défaut.
- Aucune modification des réglages VPS partagés, du proxy, des ressources, du nombre de workers, des délais ou de la concurrence dans ce chantier.
- Ne pas réécrire le générateur historique. La parité porte sur les deux carnets actuels, exposés dans NiceGUI et dans leur interface Streamlit existante.
- Ne pas remplacer les exemples PDF versionnés pour faire passer un test de régression.
- Préserver les changements locaux non commités de Folio.app, de son icône et de sa documentation avant de commencer.
- Le PDF reste statique : une référence manuscrite ne crée pas automatiquement un nouveau lien, et les tâches ne se synchronisent pas entre les pages.

## Spécification produit

### 1. Support et confort d’écriture

Ajouter une section **Support & format** :

1. Famille : Viwoods, BOOX, iPad, personnalisé.
2. Modèle exact, avec sa génération lorsque les dimensions diffèrent.
3. Confort : Standard ou Aéré.
4. Aperçu et nombre de pages actualisés après application des choix.

Première livraison recommandée : **portrait uniquement**. Le paysage demande des compositions propres et reste une extension distincte.

| Famille | Première sélection proposée | Extension du catalogue |
| --- | --- | --- |
| Viwoods | AiPaper, AiPaper Mini | Nouveaux modèles après vérification |
| BOOX | Go 10.3, Note Air4 C, Note Max | Autres Note Air, Tab et formats compacts |
| iPad | Pro 11″ M4/M5, Pro 13″ M4/M5 | Air et mini avec génération explicite |
| Personnalisé | Largeur et hauteur en mm | Paysage après validation de sa composition |

Les formats reposent sur les **proportions et dimensions utiles**, pas sur un export raster à la résolution de l’écran. Le PDF conserve son texte et ses tracés vectoriels. Les barres d’outils des lecteurs peuvent réduire la surface visible : tester le confort sur tablette en affichage pleine page.

Le mode Aéré augmente l’espace pour écrire. Il peut répartir une liste sur plusieurs pages, mais **ne supprime aucune tâche**. Le nombre total de pages doit rendre ce coût visible avant génération. Le même principe s’applique aux petits écrans.

### 2. Durées plus longues

- Choix rapides : **1, 2, 3, 6 et 12 mois**.
- Conserver la date de départ et la règle actuelle de fin de période.
- Ne pas changer automatiquement le nombre de pages Notes quand la durée augmente.
- Une période de douze mois commençant au milieu d’un mois peut traverser **treize mois calendaires affichés**.
- Pour les périodes longues, remplacer la barre de toutes les semaines par les mois. Les calendriers mensuels donnent accès à leurs semaines et journées.
- Depuis Meeting ou Notes, un lien explicite ramène aux tâches de la semaine ; précédent/suivant saute les week-ends exclus.
- Depuis le backlog : mois → semaine, sans repasser par l’accueil.
- Conserver la navigation actuelle pour les carnets historiques de un à trois mois au profil standard.

En complément, prévoir un mode **dates exactes**, avec date de fin inclusive, limité à 366 jours. Cette option est un lot indépendant, après les durées fixes.

### 3. Pages facultatives

| Page | Contenu | Destination et retour | Priorité proposée |
| --- | --- | --- | --- |
| Priorités du mois | Trois priorités, échéances, espace libre | Depuis le calendrier du mois ; retour au calendrier | Haute |
| Semaine en un coup d’œil | Sept zones de jours, espace de planification | Depuis les tâches de la semaine ; jours cliquables | Moyenne |
| Bilan hebdomadaire | Terminé / À reporter / À retenir | Depuis la semaine ; retour aux tâches, accès à la suivante | Moyenne |
| Meeting simplifié | Notes dominantes, Décisions / Actions | Même navigation que le Meeting actuel | Moyenne |
| Fonds de notes | Ligné / Pointillé / Quadrillé / Blanc | Remplace seulement le fond des pages concernées | Haute |
| Fiche projet | Objectif, prochaines actions, décisions, notes | Index Projets, retour à l’index et au backlog | Seconde étape |

Le calendrier actuel doit conserver sa surface d’écriture. Recommandation : ajouter une page de priorités reliée au calendrier plutôt que comprimer ses cases.

La fiche projet reste indépendante : elle ne crée pas une seconde copie des notes détaillées du backlog. Utiliser des champs de référence libres pour rapprocher les deux.

### 4. Confort dans Folio

- Restaurer la dernière configuration valide au démarrage, pour chaque mode.
- Proposer des profils nommés : par exemple Travail / trimestre, Personnel / mois.
- Conserver import et export JSON comme moyen portable de sauvegarde.
- Sur le web, isoler les préférences par navigateur/utilisateur technique ; aucun dictionnaire global partagé entre visiteurs.
- Ne pas sauvegarder automatiquement les PDF générés côté serveur.
- Afficher le nombre de pages réel avant génération, y compris les pages ajoutées par le confort Aéré et les modules facultatifs.

Les dates sous les semaines sont utiles là où elles restent lisibles. Sur une période longue, les calendriers mensuels portent cette information ; ne pas accumuler deux lignes minuscules dans chaque bouton latéral.

## Ordre de réalisation recommandé

| Lot | Livraison utilisable | Dépendances |
| --- | --- | --- |
| 0 | Références actuelles protégées et choix de périmètre confirmés | Aucune |
| 1 | Six et douze mois avec navigation lisible | Lot 0 |
| 2 | Formats de tablettes, pagination et confort d’écriture | Lot 0 ; vérifier aussi le lot 1 |
| 3 | Sauvegarde automatique et profils de réglages | Schéma de configuration stabilisé |
| 4 | Fonds de notes et priorités mensuelles | Lot 2 |
| 5 | Vue de semaine, bilan et Meeting simplifié | Lots 1 et 2 |
| 6 | Dates exactes et fiches projet | Pagination et navigation stabilisées |

**Premier jalon conseillé : lots 0 à 2**, puis usage réel sur tablette avant de multiplier les pages. Le lot 3 peut être livré séparément. Chaque lot constitue un changement révisable ; aucun gros basculement unique.

## État technique observé

- `PlannerConfig` porte les réglages communs ; `DatedPlannerConfig` limite actuellement la durée à trois mois.
- Les dimensions AiPaper sont globales dans `planner_config.py`, puis importées dans les deux moteurs et les classes de pages.
- Les mises en page utilisent des positions fixes ; changer uniquement `pagesize` ne suffira pas.
- `DatedPlannerPages.rail()` affiche toutes les semaines : l’étendre à un an écraserait les boutons.
- Les assemblages PDF et les propriétés `total_pages` calculent séparément la structure du carnet.
- `nicegui_service.generate_artifact()` suppose actuellement trois pages d’aperçu non datées et cinq datées.
- Les réglages NiceGUI appartiennent à chaque `PlannerWorkspace` ; ils ne sont pas restaurés après fermeture.

## Plan d’implémentation

### Lot 0 — Fixer les références de compatibilité

**Fichiers :** `tests/test_planner.py`, `tests/test_dated_pdf.py`, `tests/test_dated_config.py`, `tests/test_nicegui_service.py` ; exemples existants en lecture seule.

- [ ] Relever le statut Git, conserver les changements Folio.app en cours et démarrer l’évolution sur une branche distincte au moment de l’exécution.
- [ ] Ajouter une comparaison des deux PDF datés publiés, en complément des comparaisons non datées existantes.
- [ ] Vérifier les anciens JSON sans champs d’appareil, de densité ou de modules.
- [ ] Conserver les vérifications de liens et de coordonnées dans les pages.

Test de référence à ajouter :

```python
def test_dated_default_stays_identical_to_published_pdf(self):
    from pathlib import Path
    from planner_config import PlannerConfig
    from dated_planner_config import DatedPlannerConfig
    from dated_planner_pdf import generate_dated_pdf
    import io

    for language in ('fr', 'en'):
        config = DatedPlannerConfig(
            base=PlannerConfig(language=language), start_date='2026-09-16')
        output = io.BytesIO()
        generate_dated_pdf(config, output)
        expected = Path('examples/dated') / config.pdf_filename
        self.assertEqual(output.getvalue(), expected.read_bytes())
```

**Validation :** `venv/bin/python -m unittest discover -s tests`. Cette base doit passer avant toute modification fonctionnelle.

### Lot 1 — Étendre les périodes et la navigation

**Modifier :** `dated_planner_config.py`, `dated_planner_pages.py`, `dated_planner_pdf.py`, `nicegui_app.py`, `dated_planner_ui.py`, `generate_dated_planner.py`.
**Tests :** `tests/test_dated_config.py`, `tests/test_dated_pdf.py`, `tests/test_dated_ui.py`, `tests/test_nicegui_ui.py`.

**Contrat proposé :** `months` accepte les entiers de 1 à 12 ; les interfaces proposent les cinq durées rapides. La variante de navigation longue s’active lorsque `months > 3`.

- [ ] Écrire d’abord les tests de période 6/12 mois, année bissextile, changement d’année et exclusion des week-ends.
- [ ] Vérifier que les tests échouent sur la limite actuelle de trois mois.
- [ ] Étendre la validation, les choix UI et les arguments CLI ; conserver trois mois par défaut.
- [ ] Adapter l’accueil pour jusqu’à treize mois affichés ; réserver l’index complet des semaines aux calendriers.
- [ ] Dessiner une barre de mois pour la variante longue. Sur les pages hebdomadaires, ajouter précédent/suivant de semaine avec des destinations explicites.
- [ ] Ajouter le retour vers la semaine depuis Meeting et Notes, et vérifier les trajets depuis les pages du backlog.
- [ ] Afficher l’année lorsque des libellés seraient ambigus entre deux années.
- [ ] Vérifier tous les liens d’un carnet annuel dans les deux langues ; vérifier le profil historique par comparaison binaire.

Cas concret :

```python
config = DatedPlannerConfig(start_date='2026-09-16', months=12)
assert config.end_date.isoformat() == '2027-09-15'
assert len(config.dates) == 365
assert len(config.calendar_months) == 13
```

**Commande :** `venv/bin/python -m unittest tests.test_dated_config tests.test_dated_pdf tests.test_dated_ui tests.test_nicegui_ui`.
**Livrable :** PDF 6/12 mois générable depuis les deux interfaces et la CLI, sans boutons comprimés ni nouvelle page activée implicitement.

### Lot 2A — Catalogue d’appareils et géométrie

**Créer :** `planner_formats.py`, `planner_layout.py`, `tests/test_planner_formats.py`.
**Modifier :** `planner_config.py`, `planner_pages.py`, `dated_planner_pages.py`, `planner_pdf.py`, `dated_planner_pdf.py`.

Interfaces proposées :

```python
@dataclass(frozen=True)
class DeviceFormat:
    key: str
    brand: str
    label: str
    width_pt: float
    height_pt: float
    source_url: str

def resolve_format(config: PlannerConfig) -> DeviceFormat: ...
def make_layout(config: PlannerConfig) -> PageLayout: ...
```

`PageLayout` porte `width`, `height`, `left`, `right`, `content_width`, `rail_width`, `row_height` et les limites verticales utiles. Chaque instance de pages reçoit son propre layout ; aucune mutation des constantes globales selon le client.

- [ ] Constituer le catalogue avec sources officielles et génération explicite. Convertir en points PDF, et conserver exactement `1920 * 72 / 300` × `2560 * 72 / 300` pour le profil actuel.
- [ ] Ajouter à `PlannerConfig` : `device='viwoods-aipaper'`, `density='standard'`, `custom_width_mm=None`, `custom_height_mm=None`.
- [ ] Pour le format personnalisé, accepter uniquement des nombres finis positifs, dans une plage documentée de 100 à 400 mm par côté ; portrait seulement pour cette livraison.
- [ ] Refuser les identifiants inconnus avec une erreur lisible, sans revenir silencieusement au défaut.
- [ ] Remplacer les dépendances aux dimensions globales par la géométrie d’instance dans les variantes adaptables. Préserver les valeurs et l’ordre des opérations du rendu historique.
- [ ] Adapter aussi les liens : rectangles calculés depuis les mêmes coordonnées que leurs libellés, sans déformation anisotrope.
- [ ] Vérifier le MediaBox, les proportions, l’absence de débordement et l’identité du profil historique.

Exigence de référence :

```python
layout = make_layout(PlannerConfig())
assert layout.width == 1920 * 72 / 300
assert layout.height == 2560 * 72 / 300
```

**Commande :** `venv/bin/python -m unittest tests.test_planner_formats tests.test_planner tests.test_dated_pdf`.

### Lot 2B — Pagination adaptée aux petits formats

**Créer :** `planner_manifest.py`, `tests/test_planner_manifest.py`.
**Modifier :** les deux assembleurs PDF, les classes de pages, les propriétés `total_pages` des configurations et `nicegui_service.py`.

Le manifeste est la liste ordonnée des pages à produire. Il devient la source du nombre de pages et des destinations ; le calcul n’est plus dupliqué entre interface et génération.

```python
@dataclass(frozen=True)
class PageSpec:
    key: str
    kind: str
    reference: str
    part: int = 1
    first_item: int = 0
    last_item: int = 0

def build_manifest(config: PlannerConfig | DatedPlannerConfig) -> tuple[PageSpec, ...]: ...
```

Le module de manifeste ne consulte pas `config.total_pages`, afin d’éviter une récursion. Les imports des configurations nécessaires uniquement aux annotations utilisent `TYPE_CHECKING`.

- [ ] Écrire les tests de répartition de 40 tâches sur un petit écran et en mode Aéré : aucune ligne perdue ou dupliquée, numéros conservés.
- [ ] Calculer le nombre de lignes disponible depuis la zone utile et l’espacement. Ne jamais réduire le texte à une taille illisible pour tout faire tenir.
- [ ] Préserver `list-1` comme destination de la première page d’une liste ; nommer les suivantes `list-1-page-2`, etc.
- [ ] Les notes d’une tâche retournent à la page exacte contenant sa ligne. Les onglets de liste ouvrent la première page.
- [ ] Une liste hebdomadaire répartie sur plusieurs feuilles garde sa semaine et son nombre de tâches ; afficher page x/y sans ajouter une liste logique.
- [ ] Conserver sur les tâches hebdomadaires le principe actuel : références à gauche, espace libre à droite, longueurs d’écriture équilibrées.
- [ ] Adapter index de journées, accueil et calendriers à la place disponible, y compris les mois à six rangées.
- [ ] Faire dériver les aperçus du manifeste : ne plus supposer que leur nombre reste toujours trois ou cinq si un exemple exige plusieurs feuilles.
- [ ] Conserver les destinations historiques et les métadonnées exactes lorsque toutes les options sont celles d’origine.

**Tests :** `len(build_manifest(config)) == config.total_pages`, clés uniques, toutes les références résolues, rectangles inclus dans leur MediaBox.
**Commande :** `venv/bin/python -m unittest tests.test_planner_manifest tests.test_planner tests.test_dated_pdf tests.test_nicegui_service`.

### Lot 2C — Réglages, aperçu et export des formats

**Modifier :** `nicegui_app.py`, `nicegui_service.py`, `planner_ui.py`, `dated_planner_ui.py`, `generate_planner.py`, `generate_dated_planner.py`.
**Tests :** `tests/test_nicegui_ui.py`, `tests/test_nicegui_service.py`, `tests/test_planner_ui.py`, `tests/test_dated_ui.py`.

- [ ] Ajouter Famille → Modèle et Confort, avec le modèle AiPaper standard sélectionné au premier lancement.
- [ ] Faire dépendre la famille du modèle stocké ; ne pas sauvegarder deux champs contradictoires.
- [ ] Afficher les champs mm seulement pour Personnalisé.
- [ ] Mettre à jour l’aperçu, ses onglets et les métriques depuis la configuration appliquée ; invalider un ancien téléchargement après changement.
- [ ] Conserver ces choix dans les JSON et les profils ; proposer `--device` et `--density` en CLI.
- [ ] Ajouter un suffixe de format aux nouveaux exports pour éviter les confusions, sans changer les noms des exports historiques.
- [ ] Vérifier l’indépendance de deux clients simultanés utilisant deux appareils différents.

**Recette :** AiPaper historique, petit Viwoods Mini, grand Note Max et iPad Pro 11″ au ratio différent ; daté/non daté, FR/EN, Standard/Aéré.

### Lot 3 — Restaurer les réglages et créer des profils

**Créer :** `nicegui_preferences.py`, `tests/test_nicegui_preferences.py`.
**Modifier :** `nicegui_app.py`, `NICEGUI.md` et `DEPLOY_COOLIFY.md` pour préciser ce qui est désormais conservé.

Stockage proposé : `app.storage.user`, sous une seule clé `folio_preferences`, avec un schéma versionné. Ce stockage identifie un navigateur, pas un compte authentifié.

```python
{
    'version': 1,
    'active_mode': 'dated',
    'last_valid': {'dated': {}, 'undated': {}},
    'profiles': [{'id': 'uuid', 'name': 'Travail', 'mode': 'dated', 'config': {}}],
}
```

Les objets de configuration du schéma ci-dessus contiennent les exports complets des configurations validées, pas des objets vides en production.

- [ ] Sauvegarder après application réussie, import valide ou génération ; ne pas persister un champ provisoirement invalide pendant la saisie.
- [ ] Au lancement, valider les données sauvegardées ; en cas de corruption, utiliser les défauts avec un message et garder l’import JSON disponible.
- [ ] Ajouter Enregistrer un profil, Charger, Renommer et Supprimer. Identifier les profils par UUID, jamais par un chemin dérivé du nom.
- [ ] Limiter le nom à 48 caractères et demander confirmation uniquement pour remplacer ou supprimer un profil existant.
- [ ] Tester la restauration, la séparation des deux modes, les deux utilisateurs et les anciens JSON.
- [ ] Vérifier un redémarrage de Folio.app et un redémarrage Docker avec le volume existant, sans modifier les paramètres d’hébergement.

**Commande :** `venv/bin/python -m unittest tests.test_nicegui_preferences tests.test_nicegui_ui`.

### Lot 4 — Fonds de notes et priorités du mois

**Créer :** `planner_note_styles.py`, `tests/test_planner_note_styles.py`.
**Modifier :** les configurations, `planner_manifest.py`, les classes de pages, `planner_i18n.py`, les réglages UI et CLI.

```python
def draw_note_background(canvas, bounds: tuple[float, float, float, float],
                         style: str, spacing: float) -> None: ...
```

- [ ] Ajouter `meeting_note_style='lined'` et `task_note_style='dots'` ; garder les rendus actuels comme défauts.
- [ ] Dessiner uniquement dans la zone d’écriture, jamais sous un titre, un lien ou la barre latérale.
- [ ] Proposer `lined`, `dots`, `grid`, `blank` avec les mêmes réglages dans les deux langues.
- [ ] Ajouter `monthly_priorities=False` au carnet daté. Quand activé : une page par mois affiché, placée après son calendrier.
- [ ] Prévoir les ancres `month-plan-YYYY-MM`, retour calendrier et accès à ses semaines. Pour un mois partiel, afficher la période réellement couverte.
- [ ] Vérifier le nombre de pages supplémentaire, les retours, les noms de mois FR/EN et le rendu sur petit/grand écran.

**Validation visuelle :** rendre une page de chaque fond et une priorité mensuelle avec Poppler ; vérifier le contraste des quadrillages sur e-ink, pas seulement sur écran LCD.

### Lot 5 — Pages hebdomadaires et variante Meeting

**Modifier :** `dated_planner_config.py`, `planner_config.py`, `planner_manifest.py`, `dated_planner_pages.py`, `planner_pages.py`, `planner_i18n.py`, les interfaces et leurs tests.

- [ ] Ajouter `weekly_overview=False`, `weekly_review=False` et `meeting_layout='classic'` ; proposer `meeting_layout='notes_actions'` comme alternative.
- [ ] Pour la vue semaine, créer une page par semaine couverte ; les jours hors période restent visibles et inactifs.
- [ ] Si les week-ends sont exclus, leurs zones restent visibles mais n’ouvrent pas de Meeting inexistant.
- [ ] Pour le bilan, utiliser Terminé / À reporter / À retenir, avec liens vers tâches de la semaine et semaine suivante.
- [ ] Réutiliser les mêmes destinations Meeting dans la variante simplifiée : seule sa composition change.
- [ ] Ajouter ces pages au manifeste et aux aperçus sélectionnables, sans remplacer les tâches hebdomadaires existantes.
- [ ] Vérifier séparément chaque option puis leur combinaison ; conserver les pages classiques par défaut.

**Ancres proposées :** `week-overview-YYYY-MM-DD` et `week-review-YYYY-MM-DD`, avec la date du lundi ISO comme identifiant stable.

### Lot 6 — Dates exactes et projets

Ces deux éléments sont indépendants et se livrent dans deux changements distincts.

**Dates exactes — fichiers :** `dated_planner_config.py`, les deux interfaces datées, `generate_dated_planner.py`, `tests/test_dated_config.py`, `tests/test_dated_ui.py`.

- [ ] Ajouter `end_date_override: str | None = None` ; ne pas entrer en conflit avec la propriété existante `end_date`.
- [ ] Sans valeur explicite, conserver le calcul par mois. Avec une valeur, utiliser une fin inclusive et ignorer le nombre de mois dans le calcul.
- [ ] Refuser une fin antérieure au début ou une période supérieure à 366 jours.
- [ ] Refuser une période sans journée générable, par exemple uniquement un week-end avec week-ends exclus, avec un message permettant de corriger les dates.
- [ ] Sélectionner la navigation longue selon la période effective, et non plus seulement `months > 3`.
- [ ] Tester même jour, fin de mois, année bissextile et import d’une ancienne configuration.

**Projets — fichiers :** configurations, `planner_manifest.py`, nouveau `planner_project_pages.py`, `planner_i18n.py`, interfaces et nouveau `tests/test_planner_projects.py`.

- [ ] Ajouter `project_count=0`, noms facultatifs et un nombre explicite de pages de notes par projet.
- [ ] Lorsque le nombre est positif, ajouter un index Projets puis les fiches ; sinon ne produire aucune page ni lien de projet.
- [ ] Créer `projects`, `project-N` et `project-N-notes-P` ; conserver des retours explicites vers l’index et le backlog.
- [ ] Donner une place fixe aux références manuscrites du backlog, sans prétendre créer des liens depuis le texte écrit.
- [ ] Vérifier les pages supplémentaires et les combinaisons avec les carnets datés/non datés.

## Recette finale et livraison

- [ ] Suite complète : `venv/bin/python -m unittest discover -s tests`.
- [ ] Comparaison binaire des quatre PDF de référence actuels.
- [ ] Audit pypdf des destinations, pages, rectangles cliquables et tailles de page de chaque profil livré.
- [ ] Rendus Poppler : accueil, mois à six rangées, semaine, Meeting, Notes, backlog et contexte sur les quatre formats représentatifs.
- [ ] Essai manuel sur les tablettes disponibles : écriture au stylet et précision tactile. Marquer les autres profils « format vérifié, usage sur appareil non testé » dans la documentation de validation.
- [ ] Mesurer durée de génération, taille du PDF et mémoire pour un carnet annuel représentatif ; ne pas promettre la même fluidité dans tous les lecteurs.
- [ ] Vérifier aperçu, génération, import/export et préférences dans le navigateur et dans Folio.app.
- [ ] Actualiser les COPY du Dockerfile uniquement pour les nouveaux modules nécessaires, puis reconstruire l’image et contrôler son démarrage et Poppler.
- [ ] Mettre à jour `README.md`, `PLANNER.md`, `NICEGUI.md`, `DEPLOY_COOLIFY.md` et ajouter des exemples clairement séparés des fichiers historiques.
- [ ] Préparer des commits par lot ; commit/push seulement sur demande. Déploiement VPS séparé de l’implémentation.

## Décisions à confirmer avant exécution

1. **Premier périmètre recommandé :** durées 6/12 mois et formats portrait, puis profils de réglages.
2. **Premières pages nouvelles recommandées :** fonds de notes et priorités du mois ; les autres restent des options de seconde livraison.
3. **Catalogue initial recommandé :** les modèles explicitement listés, avec Air/mini et autres BOOX ajoutés après vérification de leurs dimensions exactes.
4. **Mode Aéré recommandé :** davantage de pages si nécessaire, plutôt que moins de tâches ou du texte plus petit.

## Sources pour le catalogue

- [Apple — dimensions et résolutions par modèle](https://developer.apple.com/design/human-interface-guidelines/layout).
- [BOOX — spécifications des appareils](https://help.boox.com/hc/en-us/articles/360027768131-What-are-the-specifications-of-BOOX-devices).
- [Viwoods — tablettes AiPaper et AiPaper Mini](https://viwoods.com/collections/tablet).

Revalider les fiches officielles au moment d’ajouter un modèle. Le nom commercial, la taille diagonale et la génération ne sont pas interchangeables.
