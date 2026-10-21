# POC Performance : JMeter vs Locust

[![Performance Tests](https://github.com/otshudi-n-koy/poc-performance-jmeter-locust/actions/workflows/performance.yml/badge.svg)](https://github.com/otshudi-n-koy/poc-performance-jmeter-locust/actions/workflows/performance.yml)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

Un même scénario d'API REST — authentification, extraction de jeton (corrélation), appel d'une route
protégée — écrit dans deux outils open source : **Apache JMeter** (XML, interface graphique) et
**Locust** (code Python). Une cible mock locale rend l'ensemble exécutable hors ligne, une stack Docker
supprime toute installation, et une CI à seuils bloquants vérifie chaque exécution.

## Sommaire

- [Ce que ce POC démontre](#ce-que-ce-poc-démontre)
- [Démarrage rapide (Docker)](#démarrage-rapide-docker)
- [Sans Docker](#sans-docker)
- [Structure du dépôt](#structure-du-dépôt)
- [Analyse comparative](#analyse-comparative)
- [Intégration continue](#intégration-continue)
- [Résultats de référence](#résultats-de-référence)
- [Documentation détaillée](#documentation-détaillée)
- [Limites connues](#limites-connues)
- [Conclusion pour un client](#conclusion-pour-un-client)

## Ce que ce POC démontre

- **Le même scénario dans deux paradigmes** : un plan XML piloté par interface (JMeter) et du code
  Python versionné (Locust) — pour comparer ce qui se compare.
- **La corrélation** : le jeton renvoyé par `/login` est extrait puis réinjecté dans l'en-tête
  `Authorization` des requêtes suivantes. Sans elle, aucun test authentifié n'a de sens.
- **L'externalisation de la cible et de la charge** : propriétés `-J` côté JMeter, `--host` et variables
  d'environnement côté Locust. Aucun fichier à modifier pour changer d'environnement.
- **Un garde-fou automatisé** : la CI démarre la cible, joue les deux scénarios et **échoue** si le p95
  dépasse 500 ms ou si une requête échoue. Un test de charge qui ne peut pas échouer ne prouve rien.

## Démarrage rapide (Docker)

Rien à installer, hormis Docker Desktop.

```bash
docker compose up -d mock        # la cible, sur http://localhost:8080
docker compose run --rm locust   # 50 utilisateurs, 1 min
docker compose run --rm jmeter   # 50 threads, 60 s
docker compose down
```

Puis ouvrir `resultats/rapport_html/index.html` (rapport JMeter) ou `resultats/resultats.html`
(rapport Locust). **Résultat attendu** : environ 1 000 échantillons et 0 % d'erreur côté JMeter,
environ 1 400 requêtes et 0 échec côté Locust.

Charge et latence se règlent par variables d'environnement, sans éditer de fichier :

```bash
MOCK_LATENCY_MS=400 docker compose up -d mock
THREADS=100 DURATION=120 docker compose run --rm jmeter
USERS=200 RUN_TIME=3m docker compose run --rm locust
```

Sous PowerShell, les variables s'écrivent `$env:THREADS=100` (une par ligne, avant la commande).

| Image | Base | Taille |
|---|---|---|
| `poc-perf-mock` | `python:3.12-slim` | 177 Mo |
| `poc-perf-locust` | `python:3.12-slim` + Locust | 256 Mo |
| `poc-perf-jmeter` | `eclipse-temurin:17-jre` + JMeter 5.6.3 | 624 Mo |

> **Piège Windows : un fichier ouvert est verrouillé.** Si `resultats/resultats_stats.csv` est ouvert
> dans Excel ou VS Code pendant un test, le conteneur échoue avec
> `PermissionError: '/resultats/resultats_stats.csv'` — Docker traduit le verrou Windows en erreur de
> permission, ce qui ressemble à un problème de droits alors que c'est un fichier ouvert. Fermez-le,
> ou changez le préfixe de sortie : `$env:CSV_PREFIX='run2'; docker compose run --rm locust`.

## Sans Docker

### Prérequis

| Outil | Version | Remarque |
|---|---|---|
| Java | **17** recommandé (11 minimum) | c'est la version des images Docker et de la CI |
| Apache JMeter | **5.6.3** | télécharger l'archive binaire, ajouter `bin/` au `PATH` |
| Python | **3.12** recommandé (3.9 minimum) | Locust 2.x ne supporte pas encore les versions plus récentes |
| Locust | `pip install "locust>=2.20,<3"` | borne haute : une majeure casserait le scénario |

La cible mock ne demande **aucune dépendance** : bibliothèque standard uniquement.

### Lancer la démo locale, hors ligne

```bash
# terminal 1 — la cible
python mock_api/mock_server.py --port 8080 --latency-ms 60

# terminal 2 — Locust
locust -f locust/locustfile.py --headless -u 50 -r 10 --run-time 1m \
       --host http://127.0.0.1:8080 --csv=resultats

# terminal 2 bis — JMeter
jmeter -n -t jmeter/plan_de_test.jmx \
       -Jhost=127.0.0.1 -Jport=8080 -Jprotocol=http \
       -l resultats.jtl -e -o rapport_html
```

La démonstration la plus parlante : relancer la cible avec `--latency-ms 400`, rejouer le même scénario,
comparer les deux rapports. Même charge, seule la latence de la cible change.

### Cibler une autre API

Le plan JMeter pointe par défaut sur `api.example.com`, une adresse de contrat d'interface qui n'existe
pas. On la remplace en ligne de commande : `-Jhost=… -Jport=… -Jprotocol=…`.

Pour une API publique réelle, `https://dummyjson.com` fonctionne (vérifié le 2026-10-21 : `POST
/auth/login` → `200` avec la clé `accessToken` ; `GET /auth/me` avec `Bearer` → `200`, sans en-tête →
`401`). Il faut alors adapter les chemins et le nom du jeton — le détail est dans
[jmeter/README.md](jmeter/README.md) et
[locust/README.md](locust/README.md).

## Structure du dépôt

```
├── jmeter/
│   ├── plan_de_test.jmx      plan JMeter : Thread Group, corrélation, assertion
│   └── README.md             structure du plan, propriétés -J, lecture du rapport
├── locust/
│   ├── locustfile.py         scénario Locust : on_start (login), tâches pondérées
│   └── README.md             poids des tâches, CSV, comparaison avec JMeter
├── mock_api/
│   ├── mock_server.py        cible locale (stdlib) : /login, /protected, /health
│   └── README.md             endpoints, latence simulée, limites
├── docker/
│   ├── Dockerfile.mock       image de la cible
│   ├── Dockerfile.jmeter     JMeter 5.6.3 sur JRE 17
│   ├── Dockerfile.locust     Locust sur Python 3.12
│   └── entrypoint-*.sh       cible et charge par variables d'environnement
├── ci/
│   └── check_thresholds.py   seuils bloquants : p95 et taux d'erreur
├── .github/workflows/
│   └── performance.yml       CI : cible mock, deux tests, seuils, release sur tag
├── docker-compose.yml        stack complète (mock + jmeter + locust)
├── DEMO-ENTRETIEN.md         script de démonstration en entretien
└── QUESTIONS-REPONSES.md     22 questions d'entretien et leurs réponses
```

## Analyse comparative

| Critère | JMeter | Locust |
|---|---|---|
| Approche | Interface graphique / XML | Code Python (As Code) |
| Courbe d'apprentissage | Modérée | Faible (si Python) |
| Protocoles supportés | Très large (HTTP, JDBC, JMS...) | Principalement HTTP(S) |
| Intégration CI/CD | Bonne (mode headless) | Excellente (natif) |
| Rapports | HTML complet intégré | Interface web temps réel + CSV |

## Intégration continue

Le workflow [`.github/workflows/performance.yml`](.github/workflows/performance.yml) exécute les deux
scénarios contre la cible mock, à chaque push sur `main`, à chaque pull request, et sur demande :

1. démarrage de `mock_api/mock_server.py` sur le port 8080 (latence simulée de 50 ms) ;
2. Locust puis JMeter en headless, ciblés sur `http://127.0.0.1:8080` — aucun appel à une API tierce ;
3. **seuils bloquants** avec `ci/check_thresholds.py` : p95 < 500 ms et zéro erreur, sinon le job
   échoue ;
4. publication des rapports en artefacts, **même si un seuil casse**, pour pouvoir diagnostiquer.

```bash
# les mêmes contrôles, en local
python ci/check_thresholds.py --jtl resultats/resultats.jtl --max-p95-ms 500
python ci/check_thresholds.py --locust-csv resultats/resultats_stats.csv --max-p95-ms 500
```

### Publier une release avec les rapports

Les artefacts GitHub Actions exigent un compte connecté pour être téléchargés. Un tag `v*` déclenche
donc en plus la création d'une release, dont les pièces jointes sont **publiques** :

```bash
git tag v1.0.0-poc
git push origin v1.0.0-poc
```

Le workflow joint `rapport-jmeter.zip` (rapport HTML complet) et `rapport-locust.html` (fichier
autonome), générés par cette exécution et dont les seuils ont été vérifiés.

## Résultats de référence

Campagne du 2026-10-21, cible mock avec `--latency-ms 60`, 50 utilisateurs virtuels, une minute.
Reproductible avec la commande de la section [Sans Docker](#sans-docker).

| Outil | Simulation sur la cible | Résultat |
|---|---|---|
| JMeter 5.6.3 | 50 threads, rampe 10 s | 1 000 échantillons, **0 % d'erreur**, 92 trans/s, moyenne 45 ms, **p95 93 ms**, p99 139 ms |
| Locust 2.46.7 | 50 utilisateurs, rampe 10/s | 1 429 requêtes, **0 échec**, 24,7 req/s, moyenne 52 ms, **p95 78 ms**, p99 110 ms |

**Pourquoi les débits diffèrent (92 contre 24,7 req/s)** : le scénario Locust applique un
`wait_time = between(1, 3)` — un temps de réflexion humain — alors que le plan JMeter n'en a aucun et
enchaîne les requêtes au maximum. Les deux outils ne génèrent donc pas la même pression : ce sont les
**latences** qui sont comparables (~45 contre ~52 ms), pas les débits. Savoir l'expliquer vaut mieux
que masquer l'écart en alignant artificiellement les chiffres.

Deux corrections ont marqué ce POC, toutes deux visibles dans les journaux :

- **Le plan JMeter d'origine renvoyait `400` sur `/login` pour 100 % des requêtes** : les paramètres
  `user`/`pass` étaient déclarés sans `Argument.name`, donc envoyés sous la forme `=testuser`. Corrigé,
  puis vérifié — 0 % d'erreur.
- **La cible mock produisait des latences de 1 000, 1 100, 1 200 ms** sur la première requête de chaque
  utilisateur. Cause : `request_queue_size = 5` par défaut en Python, file d'acceptation saturée par 50
  connexions simultanées, `SYN` renvoyés après 1 s. Corrigé (128) : p90 du login ramené de 1 000 ms à
  80 ms. Détail dans [mock_api/README.md](mock_api/README.md).

## Documentation détaillée

| Document | Contenu |
|---|---|
| [jmeter/README.md](jmeter/README.md) | Structure du plan, propriétés `-J`, corrélation, lecture du rapport HTML |
| [locust/README.md](locust/README.md) | Poids des tâches, `on_start`, fichiers CSV, dépannage |
| [mock_api/README.md](mock_api/README.md) | API de démonstration, options de latence, piège du backlog, limites |
| [ci/](ci/) + [.github/workflows/](.github/workflows/) | Seuils bloquants et publication des rapports |
| [docker/](docker/) + [docker-compose.yml](docker-compose.yml) | Images et stack complète |
| [DEMO-ENTRETIEN.md](DEMO-ENTRETIEN.md) | Script de démonstration et questions/réponses pour un entretien |
| [QUESTIONS-REPONSES.md](QUESTIONS-REPONSES.md) | 22 questions d'entretien avec réponses à dire, et les pièges |

## Limites connues

- **La cible mock n'est pas représentative** d'une application réelle : pas de base de données, pas de
  réseau, un seul processus Python (GIL). Elle sert à rendre le POC déterministe, pas à mesurer une
  capacité.
- **Un seul compte de test** (`testuser`) pour tous les utilisateurs virtuels : le cache applicatif est
  artificiellement chaud. Un vrai test génère un utilisateur par thread (`CSV Data Set Config`).
- **Pas de temps de réflexion côté JMeter**, contrairement à Locust : les deux scénarios ne génèrent pas
  la même pression (voir les résultats ci-dessus).
- **Assertions limitées au code HTTP** : une réponse `200` au contenu invalide passerait pour un succès.
- **Pas de charge distribuée** : au-delà de quelques centaines d'utilisateurs virtuels, il faudrait
  passer en contrôleur/worker (JMeter) ou `--master`/`--worker` (Locust).
- **Pas de supervision serveur** (APM, CPU, pool de connexions) : le POC mesure, il n'explique pas le
  goulot.

## Conclusion pour un client

Pour un client avec des équipes QA classiques ou des besoins de protocoles variés (JDBC, SOAP),
**JMeter** est recommandé : interface graphique, couverture protocolaire large, compétences déjà
présentes.

Pour un client avec des stacks Python/DevOps souhaitant des tests versionnés dans Git et intégrés
nativement à la CI/CD, **Locust** est idéal : le scénario est du code, relu en revue et exécuté par le
pipeline.

## Licence

[MIT](LICENSE).
