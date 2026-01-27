
from ultralytics import YOLO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.core.config import settings

try:
    logger.info(f"Loading YOLO model from: {settings.YOLO_BODY_MODEL}")
    model = YOLO(settings.YOLO_BODY_MODEL)
    logger.info("YOLO model loaded successfully")
except Exception as e:
    logger.error(f"YOLO Error: {e}")
except SystemExit as e:
    logger.error(f"YOLO SystemExit: {e}")
