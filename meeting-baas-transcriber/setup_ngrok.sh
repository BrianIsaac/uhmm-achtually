#!/bin/bash

echo "================================================================"
echo "NGROK SETUP - GET YOUR AUTH TOKEN"
echo "================================================================"
echo ""
echo "Follow these steps:"
echo ""
echo "1. Open this link in your browser:"
echo "   https://dashboard.ngrok.com/get-started/your-authtoken"
echo ""
echo "2. Sign up (it's free, takes 30 seconds)"
echo "   - Use Google/GitHub or email"
echo ""
echo "3. Copy your auth token (looks like: 2abc...xyz)"
echo ""
echo "4. Paste it below when prompted"
echo ""
echo "================================================================"
echo ""

read -p "Have you opened the link? Press Enter when ready..."
read -p "Paste your ngrok auth token here: " NGROK_TOKEN

if [ -z "$NGROK_TOKEN" ]; then
    echo "❌ No token provided. Exiting."
    exit 1
fi

echo ""
echo "Setting up ngrok..."

# Configure ngrok with the token
~/.local/bin/ngrok config add-authtoken "$NGROK_TOKEN"

# Add to .env file
if grep -q "NGROK_AUTH_TOKEN" .env; then
    sed -i "s/^NGROK_AUTH_TOKEN=.*/NGROK_AUTH_TOKEN=$NGROK_TOKEN/" .env
    echo "✅ Updated NGROK_AUTH_TOKEN in .env"
else
    echo "NGROK_AUTH_TOKEN=$NGROK_TOKEN" >> .env
    echo "✅ Added NGROK_AUTH_TOKEN to .env"
fi

echo ""
echo "✅ Ngrok configured successfully!"
echo ""
echo "Next steps:"
echo "1. Run: uv run python run_server.py --ngrok"
echo "2. Copy the webhook URL"
echo "3. Run: uv run python create_bot.py <zoom_url> <webhook_url>"
echo ""
