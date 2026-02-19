import api from './api';

class NotificationService {
  constructor() {
    this.listeners = new Set();
  }

  subscribe(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  notify(notification) {
    this.listeners.forEach(callback => callback(notification));
  }

  async getNotifications(unreadOnly = false) {
    try {
      const response = await api.get('/notifications', {
        params: { unread_only: unreadOnly }
      });
      return response.data.notifications;
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
      return [];
    }
  }

  async markAsRead(notificationId) {
    try {
      await api.put(`/notifications/${notificationId}/read`);
      return true;
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
      return false;
    }
  }

  async markAllAsRead() {
    try {
      await api.put('/notifications/read-all');
      return true;
    } catch (error) {
      console.error('Failed to mark all as read:', error);
      return false;
    }
  }
}

export const notificationService = new NotificationService();