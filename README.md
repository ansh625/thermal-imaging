# Thermal Polaris

Thermal Polaris is a thermal camera monitoring and analytics platform that combines real-time streaming, YOLO object detection, smart event recording, scheduling, notifications, and secure user access.

## Overview

The application consists of a React/Vite frontend interacting with a FastAPI backend. The backend manages camera sessions, YOLO detection, recording workflows, scheduling, email/password reset, and real-time updates via WebSockets.

## Features

- User authentication: signup, login, JWT access, password reset
- Forgot password with email reset link and fallback reset code
- Camera connect/disconnect for USB, RTSP, IP, HTTP, and raw streams
- Live WebSocket video streaming with detection overlays
- YOLOv8 object detection and detection history
- Manual recording, scheduled recording, and smart event clip capture
- Screenshot capture from live stream
- Notifications, alerts, and realtime dashboard updates
- Dashboard statistics for active cameras, recordings, detections, and storage
- Local storage for recordings, screenshots, and detection artifacts

## Tech Stack

- Frontend: React, Vite, Tailwind CSS, Zustand
- Backend: FastAPI, SQLAlchemy, SQLite, OpenCV, Ultralytics YOLO
- Realtime: WebSockets
- Scheduling: APScheduler
- Email: SMTP

## Project Structure

```
frontend/
backend/
docs/
README.md
FORGOT_PASSWORD_SETUP.md
PERFORMANCE_IMPROVEMENTS.md
```

## Setup Instructions

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Create a `.env` file from `.env.example` and configure your environment values.

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-email-password
FROM_EMAIL=your-email@example.com
FROM_NAME=Thermal Polaris
DATABASE_URL=sqlite:///./thermal_polaris.db
FRONTEND_URL=http://localhost:5173
```

## API Overview

Authentication
- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password`
- `GET /api/auth/forgot-password-code`
- `POST /api/auth/reset-password`
- `POST /api/auth/test-email`

Camera Management
- `POST /api/camera/connect`
- `POST /api/camera/disconnect`
- `GET /api/camera/list`
- `DELETE /api/camera/{camera_id}`

Streaming
- `GET /ws/video/{session_id}`
- `GET /ws/updates/{user_id}`

Recording
- `POST /api/recording/start`
- `POST /api/recording/stop`
- `GET /api/recording/list`
- `GET /api/recording/download/{recording_id}`
- `DELETE /api/recording/{recording_id}`

Smart Recording
- `GET /api/smart-recording/status`
- `GET /api/smart-recording/status/{session_id}`
- `POST /api/smart-recording/config`
- `POST /api/smart-recording/cleanup`
- `GET /api/smart-recording/clips`

Detection & Screenshots
- `GET /api/detection/list`
- `POST /api/screenshot/capture`

Scheduling
- `POST /api/schedule/create`
- `GET /api/schedule/list`
- `PUT /api/schedule/{schedule_id}/toggle`
- `DELETE /api/schedule/{schedule_id}`

Notifications & Dashboard
- `GET /api/notifications`
- `PUT /api/notifications/{notification_id}/read`
- `PUT /api/notifications/read-all`
- `GET /api/dashboard/stats`

## Documentation

- `docs/architecture.txt`
- `docs/forgot-password.md`
- `docs/performance_improvements.md`

## Notes

- Recordings, screenshots, and detection outputs are stored locally in `recordings/`, `screenshots/`, and `detections/`.
- The backend includes a `camera_handler`, `yolo_detector`, `recording_manager`, `smart_recording_manager`, `scheduler_service`, `notification_service`, `email_service`, and `websocket_manager`.
