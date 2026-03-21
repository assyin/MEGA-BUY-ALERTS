#!/bin/bash
# =============================================================================
# MEGA BUY - Batch Backtest Runner
# Usage: ./run_backtests.sh [v4|v5|v6|all]
# =============================================================================

API_URL="http://localhost:9001"
START_DATE="2026-02-01"
END_DATE="2026-03-16"

# Fichier contenant la liste des paires
PAIRS_FILE="/home/assyin/MEGA-BUY-BOT/Backtest-paire-backtest.md"

# Lecture dynamique des paires depuis le fichier
if [ ! -f "$PAIRS_FILE" ]; then
    echo -e "${RED}Erreur: Fichier $PAIRS_FILE introuvable${NC}"
    exit 1
fi

# Lire les paires (une par ligne, ignorer les lignes vides et commentaires)
mapfile -t PAIRS < <(grep -v '^#' "$PAIRS_FILE" | grep -v '^$' | tr -d '\r')

TOTAL=${#PAIRS[@]}

if [ $TOTAL -eq 0 ]; then
    echo -e "${RED}Erreur: Aucune paire trouvée dans $PAIRS_FILE${NC}"
    exit 1
fi

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Compteurs
SUCCESS=0
FAILED=0

run_backtest() {
    local symbol=$1
    local version=$2
    local index=$3

    echo -ne "${BLUE}[$index/$TOTAL]${NC} $symbol (${version})... "

    # 1. Lancer le backtest
    response=$(curl -s -X POST "$API_URL/api/backtests" \
        -H "Content-Type: application/json" \
        -d "{\"symbol\": \"$symbol\", \"start_date\": \"$START_DATE\", \"end_date\": \"$END_DATE\", \"strategy_version\": \"$version\"}")

    # Extraire task_id
    task_id=$(echo "$response" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)

    if [ -z "$task_id" ]; then
        echo -e "${RED}✗ Failed to start${NC}"
        ((FAILED++))
        return
    fi

    # 2. Attendre la fin du backtest
    local max_wait=300  # 5 minutes max
    local waited=0
    local status="running"

    while [ "$status" = "running" ] || [ "$status" = "queued" ]; do
        sleep 3
        ((waited+=3))

        status_response=$(curl -s "$API_URL/api/backtests/status/$task_id")
        status=$(echo "$status_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

        # Afficher progression
        progress=$(echo "$status_response" | grep -o '"progress":"[^"]*"' | cut -d'"' -f4)
        echo -ne "\r${BLUE}[$index/$TOTAL]${NC} $symbol (${version})... ${CYAN}$progress${NC}          "

        if [ $waited -ge $max_wait ]; then
            echo -e "\r${BLUE}[$index/$TOTAL]${NC} $symbol (${version})... ${RED}✗ Timeout${NC}          "
            ((FAILED++))
            return
        fi
    done

    # 3. Afficher le résultat
    if [ "$status" = "completed" ]; then
        run_id=$(echo "$status_response" | grep -o '"run_id":[0-9]*' | grep -o '[0-9]*')
        echo -e "\r${BLUE}[$index/$TOTAL]${NC} $symbol (${version})... ${GREEN}✓ Completed (ID:$run_id)${NC}          "
        ((SUCCESS++))
    else
        error=$(echo "$status_response" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        echo -e "\r${BLUE}[$index/$TOTAL]${NC} $symbol (${version})... ${RED}✗ $error${NC}          "
        ((FAILED++))
    fi
}

run_version() {
    local version=$1
    SUCCESS=0
    FAILED=0

    echo ""
    echo "=============================================="
    echo -e "${YELLOW}  BACKTEST $version - $TOTAL paires${NC}"
    echo "  Period: $START_DATE → $END_DATE"
    echo "=============================================="
    echo ""

    local i=1
    for pair in "${PAIRS[@]}"; do
        run_backtest "$pair" "$version" "$i"
        ((i++))
    done

    echo ""
    echo -e "${GREEN}✓ $version terminé! Success: $SUCCESS | Failed: $FAILED${NC}"
}

show_help() {
    echo "Usage: $0 [v2|v4|v5|v6|all]"
    echo ""
    echo "Options:"
    echo "  v2      Run V2 backtests only"
    echo "  v4      Run V4 backtests only"
    echo "  v5      Run V5 backtests only"
    echo "  v6      Run V6 backtests only"
    echo "  all     Run all versions (V2, V4, V5, V6)"
    echo ""
    echo "Pairs: $TOTAL"
    echo "Period: $START_DATE → $END_DATE"
    echo ""
    echo "Examples:"
    echo "  $0 v4"
    echo "  $0 all"
    echo "  nohup $0 all > backtest_log.txt 2>&1 &"
}

# Vérifier que l'API est accessible
check_api() {
    echo -n "Checking API connection... "
    if curl -s "$API_URL/api/backtests" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo "Error: Cannot connect to API at $API_URL"
        echo "Make sure the API is running: systemctl --user status mega-buy-api"
        exit 1
    fi
}

# Main
case "${1:-help}" in
    v2)
        check_api
        run_version "v2"
        ;;
    v4)
        check_api
        run_version "v4"
        ;;
    v5)
        check_api
        run_version "v5"
        ;;
    v6)
        check_api
        run_version "v6"
        ;;
    all)
        check_api
        run_version "v2"
        run_version "v4"
        run_version "v5"
        run_version "v6"
        ;;
    *)
        show_help
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo -e "${GREEN}  TOUS LES BACKTESTS TERMINÉS!${NC}"
echo "  Voir les résultats: http://localhost:9000"
echo "=============================================="
