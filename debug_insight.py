import os
import sys
import logging
from insight_engine import generate_insight, send_to_discord

# 配置日志到标准输出，方便直接看
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("debug_insight")

def debug_run():
    logger.info("--- Starting Insight Engine Debug Run ---")
    
    # 检查环境变量
    gemini_key = os.getenv("GEMINI_API_KEY")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if not gemini_key:
        logger.error("❌ GEMINI_API_KEY is missing!")
    if not discord_url:
        logger.error("❌ DISCORD_WEBHOOK_URL is missing!")
        
    logger.info("Step 1: Generating Insight via Gemini...")
    try:
        content = generate_insight()
        logger.info(f"✅ Gemini Response Received:\n{content}")
        
        if "还没攒够数据" in content:
            logger.warning("⚠️ Database seems to have insufficient data for analysis.")
    except Exception as e:
        logger.error(f"❌ Failed to generate insight: {e}")
        return

    logger.info("Step 2: Sending to Discord...")
    try:
        send_to_discord(content)
        logger.info("✅ Discord notification sent (check your channel).")
    except Exception as e:
        logger.error(f"❌ Failed to send to Discord: {e}")

if __name__ == "__main__":
    debug_run()
