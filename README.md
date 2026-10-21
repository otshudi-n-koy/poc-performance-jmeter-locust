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

## 📚 Documentation détaillée

| Document | Contenu |
|---|---|
| [jmeter/README.md](jmeter/README.md) | Structure du plan, propriétés `-J`, corrélation, lecture du rapport HTML |
| [locust/README.md](locust/README.md) | Poids des tâches, `on_start`, fichiers CSV, comparaison avec JMeter |
| [mock_api/README.md](mock_api/README.md) | API de démonstration, options de latence, limites |
| [DEMO-ENTRETIEN.md](DEMO-ENTRETIEN.md) | Script de démonstration et questions/réponses pour un entretien |

## 💡 Conclusion pour un client

Pour un client avec des équipes QA classiques ou des besoins de protocoles variés (JDBC, SOAP), **JMeter** est recommandé.

Pour un client avec des stacks Python/DevOps souhaitant des tests versionnés dans Git et intégrés nativement à la CI/CD, **Locust** est idéal.
