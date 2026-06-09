#!/usr/bin/env bash
# TalentAlign — post-deployment smoke test
#
# Verifies the deployed backend + frontend before opening the URL to users.
# Exits 0 on full green, non-zero on first failure.
#
# Usage:
#   BACKEND=https://your-backend.onrender.com \
#   FRONTEND=https://your-app.vercel.app \
#   bash Main/backend/scripts/smoke_test.sh [path/to/resume.pdf]
#
# If no resume path is given, defaults to tests/fixtures/Eklavya_Singh_Rathore_Resume.pdf
# relative to this script's repo location.

set -uo pipefail

BACKEND="${BACKEND:-http://localhost:8000}"
FRONTEND="${FRONTEND:-http://localhost:3000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RESUME="${1:-${BACKEND_DIR}/tests/fixtures/Eklavya_Singh_Rathore_Resume.pdf}"

# A small ML-engineer JD for the analyze test. Self-contained so the script
# does not depend on any docx fixture.
read -r -d '' JD <<'EOF' || true
About the job
Requirements
Proven experience as a Machine Learning Engineer or similar role
Strong knowledge of Python, scikit-learn, TensorFlow or PyTorch
Familiarity with data structures, statistics, and algorithms
Experience with SQL databases (MySQL, PostgreSQL)
Excellent communication and problem-solving skills

Responsibilities
Build and deploy ML models for classification and ranking
Run experiments, evaluate, and improve model performance
EOF

PASS=0
FAIL=0
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

ok()   { printf "${GREEN}[ ok ]${NC} %s\n" "$1"; PASS=$((PASS+1)); }
fail() { printf "${RED}[fail]${NC} %s\n" "$1"; printf "       %s\n" "$2"; FAIL=$((FAIL+1)); }
info() { printf "${YELLOW}[..]${NC}   %s\n" "$1"; }

echo "==============================================================="
echo " TalentAlign — Post-Deployment Smoke Test"
echo "==============================================================="
echo " backend:  $BACKEND"
echo " frontend: $FRONTEND"
echo " resume:   $RESUME"
echo

# ── Test 1: backend /health ────────────────────────────────────────────────
info "1. backend /health"
HEALTH_JSON="$(curl -fsS --max-time 15 "${BACKEND}/health" 2>&1)" || {
    fail "/health unreachable" "$HEALTH_JSON"; exit 1;
}
STATUS="$(echo "$HEALTH_JSON" | python -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)"
LLM_BACKEND="$(echo "$HEALTH_JSON" | python -c "import json,sys; print(json.load(sys.stdin).get('llm_backend',''))" 2>/dev/null)"
EMB_BACKEND="$(echo "$HEALTH_JSON" | python -c "import json,sys; print(json.load(sys.stdin).get('embedding_backend',''))" 2>/dev/null)"
if [ "$STATUS" = "ok" ]; then
    ok "/health → status=ok, llm_backend=$LLM_BACKEND, embedding_backend=$EMB_BACKEND"
else
    fail "/health did not return status=ok" "$HEALTH_JSON"
    exit 1
fi
if [ "$LLM_BACKEND" = "none" ]; then
    info "    Note: llm_backend=none — Gemini fallback path will run, narrative fields will be empty"
fi

# ── Test 2: backend /analyze with a real resume ────────────────────────────
info "2. backend /analyze (multipart: $RESUME + inline JD)"
if [ ! -f "$RESUME" ]; then
    fail "resume fixture missing" "$RESUME does not exist on this host"
    echo "       Skipping remaining backend tests."
else
    JD_FILE="$(mktemp)"; echo "$JD" > "$JD_FILE"
    ANALYZE_OUT="$(mktemp).json"
    HTTP_CODE="$(curl -s -o "$ANALYZE_OUT" --max-time 60 -w "%{http_code}" \
        -X POST "${BACKEND}/analyze" \
        -F "resume=@${RESUME}" \
        -F "jd_text=<${JD_FILE}")"
    rm -f "$JD_FILE"
    if [ "$HTTP_CODE" != "200" ]; then
        fail "/analyze returned HTTP $HTTP_CODE" "$(head -c 500 "$ANALYZE_OUT")"
    else
        # Payload checks
        KEY_COUNT="$(python -c "import json; print(len(json.load(open('$ANALYZE_OUT'))))" 2>/dev/null)"
        SCORE="$(python -c "import json; print(json.load(open('$ANALYZE_OUT')).get('placement_score'))" 2>/dev/null)"
        LEVEL="$(python -c "import json; print(json.load(open('$ANALYZE_OUT')).get('match_level'))" 2>/dev/null)"
        DOMAIN="$(python -c "import json; print(json.load(open('$ANALYZE_OUT')).get('domain_detected'))" 2>/dev/null)"
        STRENGTHS="$(python -c "import json; d=json.load(open('$ANALYZE_OUT')); print(len(d.get('final_summary',{}).get('strengths') or []))" 2>/dev/null)"
        if [ "$KEY_COUNT" = "29" ]; then
            ok "/analyze → 200, 29-key payload, score=$SCORE ($LEVEL), domain=$DOMAIN, strengths=$STRENGTHS"
        else
            fail "/analyze payload has $KEY_COUNT keys, expected 29" "$(head -c 300 "$ANALYZE_OUT")"
        fi
        if [ "$LLM_BACKEND" = "gemini" ] && [ "${STRENGTHS:-0}" -lt 1 ]; then
            fail "Gemini active but final_summary.strengths is empty" "Check Gemini auth / quota / schema validation"
        fi
    fi
    rm -f "$ANALYZE_OUT"
fi

# ── Test 3: frontend root reachable ────────────────────────────────────────
info "3. frontend root"
FRONT_CODE="$(curl -s -o /dev/null --max-time 15 -w "%{http_code}" "${FRONTEND}/")"
if [ "$FRONT_CODE" = "200" ]; then
    ok "frontend → 200"
else
    fail "frontend returned HTTP $FRONT_CODE" "Check Vercel deployment status and NEXT_PUBLIC_API_BASE_URL"
fi

# ── Test 4: CORS preflight from frontend origin ────────────────────────────
info "4. CORS preflight (OPTIONS from $FRONTEND to $BACKEND/analyze)"
CORS_HEADERS="$(curl -fsS -X OPTIONS --max-time 10 \
    -H "Origin: ${FRONTEND}" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: content-type" \
    -D - -o /dev/null \
    "${BACKEND}/analyze" 2>&1)" || true
ALLOW_ORIGIN="$(echo "$CORS_HEADERS" | grep -i '^access-control-allow-origin:' | tr -d '\r')"
if [ -n "$ALLOW_ORIGIN" ]; then
    ok "CORS preflight allowed: $ALLOW_ORIGIN"
else
    fail "CORS preflight did not return Access-Control-Allow-Origin" "Add ${FRONTEND} to TALENTALIGN_CORS_ORIGINS on the backend"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo
echo "==============================================================="
printf " summary: ${GREEN}%d passed${NC}, ${RED}%d failed${NC}\n" "$PASS" "$FAIL"
echo "==============================================================="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
