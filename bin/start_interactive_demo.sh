#!/bin/bash
# Quick start script for interactive demo

echo "🚀 Setting up Interactive Demo with Real Videos"
echo ""

# Check if in backend directory
if [ ! -f "main.py" ]; then
    echo "❌ Please run this from the olleey-backend directory"
    exit 1
fi

echo "1. Resetting demo data..."
python3 scripts/setup_interactive_demo.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Setup failed. Make sure:"
    echo "   - Backend server is NOT running (stop it first)"
    echo "   - Firebase is configured"
    echo "   - Demo user exists"
    exit 1
fi

echo ""
echo "2. Starting backend server..."
python3 dev_server.py &
BACKEND_PID=$!

echo "   Backend PID: $BACKEND_PID"
echo "   Waiting for server to start..."
sleep 5

echo ""
echo "=" * 70
echo "🎉 Interactive Demo Ready!"
echo "=" * 70
echo ""
echo "Next Steps:"
echo "  1. Start frontend: cd ../olleey-web && npm run dev"
echo "  2. Open browser: http://localhost:3000"
echo "  3. Login with: demo@olleey.com / password"
echo "  4. Navigate to: All Media page"
echo "  5. Find your real video and test the interactive controls!"
echo ""
echo "Demo Controls Available:"
echo "  • Processing → Draft (click '→ Draft')"
echo "  • Draft → Live (click '✓ Approve')"
echo "  • Draft → Processing (click '↻ Reprocess')"
echo "  • Live → Draft (click '← Unpublish')"
echo ""
echo "Backend running on: http://localhost:8000"
echo "To stop backend: kill $BACKEND_PID"
echo ""
