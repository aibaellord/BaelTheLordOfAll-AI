#!/bin/bash
# Run BAEL UI development server
# Uses globally installed vite to avoid local dependency issues

export PATH="/opt/homebrew/bin:$PATH"
cd "$(dirname "$0")"

echo "🔥 Starting BAEL UI..."
echo "📦 Installing dependencies (this may take a moment)..."

# Install dependencies if needed
if [ ! -d "node_modules/react" ]; then
    /opt/homebrew/bin/npm install --prefer-offline --no-audit 2>&1 || true
fi

# Run vite using global installation
echo "🚀 Launching development server..."
exec /opt/homebrew/bin/vite --host 0.0.0.0 --port 5173
