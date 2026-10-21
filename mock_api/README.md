# API mock — cible locale des scénarios

Les scénarios du dépôt ciblent `api.example.com`, qui n'existe pas. Cette API mock de ~180 lignes,
en **standard library Python uniquement**, fournit les trois endpoints attendus : elle rend le POC
exécutable **hors ligne**, sans compte, sans quota et sans dépendance réseau.

## Endpoints

| Route | Méthode | Réponse |
|---|---|---|
| `/login` | POST | `200` `{"access_token": "<hex>", "token_type": "Bearer", "expires_in": 3600}` — `401` si identifiants invalides, `400` si absents |
| `/protected` | GET | `200` `{"message": "acces autorise", "user": "testuser"}` avec `Authorization: Bearer <token>` valide, sinon `401` |
| `/health` | GET | `200` `{"status": "ok", "uptime_s": n}` |

Le login accepte **les deux formats** utilisés par les scénarios, ce qui permet de ne modifier aucun
fichier du POC :

```bash
# formulaire (ce qu'envoie plan_de_test.jmx)
curl -X POST http://127.0.0.1:8080/login -d 'user=testuser&pass=testpass'

# JSON (ce qu'envoie locustfile.py)
curl -X POST http://127.0.0.1:8080/login \
  -H 'Content-Type: application/json' \
  -d '{"user":"testuser","pass":"testpass"}'
```

Identifiants : `testuser` / `testpass`.

## Lancement

```bash
python mock_api/mock_server.py                          # 127.0.0.1:8080, sans latence
python mock_api/mock_server.py --port 8080 --verbose    # journalise chaque requête
python mock_api/mock_server.py --latency-ms 120 --jitter-ms 80
```

| Option | Effet |
|---|---|
| `--host` | Adresse d'écoute (défaut `127.0.0.1`) |
| `--port` | Port d'écoute (défaut `8080`) |
| `--latency-ms` | Latence fixe ajoutée à **`/protected`** — le levier pour faire varier vos courbes |
| `--jitter-ms` | Latence aléatoire ajoutée à `/protected` |
| `--verbose` | Journalise chaque requête sur stderr |

Le serveur affiche au démarrage les deux commandes prêtes à copier (Locust et JMeter).

## Utilisation avec les scénarios du dépôt

```bash
# terminal 1 — la cible
python mock_api/mock_server.py --port 8080 --latency-ms 60

# terminal 2 — Locust (aucune modification du locustfile)
locust -f locust/locustfile.py --headless -u 50 -r 10 --run-time 1m --host http://127.0.0.1:8080 --csv=resultats

# terminal 2 bis — JMeter (aucune modification du .jmx)
jmeter -n -t jmeter/plan_de_test.jmx \
       -Jhost=127.0.0.1 -Jport=8080 -Jprotocol=http \
       -Jthreads=50 -Jramp=10 -Jduration=60 \
       -l resultats.jtl -e -o rapport_html
```

Aucune édition de fichier : la cible et la charge sont des **propriétés** passées en ligne de commande.

## Vérifications effectuées (2026-10-21)

| Contrôle | Résultat |
|---|---|
| `GET /health` | `200` en 7 ms |
| `POST /login` JSON | `200` + `access_token` en 9 ms |
| `POST /login` formulaire | `200` + `access_token` en 3 ms |
| `POST /login` mauvais mot de passe | `401` `invalid_credentials` |
| `GET /protected` avec token | `200` en ~72 ms (latence 60 ms + jitter 40 ms bien appliquée) |
| `GET /protected` sans token / token inconnu | `401` |
| `GET /nope` | `404` |
| Charge : 300 requêtes, 25 en parallèle | 300 succès, 0 erreur, ~279 req/s |
| Python utilisé | 3.15.0, aucune dépendance |

## Latences quantifiées à 1 s : un piège d'outillage

Premier run Locust en conteneur, 50 utilisateurs : `POST /login` affichait une médiane à 39 ms…
et un **p90 à 1 000 ms, un max à 1 200 ms**. Quatre valeurs rondes, uniquement sur le login, qui
n'apparaissaient qu'au moment du démarrage des utilisateurs.

Cause : `socketserver.TCPServer` utilise par défaut `request_queue_size = 5`. Dès que 50 clients se
connectent dans la même seconde, la file d'acceptation déborde ; le noyau jette les `SYN` en trop, et
le client les renvoie **après un délai de 1 s** (ou reçoit un `RST`). Reproduction dans le conteneur,
50 connexions simultanées :

| Version | Résultat |
|---|---|
| `request_queue_size = 5` (défaut) | `ConnectionResetError: [Errno 104] Connection reset by peer` |
| `request_queue_size = 128` | p90 27 ms, max 36 ms, 0 reset — sur 50 **et** 100 connexions simultanées |

Après correction, le même scénario Locust (50 utilisateurs, 60 s) donne `POST /login` à
**p90 80 ms, p95 83 ms, max 89 ms** — au lieu de 1 000–1 200 ms.

**La leçon, et c'est le meilleur argument d'entretien de ce dépôt** : une latence bizarrement ronde
(1 000, 2 000, 3 000 ms) n'est presque jamais applicative. C'est un **artefact de mesure** —
retransmission TCP, `SYN` perdu, file d'attente pleine. Avant d'accuser l'application, il faut
s'assurer que le générateur et la cible ne saturent pas leurs propres files d'attente.

```bash
# vérifier où se situe le goulot
docker compose exec -T mock python /tmp/burst_login.py   # côté cible
docker stats                                            # CPU des conteneurs pendant le test
```


## Limites — à connaître avant d'en parler

- **Ce n'est pas un serveur de production** : jeton en mémoire, pas de persistance, un seul processus.
  300 requêtes concurrentes passent sans erreur, ce qui suffit largement pour une démo de 50 à
  200 utilisateurs virtuels ; au-delà, c'est le mock qu'on mesure, pas le scénario.
- **Le GIL Python plafonne le débit** : ne tirez pas de conclusion de performance *sur le mock*.
  Son rôle est de servir de cible **déterministe et contrôlée**, pas d'être un sujet de mesure.
- Pas de HTTPS, pas d'authentification OAuth complète, pas d'expiration réelle des jetons (le champ
  `expires_in` est décoratif) : suffisant pour la corrélation, insuffisant pour tester un parcours
  OAuth/refresh token.
- En entretien, assumez-le : « j'ai écrit une cible mock pour rendre le POC reproductible et
  démontrable hors ligne » est un argument de rigueur, pas un aveu de faiblesse.
