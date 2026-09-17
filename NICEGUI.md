# Interface NiceGUI : navigateur, bureau et serveur

Ce prototype ajoute une interface NiceGUI aux générateurs de carnets Viwoods
datés et non datés. Les PDF restent produits par ReportLab. Il utilise
ses propres dépendances et fichiers Docker ; l'interface Streamlit existante
reste disponible avec ses commandes habituelles.

Dans l'interface, choisir **Carnet daté** ou **Carnet libre**.
La colonne de réglages suit cinq sections : **01 / Support & format**,
**02 / Votre rythme**, **03 / Backlog & contexte**, **04 / Style & langue** et
**05 / Projets**, puis les titres, les profils et l'import/export.
Pour les carnets Viwoods, modifier les réglages, actualiser l'aperçu puis générer
et télécharger le carnet complet. Les réglages s'exportent en JSON pour être
réimportés plus tard. L'aperçu image vérifie la mise en page ; les liens internes
s'utilisent dans le PDF complet. L'essai de trois journées du carnet libre garde
toutes les listes et leurs pages de contexte.

## Fonctions reprises et différences

| Fonction | Interface NiceGUI | Vérification ou limite |
| --- | --- | --- |
| Viwoods daté et non daté | Réglages complets, FR/EN, typographies, noms des listes, aperçus et PDF complets | Comparaisons des PDF avec les moteurs existants ; carnet daté de 1 102 pages identique à l'exemple publié |
| Essai du carnet libre | Trois journées, avec toutes les listes et leurs pages de contexte | Contrôle du nombre de pages et des réglages conservés |
| JSON Viwoods | Import, export, validation et conservation du dernier document en cas d'import invalide | Parcours navigateur vérifiés, dont un carnet anglais Atkinson de huit pages |
| Bureau | Même interface dans une fenêtre pywebview | Ouverture macOS et apparition du dialogue d'enregistrement vérifiées ; confirmation du dialogue et écriture finale non validées |
| Support & format | Famille → Modèle, confort d'écriture, format personnalisé en millimètres | Deux clients simultanés dessinant deux appareils différents, et 37 profils audités avec pypdf |
| Réglages conservés | Derniers réglages valides par mode et profils nommés, dans le navigateur | Restauration après rechargement de page et après redémarrage Docker avec le volume existant |

Les aperçus Viwoods contiennent des pages d'exemple sans navigation active. Les
PDF complets conservent leurs liens internes. Les styles de l'interface et les
polices sont servis localement ; le contrôle navigateur n'a relevé aucune
ressource externe.

## Réglages conservés et profils

Folio enregistre dans le navigateur, sous une seule clé versionnée
`folio_preferences` de `app.storage.user` :

- les **derniers réglages valides** de chaque mode, écrits après une
  application réussie, un import valide ou une génération — jamais pendant la
  saisie, jamais un brouillon invalide ;
- jusqu'à **vingt profils nommés**, identifiés par UUID et non par un chemin
  dérivé de leur nom, avec Enregistrer, Charger, Renommer et Supprimer.

Une confirmation n'est demandée que pour **remplacer** un profil portant déjà ce
nom ou pour en **supprimer** un. Les noms sont limités à 48 caractères.

Ce stockage identifie un navigateur, pas un compte authentifié : deux visiteurs
ne partagent aucun dictionnaire. Des données corrompues ou d'une autre version
sont ignorées, Folio repart de ses valeurs par défaut avec un message, et
l'import JSON reste disponible. **Aucun PDF généré n'est conservé côté serveur.**

L'export JSON reste le moyen portable de sauvegarde : il traverse les
navigateurs et les machines, contrairement à ce stockage local.

## Installation locale

Dans le carnet daté, **Inclure les week-ends** est coché par défaut. Le décocher
supprime uniquement les pages Meeting et Notes du samedi et du dimanche. Le
calendrier reste complet, avec ces dates visibles mais sans lien vers une journée.
Les flèches de navigation passent du vendredi au lundi. Les semaines et le backlog
gardent le même contenu : aucune page supprimée n’est réaffectée ailleurs.
Le choix est conservé dans le JSON (`include_weekends: false`). Les fichiers
produits sans week-ends portent le suffixe `-weekdays.pdf`.

Sans interface :

```bash
python generate_dated_planner.py --start-date 2026-09-16 --months 3 --no-include-weekends
```

Depuis ce répertoire, utiliser Python 3.12 (Python 3.10 minimum pour NiceGUI) :

