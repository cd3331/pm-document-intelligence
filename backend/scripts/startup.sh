#!/bin/bash
set -e

echo "========================================="
echo "PM Document Intelligence - Startup"
echo "========================================="

# Run database migrations
echo "Running database migrations..."
python3 scripts/run_migrations.py

if [ $? -ne 0 ]; then
    echo "❌ Database migrations failed!"
    exit 1
fi

echo "✅ Database migrations completed"
echo "========================================="

# Start the application
echo "Starting application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
