#!/bin/bash
# 自动在本地启动数据库并运行调试
export IS_LOCAL_DEV=true

echo "🚀 Starting local database..."
docker-compose up -d db

echo "⏳ Waiting for DB to be ready..."
sleep 5

echo "🏗️ Initializing Database Schema..."
uv run python -c "from database import init_db; init_db()"

echo "📊 Running Insight Engine Debug..."
uv run debug_insight.py