```bash
python3 -m venv .venv-nicegui
source .venv-nicegui/bin/activate
python -m pip install -r requirements-nicegui.txt
```

Sous Windows, activer avec `.venv-nicegui\Scripts\activate`.

Les aperçus nécessitent **Poppler**, en plus du paquet Python `pdf2image` :

```bash
# macOS
brew install poppler

# Debian / Ubuntu
sudo apt-get update
sudo apt-get install poppler-utils
```

Sous Windows, installer Poppler et ajouter son répertoire `bin` au `PATH`.
`pdftoppm -v` permet de vérifier l'installation. Les polices embarquées dans
`assets/fonts/` sont utilisées pour les PDF, sans installation système.

### Dans le navigateur local

```bash
python nicegui_app.py
# Ou choisir explicitement l'adresse et le port :
python nicegui_app.py --host 127.0.0.1 --port 8080
```

Ouvrir <http://127.0.0.1:8080>. Garder le terminal ouvert pendant l'utilisation ;
`Ctrl+C` arrête l'application. Ce mode écoute sur la machine locale par défaut.

### Dans une fenêtre de bureau

Sur macOS, un lanceur **Folio.app** permet d’ouvrir la fenêtre par double-clic,
sans Terminal. Après installation des dépendances natives, le créer avec le Python
de votre environnement :

```bash
venv/bin/python build_macos_app.py --output "$HOME/Applications/Folio.app"
open "$HOME/Applications/Folio.app"
```

Glisser **Folio.app depuis le Finder vers le Dock** pour garder un raccourci.
Le lanceur choisit un port local disponible et utilise l’icône de carnet fournie
dans `assets/app/folio.png`. Fermer la fenêtre arrête son serveur local.
Les logs se trouvent dans `~/Library/Logs/Folio/app.log`.

Ce lanceur utilise le dossier du projet et le Python qui l’a construit : conserver
les deux à leur emplacement. Il peut être déplacé dans Applications, mais n’est
pas un paquet autonome à envoyer à un autre Mac. Si le projet ou l’environnement
Python change de place, déplacer l’ancien lanceur puis en reconstruire un.
La commande refuse d’écraser une application existante.

Pour lancer directement depuis le Terminal :

```bash
python -m pip install -r requirements-native.txt
python nicegui_app.py --native
```

Ce mode utilise `pywebview`, fixé à la version 6.2.1, et le moteur web du système.
Son profil navigateur est conservé dans `.nicegui/webview`. Exportez les réglages
en JSON pour les conserver ; les carnets générés restent en mémoire jusqu’au téléchargement.
Sur Windows, WebView2 Runtime doit être disponible. Sur Linux, choisir également
un moteur graphique, par exemple :

```bash
python -m pip install 'pywebview[qt]==6.2.1'
```

