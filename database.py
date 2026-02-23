import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 自动处理本地和容器内的连接地址
raw_db_url = os.getenv("DATABASE_URL", "postgresql://health_user:health_pass@db:5432/health_db")
if os.getenv("IS_LOCAL_DEV") == "true":
    DATABASE_URL = raw_db_url.replace("@db:", "@localhost:")
else:
    DATABASE_URL = raw_db_url

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    metric_type = Column(String, index=True)  # 例如: step_count, heart_rate, sleep_analysis
    value = Column(Float)
    unit = Column(String)
    source = Column(String, default="apple_health")
    raw_data = Column(JSON)  # 存储原始 JSON 以备不时之需

    # 防止重复导入同一时间点的同一指标
    __table_args__ = (UniqueConstraint('timestamp', 'metric_type', name='_timestamp_metric_uc'),)

def init_db():
    Base.metadata.create_all(bind=engine)
