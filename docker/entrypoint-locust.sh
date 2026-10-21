#!/bin/sh
# Lance le scenario Locust en headless, cible et charge parametrables par variables d'environnement.
#
# Si des arguments sont fournis (docker compose run locust locust -f ... --csv=...), ils sont
# executes tels quels : l'entrypoint ne s'interpose plus, ce qui evite les surprises.
set -e

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

LOCUSTFILE="${LOCUSTFILE:-/locust/locustfile.py}"
CSV_PREFIX="${CSV_PREFIX:-resultats}"

exec locust -f "$LOCUSTFILE" \
  --headless \
  -u "${USERS:-50}" \
  -r "${SPAWN_RATE:-10}" \
  --run-time "${RUN_TIME:-1m}" \
  --host "${TARGET:-http://mock:8080}" \
  --csv="/resultats/${CSV_PREFIX}" \
  --html="/resultats/${CSV_PREFIX}.html"
