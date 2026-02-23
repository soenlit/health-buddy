import requests
import time
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("graph_verify")

GRAFANA_URL = "http://localhost:3000"
AUTH = ("admin", "admin")

def wait_for_grafana():
    for _ in range(10):
        try:
            r = requests.get(f"{GRAFANA_URL}/api/health", auth=AUTH)
            if r.status_code == 200:
                logger.info("✅ Grafana is alive.")
                return True
        except:
            pass
        logger.info("⏳ Waiting for Grafana...")
        time.sleep(3)
    return False

def check_datasource():
    r = requests.get(f"{GRAFANA_URL}/api/datasources", auth=AUTH)
    ds_list = r.json()
    logger.info(f"Available datasources: {[ds['name'] for ds in ds_list]}")
    for ds in ds_list:
        if ds['name'] == 'PostgreSQL':
            logger.info(f"✅ Datasource 'PostgreSQL' found with UID: {ds['uid']}")
            return ds['uid']
    logger.error("❌ Datasource 'PostgreSQL' missing!")
    return None

def check_data_presence(ds_uid):
    # 测试 SQL 查询
    query = {
        "from": "now-1y",
        "to": "now",
        "queries": [
            {
                "refId": "A",
                "datasource": {"type": "postgres", "uid": ds_uid},
                "rawSql": "SELECT count(*) FROM health_metrics",
                "format": "table"
            }
        ]
    }
    r = requests.post(f"{GRAFANA_URL}/api/ds/query", auth=AUTH, json=query)
    if r.status_code == 200:
        logger.info(f"📊 Query Result: {r.json()}")
        return True
    logger.error(f"❌ Failed to query database: {r.text}")
    return False

def push_dashboard():
    db_path = "/Users/agent_bobo/soenlit/health-buddy/grafana/dashboards/overview.json"
    with open(db_path, "r") as f:
        dashboard_content = json.load(f)
    
    r = requests.get(f"{GRAFANA_URL}/api/datasources/name/PostgreSQL", auth=AUTH)
    if r.status_code != 200:
        logger.error("❌ Cannot fetch datasource for linking")
        return False
    ds_uid = r.json()['uid']
    
    # 彻底替换所有可能的 UID 引用
    dashboard_str = json.dumps(dashboard_content)
    # 替换原本模板中的变量占位符
    dashboard_str = dashboard_str.replace("${DS_POSTGRESQL}", ds_uid)
    # 兜底：如果之前 JSON 里已经带了错误的 UID，也强制换成现在的
    dashboard_data = json.loads(dashboard_str)
    for panel in dashboard_data.get('panels', []):
        if 'datasource' in panel:
            panel['datasource']['uid'] = ds_uid
        for target in panel.get('targets', []):
            if 'datasource' in target:
                target['datasource']['uid'] = ds_uid

    payload = {
        "dashboard": dashboard_data,
        "overwrite": True
    }
    
    r = requests.post(f"{GRAFANA_URL}/api/dashboards/db", auth=AUTH, json=payload)
    if r.status_code == 200:
        logger.info("🚀 Dashboard pushed successfully via API.")
        return True
    else:
        logger.error(f"❌ Failed to push dashboard: {r.text}")
        return False

if __name__ == "__main__":
    if wait_for_grafana():
        ds_uid = check_datasource()
        if ds_uid:
            check_data_presence(ds_uid)
            push_dashboard()
