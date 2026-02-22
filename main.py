import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Security, Depends, BackgroundTasks
from fastapi.security.api_key import APIKeyQuery, APIKey
from pydantic import BaseModel
from database import SessionLocal, HealthMetric, init_db

# 初始化数据库
init_db()

app = FastAPI(title="Health Buddy API")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY_NAME = "token"
webhook_token = os.getenv("WEBHOOK_TOKEN", "super-secret-token")
api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Depends(api_key_query)):
    logger.info(f"Checking token. Received: {api_key}, Expected: {webhook_token}")
    if api_key == webhook_token:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid token.")

def process_health_data(payload: Dict[str, Any]):
    db = SessionLocal()
    try:
        data = payload.get("data", {})
        metrics = data.get("metrics", [])
        
        count = 0
        for m in metrics:
            metric_type = m.get("name")
            unit = m.get("units")
            samples = m.get("data", [])
            
            for sample in samples:
                ts_str = sample.get("date")
                val = sample.get("qty")
                
                if ts_str and val is not None:
                    # 解析时间，处理几种常见的格式
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except ValueError:
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")

                    # 插入或忽略重复
                    metric_entry = HealthMetric(
                        timestamp=ts,
                        metric_type=metric_type,
                        value=float(val),
                        unit=unit,
                        raw_data=sample
                    )
                    db.merge(metric_entry) # 使用 merge 处理 UniqueConstraint 情况
                    count += 1
        
        db.commit()
        logger.info(f"Successfully processed {count} samples.")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
