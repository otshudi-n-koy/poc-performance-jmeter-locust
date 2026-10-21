# POC Performance : JMeter vs Locust

## 🎯 Objectif
Ce Proof of Concept (POC) compare deux outils open source de tests de charge :
- **Apache JMeter** : l'outil le plus proche de NeoLoad (interface graphique, couverture protocolaire large, modèle contrôleur/worker).
- **Locust** : une approche "Tests as Code" en Python, idéale pour les équipes DevOps et l'intégration CI/CD.

Le scénario teste une API REST avec authentification (login), extraction de token (corrélation) et validation de la réponse.

## 🛠️ Prérequis
- Java 11+ (pour JMeter)
- Python 3.9+ (pour Locust)
- `pip install locust`

## 🚀 Lancement des tests

### JMeter (Mode Headless)
```bash
jmeter -n -t jmeter/plan_de_test.jmx -l resultats.jtl -e -o rapport_html
```

Le rapport HTML est généré dans le dossier `rapport_html/`.

### Locust (Mode Headless)
```bash
locust -f locust/locustfile.py --headless -u 100 -r 10 --run-time 5m --host https://api.example.com --csv=resultats
```

Les résultats CSV sont générés à la racine.

## 📊 Analyse comparative

| Critère | JMeter | Locust |
|---|---|---|
| Approche | Interface graphique / XML | Code Python (As Code) |
| Courbe d'apprentissage | Modérée | Faible (si Python) |
| Protocoles supportés | Très large (HTTP, JDBC, JMS...) | Principalement HTTP(S) |
| Intégration CI/CD | Bonne (mode headless) | Excellente (natif) |
| Rapports | HTML complet intégré | Interface web temps réel + CSV |

## 🧪 Démonstration locale, hors ligne

Les deux scénarios ciblent `api.example.com` par défaut. Une API mock en Python (bibliothèque
standard, aucune dépendance) joue le rôle de cible : le POC est exécutable **sans réseau**.

```bash
# terminal 1 — la cible
python mock_api/mock_server.py --port 8080 --latency-ms 60

# terminal 2 — Locust
locust -f locust/locustfile.py --headless -u 50 -r 10 --run-time 1m --host http://127.0.0.1:8080 --csv=resultats

# terminal 2 bis — JMeter
jmeter -n -t jmeter/plan_de_test.jmx -Jhost=127.0.0.1 -Jport=8080 -Jprotocol=http -l resultats.jtl -e -o rapport_html
```

Aucun fichier de scénario n'est modifié : la cible et la charge passent par `-J` (JMeter) et `--host`
(Locust). Relancer le mock avec `--latency-ms 400` puis comparer les deux rapports donne la
démonstration la plus parlante : même charge, seul le temps de réponse change.

## 🐳 Avec Docker (si les prérequis manquent)

Rien à installer : Java, JMeter, Locust et la cible mock sont dans des images figées. Seul Docker
Desktop est nécessaire.

```bash
docker compose up -d mock        # la cible, exposée sur http://localhost:8080
docker compose run --rm locust   # 50 utilisateurs, 1 min
docker compose run --rm jmeter   # 50 threads, 60 s
docker compose down
```

Résultats dans `resultats/` : `rapport_html/` (rapport HTML JMeter) et les CSV Locust.
Charge et latence se règlent par variables d'environnement, **sans éditer de fichier** :

```bash
MOCK_LATENCY_MS=400 docker compose up -d mock
THREADS=100 DURATION=120 docker compose run --rm jmeter
USERS=200 RUN_TIME=3m docker compose run --rm locust
```

Sous PowerShell, les variables s'écrivent `$env:THREADS=100` (une par ligne, avant la commande).

> **Piège Windows : un fichier ouvert est verrouillé.** Si `resultats/resultats_stats.csv` est ouvert
> dans Excel ou VS Code pendant un test, le conteneur échoue avec
> `PermissionError: '/resultats/resultats_stats.csv'` — Docker traduit le verrou Windows en erreur de
> permission, ce qui ressemble à un problème de droits alors que c'est un fichier ouvert. Deux
> solutions : fermer le fichier, ou changer de préfixe de sortie :
>
> ```powershell
> $env:CSV_PREFIX='run2'; docker compose run --rm locust   # ecrit run2_stats.csv
> ```

Les entrypoints transmettent désormais les arguments : `docker compose run --rm locust locust --help`
execute exactement la commande donnée, sans passer par les valeurs par défaut.

| Image | Base | Taille |
|---|---|---|
| `poc-perf-mock` | `python:3.12-slim` | 177 Mo |
| `poc-perf-locust` | `python:3.12-slim` + Locust | 256 Mo |
| `poc-perf-jmeter` | `eclipse-temurin:17-jre` + JMeter 5.6.3 | 624 Mo |

**Validé le 2026-10-21** en conteneurs :

| Exécution | Résultat |
|---|---|
| JMeter, 10 threads / 15 s | 200 échantillons, **0 % d'erreur**, p95 16 ms (`/login`) et 10 ms (`/protected`) |
| Locust, 10 utilisateurs / 20 s | 101 requêtes, **0 échec** |
| Locust, 50 utilisateurs / 60 s (après correction de la cible) | 1 476 requêtes, **0 échec**, p95 global 50 ms |
| Artefacts | `rapport_html/index.html` (9,5 Ko), 4 CSV Locust, toutes les requêtes en `200` |

> À propos du plan JMeter : la version initiale renvoyait **400 sur `/login` pour 100 % des requêtes**
> (les paramètres `user`/`pass` étaient déclarés sans `Argument.name`, donc envoyés sous forme
> `=testuser`). Corrigé et revérifié : 0 % d'erreur. Si vous repartez du fichier d'origine, sachez que
> ce défaut est réel — et qu'il se voit immédiatement dans le `.jtl`.

Docker Desktop n'est pas nécessaire sur le poste du client : `docker compose` fonctionne sur macOS,
Linux et Windows.

## 📚 Documentation détaillée

| Document | Contenu |
|---|---|
| [jmeter/README.md](jmeter/README.md) | Structure du plan, propriétés `-J`, corrélation, lecture du rapport HTML |
| [locust/README.md](locust/README.md) | Poids des tâches, `on_start`, fichiers CSV, comparaison avec JMeter |
| [mock_api/README.md](mock_api/README.md) | API de démonstration, options de latence, limites |
| [DEMO-ENTRETIEN.md](DEMO-ENTRETIEN.md) | Script de démonstration et questions/réponses pour un entretien |
| [QUESTIONS-REPONSES.md](QUESTIONS-REPONSES.md) | 22 questions d'entretien avec réponses à dire, et les pièges |

## 💡 Conclusion pour un client

Pour un client avec des équipes QA classiques ou des besoins de protocoles variés (JDBC, SOAP), **JMeter** est recommandé.

Pour un client avec des stacks Python/DevOps souhaitant des tests versionnés dans Git et intégrés nativement à la CI/CD, **Locust** est idéal.
