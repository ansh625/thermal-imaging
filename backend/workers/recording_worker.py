from core.state import recording_queue
from recording_manager import recording_manager
import logging

logger = logging.getLogger(__name__)

async def recording_worker():
    while True:
        try:
            event = await recording_queue.get()
            
            recording_manager.write_frame(
                event["session_id"],
                event["frame"]
            )
            
            recording_queue.task_done()
        
        except Exception as e:
            logger.error(f"Recording worker error: {e}")