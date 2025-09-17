#!/bin/bash
# Test runner script for file upload functionality

echo "Starting JSON Compare API server..."
uv run python -m src.api &
SERVER_PID=$!

# Wait for server to start
sleep 3

echo "Installing Playwright browsers (if needed)..."
uv run playwright install chromium 2>/dev/null || true

echo "Running Playwright tests..."
uv run pytest tests/test_upload_playwright.py -v

TEST_RESULT=$?

echo "Stopping API server..."
kill $SERVER_PID 2>/dev/null

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed."
fi

exit $TEST_RESULT