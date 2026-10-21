#!/bin/sh
# Lance le scenario Locust en headless, cible et charge parametrables par variables d'environnement.
set -e

LOCUSTFILE="${LOCUSTFILE:-/locust/locustfile.py}"

exec locust -f "$LOCUSTFILE" \
  --headless \
  -u "${USERS:-50}" \
  -r "${SPAWN_RATE:-10}" \
  --run-time "${RUN_TIME:-1m}" \
  --host "${TARGET:-http://mock:8080}" \
  --csv=/resultats/resultats \
  --html=/resultats/rapport_locust.html
