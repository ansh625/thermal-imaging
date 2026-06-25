import asyncio
from workers.detection_worker import detection_worker

def start_detection_worker(session_id: str):
    return asyncio.create_task(detection_worker(session_id))