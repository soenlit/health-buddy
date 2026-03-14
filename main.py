import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Security, Depends, BackgroundTasks
from fastapi.security.api_key import APIKeyQuery, APIKey
from pydantic import BaseModel
from database import SessionLocal, HealthMetric, Workout, init_db
from insight_engine import generate_insight, send_to_discord

# 初始化数据库
init_db()

app = FastAPI(title="Health Buddy API")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY_NAME = "token"
webhook_token = os.getenv("WEBHOOK_TOKEN", "super-secret-token")
api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Depends(api_key_query)):
    logger.info(f"Checking token. Received token length: {len(api_key) if api_key else 0}")
    if api_key == webhook_token:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid token.")

def _parse_timestamp(ts_str: str) -> datetime:
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")


def process_health_data(payload: Dict[str, Any]):
    db = SessionLocal()
    try:
        data = payload.get("data", {})
        metrics = data.get("metrics", [])
        workouts = data.get("workouts", [])

        # Process standard health metrics
        count = 0
        for m in metrics:
            metric_type = m.get("name")
            unit = m.get("units")
            samples = m.get("data", [])

            for sample in samples:
                ts_str = sample.get("date")
                val = sample.get("qty")

                if ts_str and val is not None:
                    ts = _parse_timestamp(ts_str)
                    metric_entry = HealthMetric(
                        timestamp=ts,
                        metric_type=metric_type,
                        value=float(val),
                        unit=unit,
                        raw_data=sample
                    )
                    db.merge(metric_entry)
                    count += 1

        # Process workout data
        workout_count = 0
        for w in workouts:
            start_str = w.get("start")
            end_str = w.get("end")
            if not start_str:
                continue

            start_ts = _parse_timestamp(start_str)
            end_ts = _parse_timestamp(end_str) if end_str else None

            # Duration can be provided in seconds or minutes depending on the export format
            duration_raw = w.get("duration")
            duration_minutes = None
            if duration_raw is not None:
                # Health Auto Export sends duration in seconds
                duration_minutes = round(float(duration_raw) / 60, 2)

            active_cal_raw = w.get("activeEnergyBurned") or w.get("totalEnergy")
            active_calories = active_cal_raw.get("qty") if isinstance(active_cal_raw, dict) else None

            hr = w.get("heartRate") or {}
            avg_heart_rate = hr.get("avg", {}).get("qty")
            max_heart_rate = hr.get("max", {}).get("qty")

            workout_type = w.get("name", "Unknown")
            existing = db.query(Workout).filter(
                Workout.start_timestamp == start_ts,
                Workout.workout_type == workout_type
            ).first()

            if existing:
                existing.end_timestamp = end_ts
                existing.duration_minutes = duration_minutes
                existing.active_calories = active_calories
                existing.avg_heart_rate = avg_heart_rate
                existing.max_heart_rate = max_heart_rate
                existing.raw_data = w
            else:
                db.add(Workout(
                    start_timestamp=start_ts,
                    end_timestamp=end_ts,
                    workout_type=workout_type,
                    duration_minutes=duration_minutes,
                    active_calories=active_calories,
                    avg_heart_rate=avg_heart_rate,
                    max_heart_rate=max_heart_rate,
                    raw_data=w
                ))
            workout_count += 1

        db.commit()
        logger.info(f"Successfully processed {count} metric samples and {workout_count} workouts.")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        db.rollback()
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {"status": "alive", "timestamp": datetime.now()}

@app.post("/api/health/webhook")
async def health_webhook(
    payload: Dict[str, Any], 
    background_tasks: BackgroundTasks,
    token: APIKey = Depends(get_api_key)
):
    # 使用 BackgroundTasks 异步处理，防止 Webhook 超时
    background_tasks.add_task(process_health_data, payload)
    return {"status": "accepted", "message": "Processing in background"}

@app.post("/api/health/analyze")
async def trigger_analysis(background_tasks: BackgroundTasks, token: APIKey = Depends(get_api_key)):
    """
    手动触发 AI 分析并发送到 Discord
    """
    def run_and_send():
        content = generate_insight()
        send_to_discord(content)
        
    background_tasks.add_task(run_and_send)
    return {"status": "analysis_started"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
