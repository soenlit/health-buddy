import os
from google import genai
from sqlalchemy import func
from database import SessionLocal, HealthMetric, Workout
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


def get_sleep_stats(days=7):
    """Query sleep-related metrics from the health_metrics table."""
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)

        # Sleep stage metric types exported by Health Auto Export
        sleep_stage_types = {
            'sleep_deep': 'deep_sleep_minutes',
            'sleep_rem': 'rem_sleep_minutes',
            'sleep_core': 'core_sleep_minutes',
            'sleep_awake': 'awake_minutes',
            'sleep_analysis': 'total_sleep_minutes',
        }

        result = {}
        for metric_type, label in sleep_stage_types.items():
            daily_sums = db.query(
                func.date_trunc('day', HealthMetric.timestamp).label('day'),
                func.sum(HealthMetric.value).label('daily_val')
            ).filter(
                HealthMetric.metric_type == metric_type,
                HealthMetric.timestamp >= since
            ).group_by('day').all()

            if daily_sums:
                vals = [float(d.daily_val) for d in daily_sums]
                result[label] = {
                    "daily_avg_minutes": round(sum(vals) / len(vals), 1),
                    "days_tracked": len(vals),
                }

        return result if result else None
    finally:
        db.close()


def get_workout_stats(days=7):
    """Query recent workouts from the workouts table."""
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)

        workouts = db.query(Workout).filter(
            Workout.start_timestamp >= since
        ).order_by(Workout.start_timestamp.desc()).all()

        if not workouts:
            return None

        workout_list = []
        for w in workouts:
            entry = {
                "type": w.workout_type,
                "date": w.start_timestamp.strftime("%Y-%m-%d %H:%M") if w.start_timestamp else None,
                "duration_minutes": w.duration_minutes,
                "active_calories": w.active_calories,
                "avg_heart_rate": w.avg_heart_rate,
                "max_heart_rate": w.max_heart_rate,
            }
            workout_list.append(entry)

        # Aggregate summary
        total_workouts = len(workouts)
        type_counts = {}
        for w in workouts:
            type_counts[w.workout_type] = type_counts.get(w.workout_type, 0) + 1

        return {
            "total_workouts": total_workouts,
            "workout_types": type_counts,
            "sessions": workout_list,
        }
    finally:
        db.close()


def generate_insight():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Missing GEMINI_API_KEY"

    stats = get_recent_stats()
    sleep_stats = get_sleep_stats()
    workout_stats = get_workout_stats()

    if not stats and not sleep_stats and not workout_stats:
        return "还没攒够数据，再运动两天吧。"

    client = genai.Client(api_key=api_key)

    # Build a rich, multi-dimensional context block
    data_sections = []

    if stats:
        data_sections.append(f"【每日活动指标（近7天均值）】\n{stats}")

    if sleep_stats:
        data_sections.append(f"【睡眠数据（近7天）】\n{sleep_stats}")
    else:
        data_sections.append("【睡眠数据】暂无数据。")

    if workout_stats:
        data_sections.append(f"【训练记录（近7天，共{workout_stats['total_workouts']}次）】\n{workout_stats}")
    else:
        data_sections.append("【训练记录】近7天无记录。")

    combined_data = "\n\n".join(data_sections)

    prompt = f"""
    你是一个毒舌但专业的健康助手 Bobo。以下是用户近 7 天的多维度健康数据：

    {combined_data}

    请根据上述数据给出一份综合分析报告（250字以内）。
    要求：
    1. 风格要专业、简洁、带点幽默或微毒舌。
    2. 必须进行跨维度分析——例如：睡眠质量如何影响当天训练表现，心率区间能否反映训练强度，步数和训练是否互补。
    3. 如果数据显示问题（睡眠不足、训练过少、心率异常），直接指出，别客气。
    4. 如果有训练记录，请评价训练强度（结合心率区间与消耗卡路里），并与睡眠和恢复情况关联。
    5. 最后给出下周一条硬核、可执行的建议。
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents=prompt
        )
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
