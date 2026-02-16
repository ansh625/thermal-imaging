from database import Notification, get_db
from datetime import datetime
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def create_notification(user_id: int, title: str, message: str, 
                          type: str = "info", data: dict = None):
        """Create a new notification"""
        try:
            db = next(get_db())
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=type,
                data=data
            )
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            logger.info(f"Notification created: {title} for user {user_id}")
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
    
    @staticmethod
    def get_user_notifications(user_id: int, unread_only: bool = False, limit: int = 50):
        """Get user notifications"""
        try:
            db = next(get_db())
            query = db.query(Notification).filter(Notification.user_id == user_id)
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
            
            notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
            return notifications
            
        except Exception as e:
            logger.error(f"Error fetching notifications: {e}")
            return []
    
    @staticmethod
    def mark_as_read(notification_id: int, user_id: int):
        """Mark notification as read"""
        try:
            db = next(get_db())
            notification = db.query(Notification).filter(
                Notification.id == notification_id,
                Notification.user_id == user_id
            ).first()
            
            if notification:
                notification.is_read = True
                db.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    @staticmethod
    def mark_all_as_read(user_id: int):
        """Mark all user notifications as read"""
        try:
            db = next(get_db())
            db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            ).update({Notification.is_read: True})
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error marking all as read: {e}")
            return False

notification_service = NotificationService()