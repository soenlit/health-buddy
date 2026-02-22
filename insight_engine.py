import os
import google.generativeai as genai
from sqlalchemy import func
from database import SessionLocal, HealthMetric
from datetime import datetime, timedelta
import requests
import logging

logger = logging.getLogger(__name__)

def get_recent_stats(days=7):
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)
        # 聚合过去几天的核心数据
        stats = db.query(
            HealthMetric.metric_type,
            func.avg(HealthMetric.value).label('avg_val'),
            func.max(HealthMetric.value).label('max_val'),
            func.min(HealthMetric.value).label('min_val')
        ).filter(HealthMetric.timestamp >= since).group_by(HealthMetric.metric_type).all()
        
        result = {}
        for s in stats:
            result[s.metric_type] = {
                "avg": round(float(s.avg_val), 2),
                "max": float(s.max_val),
                "min": float(s.min_val)
            }
        return result
    finally:
        db.close()

def generate_insight():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Missing GEMINI_API_KEY"
    
    stats = get_recent_stats()
    if not stats:
        return "还没攒够数据，再运动两天吧。"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    你是一个毒舌但专业的健康助手 Bobo。以下是用户最近 7 天的健康数据：
    {stats}
    
    请根据这些数据给出一份简短的分析报告（200字以内）。
    要求：
    1. 风格要专业、简洁、带点幽默或微毒舌。
    2. 如果数据太差（比如步数太少、睡眠不足），直接点出来，别客气。
    3. 最后给一条下周的硬核建议。
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"AI 离家出走了: {e}"

def send_to_discord(content):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL not set")
        return
    
    payload = {
        "embeds": [{
            "title": "🤖 Bobo 的健康毒舌报告",
            "description": content,
            "color": 0x00ff00,
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    requests.post(webhook_url, json=payload)

if __name__ == "__main__":
    insight = generate_insight()
    print(f"Generated Insight: {insight}")
    send_to_discord(insight)
