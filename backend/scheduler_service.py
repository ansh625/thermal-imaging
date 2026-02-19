from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import RecordingSchedule, Camera, get_db
from datetime import datetime, time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.active_scheduled_recordings = {}  # camera_id -> recording_session_id
    
    def add_schedule(self, schedule_id: int):
        """Add a schedule to the scheduler"""
        try:
            db = next(get_db())
            schedule = db.query(RecordingSchedule).filter(
                RecordingSchedule.id == schedule_id
            ).first()
            
            if not schedule or not schedule.enabled:
                return False
            
            # Parse time
            start_hour, start_minute = map(int, schedule.start_time.split(':'))
            end_hour, end_minute = map(int, schedule.end_time.split(':'))
            
            # Convert days to APScheduler format
            day_map = {
                'Monday': 'mon', 'Tuesday': 'tue', 'Wednesday': 'wed',
                'Thursday': 'thu', 'Friday': 'fri', 'Saturday': 'sat', 'Sunday': 'sun'
            }
            days_str = ','.join([day_map[day] for day in schedule.days_of_week if day in day_map])
            
            # Schedule start
            self.scheduler.add_job(
                self._start_scheduled_recording,
                CronTrigger(day_of_week=days_str, hour=start_hour, minute=start_minute),
                args=[schedule.camera_id, schedule_id],
                id=f"start_{schedule_id}",
                replace_existing=True
            )
            
            # Schedule stop
            self.scheduler.add_job(
                self._stop_scheduled_recording,
                CronTrigger(day_of_week=days_str, hour=end_hour, minute=end_minute),
                args=[schedule.camera_id, schedule_id],
                id=f"stop_{schedule_id}",
                replace_existing=True
            )
            
            logger.info(f"Schedule added: {schedule.name} (ID: {schedule_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding schedule: {e}")
            return False
    
    def remove_schedule(self, schedule_id: int):
        """Remove a schedule from the scheduler"""
        try:
            self.scheduler.remove_job(f"start_{schedule_id}")
            self.scheduler.remove_job(f"stop_{schedule_id}")
            logger.info(f"Schedule removed: {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing schedule: {e}")
            return False
    
    def _start_scheduled_recording(self, camera_id: int, schedule_id: int):
        """Start scheduled recording"""
        logger.info(f"Starting scheduled recording for camera {camera_id}")
        # This will be triggered by the scheduler
        # The actual recording start logic will be in the WebSocket handler
        self.active_scheduled_recordings[camera_id] = {
            'schedule_id': schedule_id,
            'started_at': datetime.now()
        }
    
    def _stop_scheduled_recording(self, camera_id: int, schedule_id: int):
        """Stop scheduled recording"""
        logger.info(f"Stopping scheduled recording for camera {camera_id} (schedule: {schedule_id})")
        
        try:
            # Find and stop any active recording for this camera
            from camera_handler import camera_manager
            from recording_manager import recording_manager
            
            # Find the session for this camera
            camera_session = camera_manager.get_session_by_camera_id(camera_id)
            
            if camera_session:
                session_id = camera_session.session_id
                # Stop the recording if it's active
                if recording_manager.is_recording(session_id):
                    recording_manager.stop_recording(session_id)
                    logger.info(f"Recording stopped for camera {camera_id}")
        except Exception as e:
            logger.warning(f"Error stopping recording for camera {camera_id}: {e}")
        
        # Remove from active scheduled recordings
        if camera_id in self.active_scheduled_recordings:
            del self.active_scheduled_recordings[camera_id]
    
    def is_scheduled_recording_active(self, camera_id: int) -> bool:
        """Check if camera should be recording based on schedule"""
        return camera_id in self.active_scheduled_recordings
    
    def get_active_schedule_for_camera(self, camera_id: int):
        """Get the active schedule for a camera at current time"""
        try:
            db = next(get_db())
            now = datetime.now()
            current_day = now.strftime('%A')  # 'Monday', 'Tuesday', etc
            current_time = now.time()
            
            schedules = db.query(RecordingSchedule).filter(
                RecordingSchedule.camera_id == camera_id,
                RecordingSchedule.enabled == True
            ).all()
            
            # Check if any schedule is active now
            for schedule in schedules:
                if current_day in schedule.days_of_week:
                    start_time = datetime.strptime(schedule.start_time, '%H:%M').time()
                    end_time = datetime.strptime(schedule.end_time, '%H:%M').time()
                    
                    # Check if current time is within schedule window
                    if start_time <= current_time <= end_time:
                        return schedule
            
            return None
        except Exception as e:
            logger.error(f"Error checking active schedule: {e}")
            return None
    
    def reload_all_schedules(self):
        """Reload all active schedules from database"""
        try:
            db = next(get_db())
            schedules = db.query(RecordingSchedule).filter(
                RecordingSchedule.enabled == True
            ).all()
            
            for schedule in schedules:
                self.add_schedule(schedule.id)
            
            logger.info(f"Reloaded {len(schedules)} schedules")
            return True
            
        except Exception as e:
            logger.error(f"Error reloading schedules: {e}")
            return False

scheduler_service = SchedulerService()