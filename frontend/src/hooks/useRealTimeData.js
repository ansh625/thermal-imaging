import { useEffect, useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { websocketService } from '../services/websocket';
import { notificationService } from '../services/notifications';
import toast from 'react-hot-toast';

export function useRealTimeData() {
  const { user } = useAuthStore();
  const [stats, setStats] = useState({
    active_cameras: 0,
    total_recordings: 0,
    total_detections: 0,
    storage_used_gb: 0,
  });

  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!user?.id) return;

    const handleOpen = () => {
      setIsConnected(true);
    };

    const handleClose = () => {
      setIsConnected(false);
    };

    // Connect to real-time updates WebSocket
    setTimeout(() => {
      websocketService.connect(
        'updates',
        user.id,
        (message) => handleWebSocketMessage(message),
        (error) => {
          console.error('WebSocket error:', error);
          handleClose();
        },
        handleOpen,
        handleClose
      );
    }, 1000);

    return () => {
      websocketService.disconnect('updates', user.id);
    };
  }, [user]);

  const handleWebSocketMessage = (message) => {
    const { type, data } = message;

    switch (type) {
      case 'camera_connected':
        setStats((prev) => ({
          ...prev,
          active_cameras: prev.active_cameras + 1,
        }));
        notificationService.notify({
          title: 'Camera Connected',
          message: `Camera ${data.name} connected successfully`,
          type: 'success',
        });
        break;

      case 'camera_disconnected':
        setStats((prev) => ({
          ...prev,
          active_cameras: Math.max(0, prev.active_cameras - 1),
        }));
        notificationService.notify({
          title: 'Camera Disconnected',
          message: 'Camera disconnected',
          type: 'info',
        });
        break;

      case 'recording_started':
        notificationService.notify({
          title: 'Recording Started',
          message: 'Video recording has started',
          type: 'info',
        });
        break;

      case 'recording_stopped':
        setStats((prev) => ({
          ...prev,
          total_recordings: prev.total_recordings + 1,
        }));
        notificationService.notify({
          title: 'Recording Stopped',
          message: `Recording saved (${data.duration}s)`,
          type: 'success',
        });
        break;

      case 'detection_alert':
        setStats((prev) => ({
          ...prev,
          total_detections: prev.total_detections + 1,
        }));
        toast.success(`${data.class_name} detected!`, {
          icon: '👁️',
          duration: 4000,
        });
        break;

      case 'screenshot_taken':
        const screenshotMsg = data.detections > 0 
          ? `Screenshot saved with ${data.detections} detection${data.detections !== 1 ? 's' : ''}`
          : 'Screenshot saved successfully';
        notificationService.notify({
          title: 'Screenshot Captured',
          message: screenshotMsg,
          type: 'success',
        });
        break;

      case 'stats_update':
        setStats(data);
        break;

      default:
        console.log('Unknown message type:', type);
    }
  };

  return { stats, isConnected, setStats };
}
