import os
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyQuery, APIKey
from pydantic import BaseModel

app = FastAPI(title="Health Buddy API")

# 这里的 Token 就是你之前建议的 URL Token
API_KEY_NAME = "token"
webhook_token = os.getenv("WEBHOOK_TOKEN", "super-secret-token")
api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Depends(api_key_query)):
    if api_key == webhook_token:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid token. Who the hell are you?")

@app.get("/health")
def health_check():
    return {"status": "alive", "timestamp": datetime.now()}

@app.post("/api/health/webhook")
async def health_webhook(payload: Dict[str, Any], token: APIKey = Depends(get_api_key)):
    """
    接收来自 Health Auto Export 的 JSON 数据
    """
    # 暂时只打印，后续接入 DB 存储
    data = payload.get("data", {})
    metrics = data.get("metrics", [])
    
    print(f"[{datetime.now()}] 收到 Webhook 数据, 指标数量: {len(metrics)}")
    
    # 后续这里接入 PostgreSQL 存储逻辑
    for metric in metrics:
        name = metric.get("name")
        samples = metric.get("data", [])
        if samples:
            print(f"指标: {name}, 最新数值: {samples[0].get('qty')}")
            
    return {"status": "success", "processed_metrics": len(metrics)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
