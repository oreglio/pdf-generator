# Déployer les carnets Viwoods sur pdf.readtoken.app

Ce guide déploie l’interface NiceGUI pour les carnets **datés et non datés**, avec
aperçus, export PDF et import/export des réglages. Il suppose que Coolify est déjà
installé sur le VPS et que vous pouvez modifier le DNS de `readtoken.app`.
La construction Docker a été vérifiée localement ; le VPS n’a pas été déployé
depuis cette session.

## 1. Préparer le DNS

Chez le fournisseur DNS de `readtoken.app`, ajouter :

| Type | Nom | Valeur |
| --- | --- | --- |
| A | `pdf` | IPv4 publique du VPS qui hébergera l’application |

Un enregistrement AAAA n’est utile que si le VPS et son proxy fonctionnent aussi
en IPv6. Conserver les autres enregistrements du domaine. Vérifier la résolution
depuis votre ordinateur :

```bash
dig +short pdf.readtoken.app A
dig +short pdf.readtoken.app AAAA
```

Les ports HTTP/HTTPS du proxy Coolify doivent être accessibles depuis Internet.
Pour une première installation avec Cloudflare, le mode DNS seul simplifie le
diagnostic. [Documentation DNS Coolify](https://coolify.io/docs/core/networking/dns).

## 2. Créer l’application depuis GitHub

Dans le projet et l’environnement Coolify souhaités, choisir **New Resource**,
puis une source Git. Utiliser le dépôt public ou votre connexion GitHub existante
au compte `oreglio` :

```text
https://github.com/oreglio/pdf-generator
```

Renseigner :

| Réglage | Valeur pour ce projet |
| --- | --- |
| Nom | `viwoods-pdf` |
| Branche | `feat/nicegui-poc` |
| Build Pack | `Dockerfile` |
| Base Directory | `/` |
| Dockerfile Location | `Dockerfile.nicegui` (relatif à la racine) |
| Ports Exposes | `8080` |
| Port Mappings | Vide |
| Commande de démarrage personnalisée | Vide : utiliser le CMD du Dockerfile |

Si le champ Dockerfile impose un chemin commençant par `/`, saisir
`/Dockerfile.nicegui`. Après fusion de cette branche dans `main`, vous pourrez
sélectionner `main`. Le dépôt contient aussi un Dockerfile historique : choisir
explicitement **Dockerfile.nicegui**.
[Déploiement Dockerfile depuis Git](https://coolify.io/docs/applications/builds/dockerfile).

L’image embarque Python 3.12, NiceGUI, ReportLab, Poppler et les polices. Elle
démarre `python nicegui_app.py --web --host 0.0.0.0 --port 8080`, sous l’utilisateur
`notebook` (UID 10001). Aucun service de base de données n’est nécessaire.

## 3. Domaine et HTTPS

Dans **Configuration → General → Domains**, saisir :

```text
https://pdf.readtoken.app:8080
```

Le `:8080` indique au proxy le port **interne du conteneur**. L’adresse utilisée
dans votre navigateur sera simplement **https://pdf.readtoken.app**, sans port.
[Réglage des domaines et ports](https://coolify.io/docs/applications/configuration/general).

Le préfixe `https://` permet à Coolify de gérer le certificat. Attendre la bonne
résolution DNS avant le premier déploiement HTTPS.
[Domaines et certificats](https://coolify.io/docs/core/networking/domains).

Utiliser la racine de ce sous-domaine : l’application n’est pas configurée pour
un préfixe comme `/pdf`. Conserver la prise en charge WebSocket du proxy :
les interactions NiceGUI communiquent avec le serveur via Socket.IO.

## 4. Secret et stockage

Générer une valeur sur votre ordinateur :

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Dans **Environment Variables**, créer `NICEGUI_STORAGE_SECRET` avec cette valeur,
disponible à l’exécution, sans l’ajouter aux arguments de build. Garder la même
valeur lors des redéploiements et la conserver dans votre gestionnaire de secrets.

Dans **Persistent Storage**, ajouter un **Volume Mount** :

| Réglage | Valeur |
| --- | --- |
| Nom, si demandé | `nicegui-storage` |
| Source Path | Vide, volume géré par Docker |
| Destination Path | `/app/.nicegui` |

Ce répertoire est préparé dans l’image avec les droits de l’utilisateur applicatif.
Un volume préexistant doit également être accessible à l’UID 10001. Enregistrer
puis appliquer le montage au déploiement.
[Stockage persistant Coolify](https://coolify.io/docs/applications/configuration/persistent-storage).

Ce volume conserve désormais, par navigateur, les **derniers réglages valides**
de chaque mode et les **profils nommés** de Folio, sous la clé versionnée
`folio_preferences`. Ils survivent à un redémarrage du conteneur et à un
redéploiement tant que le volume et `NICEGUI_STORAGE_SECRET` restent les mêmes.
Vérifié : après `docker restart` avec le volume existant, la session retrouve
son titre de carnet et ses profils, sans message d’erreur.

**Les PDF générés ne sont jamais archivés côté serveur**, et les réglages en
cours de saisie restent en mémoire. Avant de fermer une session ou de
redéployer, télécharger les PDF et exporter les réglages JSON. Ce JSON permet de
régénérer le carnet — appareil, confort, durée ou dates exactes, pages
facultatives et choix d’inclure ou non les week-ends — et traverse les
navigateurs, contrairement au stockage ci-dessus. Conserver vos exports sur
votre ordinateur et dans vos sauvegardes.

Changer `NICEGUI_STORAGE_SECRET` ou supprimer le volume rend les réglages
enregistrés illisibles : Folio repart alors de ses valeurs par défaut avec un
message, sans bloquer l’application.

L’application n’a pas de comptes utilisateurs. Si vous souhaitez un accès privé,
activer l’option **HTTP Basic Authentication** de cette application dans Coolify,
avec un identifiant et un mot de passe propres à cet outil.

## 5. Déployer et vérifier

Cliquer **Deploy**, suivre les logs et attendre l’état sain du conteneur.
Le Dockerfile fournit déjà un contrôle HTTP Python sur le port 8080. Coolify
utilise ce contrôle ; aucun contrôle supplémentaire basé sur `curl` n’est requis.
[Contrôles de santé](https://coolify.io/docs/applications/configuration/health-checks).

Depuis le terminal du conteneur dans Coolify, ces commandes vérifient le serveur
et le moteur d’aperçu :

```bash
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/', timeout=4).status)"
pdftoppm -v
id
```

Ouvrir **https://pdf.readtoken.app** puis vérifier :

1. L’aperçu apparaît et les onglets Calendrier, Semaine, Meeting et Backlog répondent.
2. Le téléchargement des cinq pages d’aperçu laisse l’interface utilisable.
3. Un petit carnet daté se génère et ses liens internes fonctionnent dans le lecteur PDF.
4. Décocher **Inclure les week-ends** réduit les journées après actualisation ; le
   calendrier garde les samedis/dimanches visibles et la navigation saute au lundi.
5. Le mode non daté, l’anglais et l’import/export JSON fonctionnent aussi.

Tester d’abord avec une liste et peu de tâches ; générer ensuite le carnet complet.
Les réglages par défaut des PDF publiés restent inchangés.

## 6. Mettre à jour et revenir en arrière

Après un push sur la branche configurée, relancer **Deploy**. Une intégration GitHub
peut aussi déclencher les déploiements automatiquement si vous l’activez. Garder
une seule instance applicative pour ce POC ; les données de travail sont en mémoire.

Avant une mise à jour, noter le commit déployé et exporter les réglages ouverts.
En cas de problème, utiliser **Rollback** vers une image précédente encore disponible.
Cela restaure le code, pas les données ni les paramètres Coolify : garder le même
secret et le même volume. Refaire le contrôle de génération après retour arrière.
[Retours arrière Coolify](https://coolify.io/docs/applications/deployments/rollbacks).

## Dépannage

| Symptôme | Vérification |
| --- | --- |
| Build Streamlit ou mauvaise interface | Build Pack Dockerfile et fichier `Dockerfile.nicegui` |
| 502 / No available server | Logs, santé du conteneur et port interne 8080 |
| Certificat absent | DNS A/AAAA et accessibilité du proxy sur HTTP/HTTPS |
| Interface déconnectée ou boutons inactifs | Connexion Socket.IO/WebSocket, éventuel proxy supplémentaire |
| PDF disponible mais aperçu absent | Présence de Poppler avec `pdftoppm -v` |
| Permission denied sous `.nicegui` | Destination du volume et droits de l’UID 10001 |
| Réglages perdus après redémarrage | Réimporter le JSON exporté ; le volume n’archive pas les carnets |

Pour lancer la même interface localement ou dans une fenêtre de bureau, voir
[NICEGUI.md](NICEGUI.md). `compose.nicegui.yml` sert au lancement Docker autonome ;
le parcours Coolify ci-dessus utilise directement le Dockerfile du dépôt.
