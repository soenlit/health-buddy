from insight_engine import generate_insight, send_to_discord
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("daily_task")

if __name__ == "__main__":
    logger.info("Starting scheduled health analysis...")
    content = generate_insight()
    send_to_discord(content)
    logger.info("Analysis report sent to Discord.")
