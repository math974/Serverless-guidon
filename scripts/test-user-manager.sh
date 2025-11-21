#!/usr/bin/env bash

set -euo pipefail

# Test script for user-manager service
# Usage: ./test-user-manager.sh [BASE_URL]
# If BASE_URL is not provided, uses gcloud functions call (authenticated)

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${REGION:=europe-west1}"
: "${FUNCTION_NAME:=user-manager}"

if [ $# -eq 0 ]; then
    BASE_URL=$(gcloud functions describe "${FUNCTION_NAME}" --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)" 2>/dev/null || echo "")
    if [ -z "${BASE_URL}" ]; then
        echo "Error: user-manager service not found."
        exit 1
    fi
else
    BASE_URL="$1"
fi

# Get authentication token
echo "Getting authentication token..."
AUTH_TOKEN=$(gcloud auth print-identity-token --project="${PROJECT_ID}" 2>/dev/null || echo "")

if [ -z "${AUTH_TOKEN}" ]; then
    echo "Warning: Could not get auth token. Some tests may fail with 403."
    echo "Run: gcloud auth login"
fi

echo "Testing user-manager service"
echo "Base URL: ${BASE_URL}"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5

    echo -n "Testing ${description}... "

    local correlation_id="test-$(date +%s)"
    local headers=(
        "Content-Type: application/json"
        "X-Correlation-ID: ${correlation_id}"
    )

    if [ ! -z "${AUTH_TOKEN}" ]; then
        headers+=("Authorization: Bearer ${AUTH_TOKEN}")
    fi

    local header_args=""
    for header in "${headers[@]}"; do
        header_args="${header_args} -H \"${header}\""
    done

    local temp_file=$(mktemp)
    local http_code_file=$(mktemp)
    if [ -z "${data}" ]; then
        eval curl -s -w "%{http_code}" -X "${method}" "${BASE_URL}${endpoint}" ${header_args} -o "${temp_file}" -D "${http_code_file}" 2>/dev/null || echo "000" > "${http_code_file}"
    else
        eval curl -s -w "%{http_code}" -X "${method}" "${BASE_URL}${endpoint}" ${header_args} -d "'${data}'" -o "${temp_file}" -D "${http_code_file}" 2>/dev/null || echo "000" > "${http_code_file}"
    fi

    # Extract HTTP code from response headers
    http_code=$(head -n1 "${http_code_file}" | grep -oE 'HTTP/[0-9.]+ [0-9]{3}' | grep -oE '[0-9]{3}' || echo "000")
    if [ "${http_code}" = "000" ]; then
        # Fallback: try to get from curl's -w output (last 3 digits)
        http_code=$(tail -c 3 "${temp_file}" 2>/dev/null | grep -oE '[0-9]{3}' || echo "000")
        # Remove HTTP code from body if it was appended
        if [ "${#body}" -gt 3 ]; then
            body=$(head -c -3 "${temp_file}" 2>/dev/null || cat "${temp_file}")
        fi
    else
        body=$(cat "${temp_file}")
    fi
    rm -f "${temp_file}" "${http_code_file}"

    if [ "${http_code}" = "${expected_status}" ]; then
        echo -e "${GREEN}✓${NC} (${http_code})"
        if [ ! -z "${body}" ] && [ "${body}" != "null" ] && [ "${body}" != "{}" ]; then
            echo "${body}" | python3 -m json.tool 2>/dev/null | head -20 || echo "  ${body}"
        fi
    else
        echo -e "${RED}✗${NC} Expected ${expected_status}, got ${http_code}"
        if [ ! -z "${body}" ]; then
            echo "  Response: ${body}" | head -5
        fi
    fi
    echo ""
}

# Test user ID
TEST_USER_ID="test-user-$(date +%s)"
TEST_USERNAME="TestUser"

echo "=== Health Check ==="
test_endpoint "GET" "/health" "" "200" "Health check"

echo "=== User Management ==="
test_endpoint "POST" "/api/users" "{\"user_id\":\"${TEST_USER_ID}\",\"username\":\"${TEST_USERNAME}\"}" "200" "Create user"

test_endpoint "GET" "/api/users/${TEST_USER_ID}" "" "200" "Get user"

test_endpoint "POST" "/api/users/${TEST_USER_ID}/increment" "{\"command\":\"draw\"}" "200" "Increment usage"

test_endpoint "GET" "/api/users/${TEST_USER_ID}" "" "200" "Get user (after increment)"

test_endpoint "PUT" "/api/users/${TEST_USER_ID}/premium" "{\"is_premium\":true}" "200" "Set premium"

test_endpoint "GET" "/api/users/${TEST_USER_ID}" "" "200" "Get user (premium)"

echo "=== Rate Limiting ==="
test_endpoint "POST" "/api/rate-limit/check" "{\"user_id\":\"${TEST_USER_ID}\",\"command\":\"draw\",\"is_premium\":true}" "200" "Check rate limit (premium)"

test_endpoint "GET" "/api/rate-limit/${TEST_USER_ID}?command=draw" "" "200" "Get rate limit info"

# Test multiple rate limit checks
echo "Testing rate limit enforcement..."
for i in {1..15}; do
    test_endpoint "POST" "/api/rate-limit/check" "{\"user_id\":\"${TEST_USER_ID}\",\"command\":\"draw\",\"is_premium\":false}" "200" "Rate limit check ${i}/15"
done

test_endpoint "POST" "/api/users/${TEST_USER_ID}/ban" "{\"reason\":\"Test ban\"}" "200" "Ban user"

test_endpoint "POST" "/api/rate-limit/check" "{\"user_id\":\"${TEST_USER_ID}\",\"command\":\"draw\"}" "403" "Check rate limit (banned user)"

test_endpoint "POST" "/api/users/${TEST_USER_ID}/unban" "" "200" "Unban user"

test_endpoint "DELETE" "/api/rate-limit/${TEST_USER_ID}?command=draw" "" "200" "Reset rate limits"

echo "=== Statistics ==="
test_endpoint "GET" "/api/stats/users" "" "200" "Get total users"

test_endpoint "GET" "/api/stats/active?hours=24" "" "200" "Get active users (24h)"

test_endpoint "GET" "/api/stats/active?hours=168" "" "200" "Get active users (7d)"

test_endpoint "GET" "/api/stats/leaderboard?limit=10" "" "200" "Get leaderboard"

echo "=== Test Summary ==="
echo "Test user ID: ${TEST_USER_ID}"
echo "All tests completed"

