#!/bin/sh
# Lance le plan JMeter en headless, cible et charge parametrables par variables d'environnement.
set -e

# Arguments explicites : on les execute tels quels (ex. docker compose run jmeter jmeter -n -t ...)
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

JMX="${JMX:-/jmeter/plan_de_test.jmx}"
OUT="${OUT_DIR:-/resultats/rapport_html}"
JTL="${JTL_FILE:-/resultats/resultats.jtl}"

# -e -o exige un dossier de sortie vide : on nettoie les executions precedentes
rm -rf "$OUT" "$JTL"

exec jmeter -n \
  -t "$JMX" \
  -Jhost="${TARGET_HOST:-mock}" \
  -Jport="${TARGET_PORT:-8080}" \
  -Jprotocol="${TARGET_PROTOCOL:-http}" \
  -Jthreads="${THREADS:-50}" \
  -Jramp="${RAMP:-10}" \
  -Jduration="${DURATION:-60}" \
  -l "$JTL" \
  -e -o "$OUT"
