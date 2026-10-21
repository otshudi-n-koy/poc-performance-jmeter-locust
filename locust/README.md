# Scénario Locust — POC API

Même scénario que le plan JMeter, mais écrit en Python : c'est l'approche **Tests as Code**.
Le test devient du code versionné dans Git, relu en revue de code et exécuté par la CI.

## Fichier

| Fichier | Rôle |
|---|---|
| `locustfile.py` | Scénario de charge (Locust 2.x) |

## Structure

| Élément | Rôle |
|---|---|
| `class ApiUser(HttpUser)` | Un utilisateur virtuel = une instance de cette classe |
| `wait_time = between(1, 3)` | Temps de réflexion aléatoire entre 2 actions (simule un humain) |
| `on_start()` | Exécuté **une fois** au démarrage de chaque utilisateur : login + récupération du jeton |
| `@task(3) acceder_route_protegee()` | Tâche de poids 3 → tirée 3 fois plus souvent que la suivante |
| `@task(1) voir_healthcheck()` | Tâche de poids 1 |

La répartition réelle est donc **75 % / 25 %**. C'est la différence conceptuelle majeure avec JMeter :
ici, le profil de charge est une **probabilité** déclarée dans le code, pas un enchaînement de
samplers.

## Lancement avec l'interface web

```bash
locust -f locust/locustfile.py --host https://api.example.com
```
Puis ouvrir <http://localhost:8089> : nombre d'utilisateurs, vitesse d'arrivée, courbes temps réel.
L'IHM Locust est un **serveur de test**, pas seulement un éditeur — c'est utilisable pendant la mesure,
contrairement au GUI JMeter.

## Lancement headless (CI/CD)

Le fichier **ne définit pas de `host`** : `--host` est donc obligatoire.

```bash
locust -f locust/locustfile.py --headless -u 100 -r 10 --run-time 5m --host https://api.example.com --csv=resultats
```

| Option | Effet |
|---|---|
| `-u 100` | 100 utilisateurs virtuels simultanés |
| `-r 10` | 10 utilisateurs ajoutés par seconde (ramp-up) |
| `--run-time 5m` | Durée du palier |
| `--csv=resultats` | Export des statistiques en CSV |

Fichiers produits à la racine : `resultats_stats.csv` (agrégat par endpoint),
`resultats_failures.csv` (échecs), `resultats_stats_history.csv` (série temporelle).
Un rapport HTML autonome s'obtient en ajoutant `--html=rapport.html`.

Colonnes clés de `resultats_stats.csv` : `Request Count`, `Failure Count`, `Average Response Time`,
`Requests/s`, puis les percentiles `50%`, `66%`, `90%`, `95%`, `99%`, `99.9%`.

## Démo locale hors ligne (recommandée)

Le dépôt fournit une API mock (`mock_api/mock_server.py`) qui implémente exactement `/login`,
`/protected` et `/health` : **le locustfile fonctionne sans aucune modification**.

```bash
# terminal 1
python mock_api/mock_server.py --port 8080 --latency-ms 60

# terminal 2
locust -f locust/locustfile.py --headless -u 50 -r 10 --run-time 1m --host http://127.0.0.1:8080 --csv=resultats
```

Pour montrer l'effet d'un backend lent en direct : relancer le mock avec `--latency-ms 400`, rejouer
le même test, et comparer `Average Response Time` / `95%` dans les deux CSV. C'est la démonstration
la plus parlante — même charge, même scénario, seule la cible change.

### Dépannage : `PermissionError` sur les CSV

Deux causes possibles, dans cet ordre :

1. **Le fichier est ouvert sous Windows** (Excel, VS Code, aperçu). Windows le verrouille, le conteneur
   ne peut plus l'écraser, et Docker renvoie `PermissionError: '/resultats/resultats_stats.csv'`.
   Fermez le fichier, ou changez de préfixe : `CSV_PREFIX=run2` (PowerShell : `$env:CSV_PREFIX='run2'`).
2. **Vous passez une commande personnalisée** : elle est maintenant exécutée telle quelle, donc les
   chemins que vous indiquez (`--csv=/app/resultats/...`) doivent exister. Le volume du compose monte
   déjà `./resultats` sur `/resultats` — inutile d'ajouter un second `-v`.

## Adapter le scénario à une API publique réelle

`https://dummyjson.com` (**vérifié le 2026-10-21**) : `POST /auth/login` → `200` avec la clé
`accessToken`, `GET /auth/me` avec `Bearer` → `200`, sans en-tête → `401`, `GET /test` → `200`.

Le fichier du POC vise `/login`, `/protected` et `/health`, qui n'existent pas sur cette API. Variante
prête à l'emploi :

```python
from locust import HttpUser, task, between


class ApiUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.post("/auth/login", json={
            "username": "emilys",
            "password": "emilyspass"
        })
        if response.status_code == 200:
            self.token = response.json().get("accessToken")
        else:
            self.token = None
            print(f"Échec du login : {response.status_code}")

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def acceder_route_protegee(self):
        self.client.get("/auth/me", headers=self.auth_headers, name="/auth/me")

    @task(1)
    def voir_healthcheck(self):
        self.client.get("/test", name="/test")
```

Lancement : `locust -f locust/locustfile.py --host https://dummyjson.com`.

## Points à savoir défendre en entretien

- **`on_start` = la corrélation** : chaque utilisateur virtuel possède son propre jeton, exactement
  comme un utilisateur réel. C'est l'équivalent du JSON Extractor de JMeter, en 3 lignes de Python.
- **Poids des tâches** : `@task(3)` / `@task(1)` modélise un parcours majoritaire et un parcours
  minoritaire. On décrit un **profil d'usage**, pas une séquence.
- **`wait_time`** : sans temps de réflexion, on mesure la vitesse du générateur, pas la capacité du
  serveur.
- **Test as Code** : diff lisible en revue, rejouable, paramétrable par variables d'environnement,
  versionné avec l'application — l'argument décisif face à un `.jmx` XML.
- **CI/CD natif** : `--headless --csv` suffit à produire des artefacts exploitables, sans dépendance
  Java. Voir `.github/workflows/performance.yml`.
- **Comparaison honnête** : JMeter reste supérieur sur la couverture protocolaire (JDBC, JMS, SOAP) et
  sur l'existant en équipe QA ; Locust gagne sur l'intégration DevOps et la lisibilité du code.

## Limites connues du fichier

- **Aucun `host` défini** → `--host` obligatoire, sinon Locust refuse de démarrer.
- En cas d'échec du login, `self.token` reste indéfini dans la version du POC : l'en-tête devient
  alors `Bearer None` et la tâche suivante échoue en `401` — avec la variante ci-dessus (`.get()`
  + `auth_headers`), l'erreur est au moins explicite.
- Pas de `catch_response` / `self.environment.events.request` : les assertions métier sur le corps de
  réponse ne sont pas vérifiées, seul le code HTTP compte.
- `print()` pour les erreurs : acceptable en POC, à remplacer par du logging ou une exception
  `StopUser` en production.
