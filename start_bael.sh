#!/bin/bash
# BAEL Start Script - Starts both API and UI servers

set -e

BAEL_DIR="/Volumes/SSD320/BaelTheLordOfAll-AI"
UI_TEMP="/Users/thealchemist/bael-ui-temp"

echo "🔥 Starting Ba'el - The Lord of All 🔥"
echo "========================================"

# Kill any existing processes
echo "Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

# Copy latest UI files to temp
echo "Syncing UI files..."
cp -R "$BAEL_DIR/ui/web/src" "$UI_TEMP/" 2>/dev/null || true
cp "$BAEL_DIR/ui/web/vite.config.ts" "$UI_TEMP/" 2>/dev/null || true
cp "$BAEL_DIR/ui/web/public/"* "$UI_TEMP/public/" 2>/dev/null || true

# Start API server
echo "Starting API server on port 8000..."
cd "$BAEL_DIR"
"$BAEL_DIR/.venv/bin/python" -m uvicorn api.server:app --port 8000 --host 0.0.0.0 &
API_PID=$!
echo "API PID: $API_PID"

# Wait for API to be ready
echo "Waiting for API to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API is ready!"
        break
    fi
    sleep 1
done

# Start UI server
echo "Starting UI server on port 3000..."
cd "$UI_TEMP"
/opt/homebrew/bin/npm run dev &
UI_PID=$!
echo "UI PID: $UI_PID"

echo ""
echo "========================================"
echo "🔥 Ba'el is awakening..."
echo ""
echo "  API: http://localhost:8000"
echo "  UI:  http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo "========================================"

# Wait for either process to exit
wait $API_PID $UI_PID
