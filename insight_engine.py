import os
import google.generativeai as genai
from sqlalchemy import func
from database import SessionLocal, HealthMetric
from datetime import datetime, timedelta
import requests
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

def get_recent_stats(days=7):
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)
        
        # 针对步数、距离等累加型指标，先进行按天求和，再算平均
        # 针对心率等指标，算日均波动
        metrics_to_sum = ['step_count', 'walking_running_distance', 'flights_climbed', 'active_energy']
        
        result = {}
        for m_type in metrics_to_sum:
            daily_sums = db.query(
                func.date_trunc('day', HealthMetric.timestamp).label('day'),
                func.sum(HealthMetric.value).label('daily_val')
            ).filter(
                HealthMetric.metric_type == m_type,
                HealthMetric.timestamp >= since
            ).group_by('day').all()
            
            if daily_sums:
                vals = [float(d.daily_val) for d in daily_sums]
                result[m_type] = {
                    "daily_avg": round(sum(vals) / len(vals), 2),
                    "weekly_total": round(sum(vals), 2),
                    "max_day": max(vals)
                }
        
        # 针对心率这种不需要求和的，保持原样或取日均值
        hr_stats = db.query(
            func.avg(HealthMetric.value).label('avg_val')
        ).filter(
            HealthMetric.metric_type == 'heart_rate',
            HealthMetric.timestamp >= since
        ).first()
        
        if hr_stats and hr_stats.avg_val:
            result['heart_rate'] = {"avg": round(float(hr_stats.avg_val), 2)}
            
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
    model = genai.GenerativeModel('gemini-3-pro-preview')
    
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
