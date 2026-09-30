#!/usr/bin/env bash
set -euo pipefail

# =====================================================================
# SentinelDoc Single-Command Automated Verification & Test Runner
# Usage: ./run_tests.sh [--tier1] [--tier2] [--tier3] [--tier4] [--false-positives] [--coverage]
# =====================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ANSI Color Codes
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}========================================================${NC}"
echo -e "${CYAN}${BOLD}   SentinelDoc Automated Verification & Test Harness    ${NC}"
echo -e "${BLUE}${BOLD}========================================================${NC}"

# Step 1: Detect and activate virtual environment
if [[ -f ".venv/bin/activate" ]]; then
    echo -e "${GREEN}[+] Activating virtual environment (.venv)...${NC}"
    source .venv/bin/activate
elif [[ -f "venv/bin/activate" ]]; then
    echo -e "${GREEN}[+] Activating virtual environment (venv)...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}[!] Warning: No .venv found. Using current PATH python/pytest.${NC}"
fi

# Step 2: Ensure pytest exists
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}[-] Error: 'pytest' not found in PATH or active virtual environment.${NC}"
    echo -e "    Please run: pip install -r requirements.txt"
    exit 1
fi

# Step 3: Parse arguments and construct pytest flags
EXTRA_ARGS=()
SELECTED_TIERS=""

for arg in "$@"; do
    case "$arg" in
        --tier1)
            EXTRA_ARGS+=("-m" "tier1")
            SELECTED_TIERS="${SELECTED_TIERS} [Tier 1: Features]"
            ;;
        --tier2)
            EXTRA_ARGS+=("-m" "tier2")
            SELECTED_TIERS="${SELECTED_TIERS} [Tier 2: Boundaries]"
            ;;
        --tier3)
            EXTRA_ARGS+=("-m" "tier3")
            SELECTED_TIERS="${SELECTED_TIERS} [Tier 3: Combinations]"
            ;;
        --tier4)
            EXTRA_ARGS+=("-m" "tier4")
            SELECTED_TIERS="${SELECTED_TIERS} [Tier 4: Scenarios]"
            ;;
        --false-positives)
            EXTRA_ARGS+=("-m" "false_positive")
            SELECTED_TIERS="${SELECTED_TIERS} [False-Positive Controls]"
            ;;
        --coverage)
            EXTRA_ARGS+=("--cov=app" "--cov-report=term-missing")
            ;;
        *)
            EXTRA_ARGS+=("$arg")
            ;;
    esac
done

if [[ -z "$SELECTED_TIERS" ]]; then
    SELECTED_TIERS="[Full Suite: All 4 Tiers + False-Positive Controls]"
fi

echo -e "${CYAN}[+] Selected Target: ${BOLD}${SELECTED_TIERS}${NC}"
echo -e "${CYAN}[+] Executing Pytest Runner...${NC}"
echo ""

# Step 4: Execute pytest with exit code propagation
set +e
pytest -v -s ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} tests/
EXIT_CODE=$?
set -e

echo ""
echo -e "${BLUE}${BOLD}========================================================${NC}"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}${BOLD}   [PASSED] All SentinelDoc Verification Tests Passed!   ${NC}"
    echo -e "${GREEN}   Exit Code: 0${NC}"
else
    echo -e "${RED}${BOLD}   [FAILED] Verification tests encountered failures.   ${NC}"
    echo -e "${RED}   Exit Code: ${EXIT_CODE}${NC}"
fi
echo -e "${BLUE}${BOLD}========================================================${NC}"

exit $EXIT_CODE
