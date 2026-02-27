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
        
        # 定义需要统计的指标类别
        # 1. 累加型指标 (Activity)
        metrics_to_sum = [
            'step_count', 
            'walking_running_distance', 
            'active_energy', 
            'flights_climbed',
            'swimming_distance',
            'cycling_distance'
        ]
        
        # 2. 平均/波动型指标 (Vitals)
        metrics_to_avg = [
            'heart_rate',
            'resting_heart_rate',
            'blood_oxygen_saturation',
            'respiratory_rate',
            'body_temperature'
        ]

        # 3. 睡眠型指标 (Sleep)
        # Health Auto Export 的睡眠数据通常以分钟为单位
        metrics_sleep = [
            'sleep_analysis'
        ]

        result = {}
        
        # 处理累加指标
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

        # 处理平均指标
        for m_type in metrics_to_avg:
            avg_stats = db.query(
                func.avg(HealthMetric.value).label('avg_val'),
                func.min(HealthMetric.value).label('min_val'),
                func.max(HealthMetric.value).label('max_val')
            ).filter(
                HealthMetric.metric_type == m_type,
                HealthMetric.timestamp >= since
            ).first()
            
            if avg_stats and avg_stats.avg_val:
                result[m_type] = {
                    "avg": round(float(avg_stats.avg_val), 2),
                    "range": f"{round(float(avg_stats.min_val), 2)} - {round(float(avg_stats.max_day), 2)}" if hasattr(avg_stats, 'max_day') else f"{round(float(avg_stats.min_val), 2)} - {round(float(avg_stats.max_val), 2)}"
                }

        # 处理睡眠数据 (假设单位是小时或分钟，需要根据实际数据清洗判断)
        for m_type in metrics_sleep:
            sleep_stats = db.query(
                func.date_trunc('day', HealthMetric.timestamp).label('day'),
                func.sum(HealthMetric.value).label('daily_sleep')
            ).filter(
                HealthMetric.metric_type == m_type,
                HealthMetric.timestamp >= since
            ).group_by('day').all()
            
            if sleep_stats:
                vals = [float(d.daily_sleep) for d in sleep_stats]
                result['sleep'] = {
                    "avg_hours": round((sum(vals) / len(vals)) / 60, 2) if sum(vals) > 500 else round(sum(vals) / len(vals), 2), # 简单逻辑判断单位
                    "min_hours": round(min(vals) / 60, 2) if min(vals) > 100 else min(vals)
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
    # 使用最新的 gemini-2.0-flash 或指定模型
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    你是一个毒舌但极致专业的健康教练 Bobo，你的任务是分析用户过去 7 天的 Apple Health 数据并给出一份令其“警醒”的报告。
    
    ### 原始数据:
    {stats}
    
    ### 任务要求:
    1. **多维度剖析**: 不要只盯着步数。要把活动量 (Activity)、心率/血氧 (Vitals) 和睡眠 (Sleep) 结合起来看。
       - 比如：如果步数很多但睡眠极少，指出他在透支身体。
       - 比如：如果心率偏高且运动量为 0，质疑他是不是压力太大或者太虚。
    2. **毒舌风格**: 语气要犀利，像是一个严厉的私人教练。禁止使用“做得不错”、“请保持”这种废话。
    3. **数字驱动**: 引用具体的数字来支撑你的羞辱或建议。
    4. **字数限制**: 250字以内，保持极高的信息密度。
    5. **硬核建议**: 最后给一条非常具体的、下周必须执行的改进动作。
    
    请开始你的毒舌表演。
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
            "title": "🤖 Bobo 的深度健康审计",
            "description": content,
            "color": 0xFF0000, # 警示红
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "由 Gemini 2.0 Flash 驱动 | Health Buddy AI"}
        }]
    }
    requests.post(webhook_url, json=payload)

if __name__ == "__main__":
    insight = generate_insight()
    print(f"Generated Insight: {insight}")
    send_to_discord(insight)