Une session graphique est nécessaire ; ce mode n'est pas destiné à un serveur
sans écran. Voir les [prérequis pywebview par plateforme](https://pywebview.flowrl.com/guide/installation.html).
Le lanceur macOS reste lié à l’installation Python locale ; il n’y a pas encore
d’installateur autonome macOS ou Windows, ni de signature de distribution.

Pour les carnets Viwoods, les boutons de téléchargement des PDF ouvrent directement
le dialogue système d'enregistrement puis écrivent le fichier choisi. Le PDF ne
remplace pas l'interface ; annuler laisse les réglages et l'aperçu en place.
Les tests couvrent l'enregistrement des octets, l'annulation et les erreurs
d'écriture avec une sélection de fichier simulée. Le téléchargement dans le
navigateur conserve son fonctionnement habituel.

### Mode web

```bash
python nicegui_app.py --web --port 8080
```

`--web` écoute sur `0.0.0.0` pour accepter les connexions réseau. Le mode bureau
est désactivé et le rechargement automatique du code est désactivé au lancement.
Cette commande n'installe ni certificat TLS ni authentification.

## Docker et VPS

**[Guide complet Coolify avec domaine et HTTPS → DEPLOY_COOLIFY.md](DEPLOY_COOLIFY.md)**

Le fichier dédié utilise Python 3.12, installe Poppler et exécute l'application
avec un utilisateur sans privilèges. Depuis ce répertoire :

```bash
export NICEGUI_STORAGE_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
docker compose -f compose.nicegui.yml config --quiet
docker compose -f compose.nicegui.yml up -d --build
docker compose -f compose.nicegui.yml logs -f nicegui
```

Conserver la même valeur de `NICEGUI_STORAGE_SECRET` lors des redémarrages, dans
l'environnement de déploiement. Ce secret signe l'identité des sessions du
navigateur. S'il n'est pas fourni, l'application crée une clé locale persistante
dans `.nicegui/storage-secret` ; ce répertoire est monté dans un volume Docker.
Changer ou perdre la clé peut rendre les anciennes sessions inaccessibles.

Le port est publié uniquement sur **127.0.0.1:8080** de l'hôte. Pour un VPS,
faire pointer le reverse proxy existant vers cette adresse, en conservant la
transmission HTTP et les connexions **WebSocket / Socket.IO**. NiceGUI exige une
connexion active entre le navigateur et Python. Utiliser de préférence un domaine
ou sous-domaine dédié à la racine `/` ; un déploiement sous un préfixe de chemin
n'est pas configuré par ce prototype. Le proxy, le DNS et le certificat restent
à configurer sur le serveur. Ces fichiers ne modifient aucun VPS.

Si le reverse proxy est lui-même dans un conteneur, `127.0.0.1` y désigne ce
conteneur : le connecter au réseau de ce service et utiliser `nicegui:8080`, ou
adapter son accès à l'hôte. Voir la [documentation de déploiement NiceGUI](https://nicegui.io/documentation/section_configuration_deployment).

L'installation utilise le projet Compose `notebook-nicegui` et un volume
dédié pour `.nicegui`. Les réglages s’exportent en JSON ; conservez-les avec
les PDF téléchargés sur votre poste.

```bash
# Arrêter l'application en conservant ses volumes :
docker compose -f compose.nicegui.yml down
```

Un seul processus applicatif est prévu. Les réglages de chaque connexion et
les PDF générés restent en mémoire ; ils ne sont pas restaurés après redémarrage.
Le JSON exporté permet de retrouver les réglages et de régénérer le carnet.

## Hors ligne et limites

Vérifications effectuées sur macOS et dans Docker Linux ARM64 : construction de
l'image Python 3.12, démarrage HTTP, état de santé du conteneur, génération et
conversion PNG pour les deux modes, exécution sans privilèges, clé de session
avec permissions `0600` et écriture dans le volume Compose. Les réglages d'une
session ont également survécu à un `docker restart` avec le volume existant,
sans modifier les paramètres d'hébergement. L'interface
a également été contrôlée dans le navigateur à une largeur mobile de 390 px.
Les plateformes natives Windows/Linux et le déploiement sur un VPS réel n'ont
pas été testés. La confirmation manuelle du dialogue système reste à vérifier
sur chaque plateforme ; son résultat est simulé dans les tests automatisés.

- **Local / bureau :** après installation des paquets et de Poppler, le serveur
  Python et les rendus PDF fonctionnent sur la machine. Conserver les polices et
  les fichiers de l'application. La connexion locale au serveur reste nécessaire.
- **Web / VPS :** le navigateur dépend de sa connexion au serveur pour les
  aperçus et la génération. Ce n'est pas une application web qui peut continuer
  à générer des PDF après déconnexion.
- **PDF exporté :** une fois téléchargé, le carnet et ses liens internes
  fonctionnent sans l'application ni connexion réseau, selon le lecteur PDF.
- **Accès :** l’application ne propose pas de comptes utilisateurs. Pour un
  usage privé, activer l’authentification de cette application dans Coolify.
- **Réglages conservés :** ils appartiennent à un navigateur et à sa clé de
  session. Vider les données du site, changer de machine ou perdre
  `NICEGUI_STORAGE_SECRET` les rend illisibles. Exporter le JSON pour un
  archivage durable.
- **Formats :** les surfaces des tablettes viennent des fiches officielles et
  les rendus sont audités, mais l'écriture au stylet n'a été essayée que sur le
  Viwoods AiPaper. Les autres profils sont « format vérifié, usage sur appareil
  non testé ».
- **Charge :** un carnet complet peut dépasser mille pages. Un carnet annuel de
  1 972 pages demande environ 11 secondes et 213 Mo de mémoire par génération. Tester les volumes
  et délais sur le VPS cible ; ce prototype ne constitue pas une validation de
  capacité ni une file de travaux distribuée.

Versions : [NiceGUI 3.17.0](https://pypi.org/project/nicegui/3.17.0/),
[pywebview 6.2.1](https://pypi.org/project/pywebview/6.2.1/), ReportLab 4.0.7 et
pdf2image 1.17.0. Les dépendances natives ne sont installées que pour le mode
bureau ; l'image Docker utilise le mode web.
