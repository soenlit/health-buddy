import pandas as pd
from database import SessionLocal, HealthMetric
from datetime import datetime
import os

def import_csv(file_path):
    print(f"📖 Reading {file_path}...")
    df = pd.read_csv(file_path)
    
    db = SessionLocal()
    count = 0
    try:
        for idx, row in df.iterrows():
            ts = datetime.fromisoformat(row['timestamp'].replace(" -0800", "-08:00"))
            metric = HealthMetric(
                timestamp=ts,
                metric_type=row['metric_type'],
                value=float(row['value']),
                unit=row.get('unit', 'count'),
                source=row.get('source', 'apple_health'),
                raw_data={"imported": True}
            )
            db.merge(metric)
            count += 1
            if count % 100 == 0:
                print(f"✅ Processed {count} rows...")
        
        db.commit()
        print(f"🚀 Successfully imported {count} data points to local database.")
    except Exception as e:
        print(f"❌ Error during import: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    csv_path = "/Users/agent_bobo/.openclaw/media/inbound/f4ed3c9a-48db-4d42-8915-bceb298ab374.csv"
    if os.path.exists(csv_path):
        import_csv(csv_path)
    else:
        print(f"File not found: {csv_path}")
