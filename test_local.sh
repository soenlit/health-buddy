#!/bin/bash
# 自动在本地启动数据库并运行调试
export IS_LOCAL_DEV=true

echo "🚀 Starting local database..."
docker compose up -d db

echo "⏳ Waiting for DB to be ready..."
sleep 3

echo "📊 Running Insight Engine Debug..."
uv run debug_insight.py
