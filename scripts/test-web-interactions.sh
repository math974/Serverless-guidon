#!/usr/bin/env bash

# Test script for /web/interactions endpoint
# Usage:
#   GATEWAY_URL=https://guidon-60g097ca.ew.gateway.dev ./test-web-interactions.sh
#   Or use the default gateway URL

: "${GATEWAY_URL:=https://guidon-60g097ca.ew.gateway.dev}"

echo "Testing /web/interactions endpoint"
echo "Gateway URL: ${GATEWAY_URL}"
echo ""

# Test 1: Ping command (simple, immediate response)
echo "=========================================="
echo "Test 1: Ping command (simple)"
echo "=========================================="
curl -i -X POST "${GATEWAY_URL}/web/interactions" \
  -H 'Content-Type: application/json' \
  -d '{
    "command": "ping"
  }'
echo ""
echo ""

# Test 2: Hello command (simple, immediate response)
echo "=========================================="
echo "Test 2: Hello command (simple)"
echo "=========================================="
curl -i -X POST "${GATEWAY_URL}/web/interactions" \
  -H 'Content-Type: application/json' \
  -d '{
    "command": "hello"
  }'
echo ""
echo ""

# Test 3: Help command (simple, immediate response)
echo "=========================================="
echo "Test 3: Help command (simple)"
echo "=========================================="
curl -i -X POST "${GATEWAY_URL}/web/interactions" \
  -H 'Content-Type: application/json' \
  -d '{
    "command": "help"
  }'
echo ""
echo ""

# Test 4: Draw command (complex, goes to Pub/Sub)
echo "=========================================="
echo "Test 4: Draw command (complex, async)"
echo "=========================================="
curl -i -X POST "${GATEWAY_URL}/web/interactions" \
  -H 'Content-Type: application/json' \
  -d '{
    "command": "draw",
    "options": [
      {"name": "x", "value": 10},
      {"name": "y", "value": 20},
      {"name": "color", "value": "#FF0000"}
    ],
    "token": "test-token-123",
    "application_id": "web-client"
  }'
echo ""
echo ""

# Test 5: Snapshot command (complex, goes to Pub/Sub)
echo "=========================================="
echo "Test 5: Snapshot command (complex, async)"
echo "=========================================="
curl -i -X POST "${GATEWAY_URL}/web/interactions" \
  -H 'Content-Type: application/json' \
  -d '{
    "command": "snapshot",
    "token": "test-token-456",
    "application_id": "web-client"
  }'
echo ""
echo ""

# Test 6: Invalid command (should return error)
echo "=========================================="
echo "Test 6: Invalid command (error handling)"
echo "=========================================="
curl -i -X POST "${GATEWAY_URL}/web/interactions" \
  -H 'Content-Type: application/json' \
  -d '{
    "command": "invalid_command"
  }'
echo ""
echo ""

# Test 7: Missing command (should return 400)
echo "=========================================="
echo "Test 7: Missing command (error handling)"
echo "=========================================="
curl -i -X POST "${GATEWAY_URL}/web/interactions" \
  -H 'Content-Type: application/json' \
  -d '{}'
echo ""
echo ""

echo "=========================================="
echo "All tests completed!"
echo "=========================================="
echo ""
echo "Expected responses:"
echo "  - ping, hello, help: 200 OK (immediate response)"
echo "  - draw, snapshot: 202 Accepted (processing)"
echo "  - invalid/missing: 400 Bad Request"
echo ""
echo "Note: For complex commands (draw, snapshot), the response"
echo "      will be processed asynchronously via Pub/Sub."

