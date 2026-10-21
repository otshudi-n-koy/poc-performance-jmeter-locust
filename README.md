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
locust -f locust/locustfile.py --headless -u 100 -r 10 --run-time 5m --csv=resultats
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

## 💡 Conclusion pour un client

Pour un client avec des équipes QA classiques ou des besoins de protocoles variés (JDBC, SOAP), **JMeter** est recommandé.

Pour un client avec des stacks Python/DevOps souhaitant des tests versionnés dans Git et intégrés nativement à la CI/CD, **Locust** est idéal.
