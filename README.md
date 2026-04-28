# Thermal Polaris

A thermal camera monitoring and analytics system with live stream monitoring, YOLO object detection, scheduling, recordings, and secure user access.

## Overview

Thermal Polaris is a surveillance and analytics platform built for thermal camera workflows. It supports live camera streaming, YOLO-powered object detection, an analytics dashboard, recordings and snapshots, schedule management, and user authentication.

## Features

- Authentication: Login, Signup, Forgot Password, Reset Password
- Live camera streaming
- Object detection with YOLO
- Advanced analytics dashboard
- Recording and snapshot system
- Scheduling system
- Real-time updates via WebSockets
- Notifications and email integration

## Tech Stack

- Frontend: React (Vite), Tailwind CSS
- Backend: FastAPI (Python)
- Database: SQLite (via SQLAlchemy ORM)
- Realtime: WebSockets
- Detection: YOLO
- State Management: Zustand

## Architecture

The system is built as a React/Vite frontend that communicates with a FastAPI backend. FastAPI handles both API routing and backend business logic, while the backend connects to the database and supporting services such as camera processing, notifications, email, and scheduling.

For full architecture details, see `docs/architecture.txt`.

## Project Structure

```
frontend/
backend/
docs/
README.md
.env.example
```

## Key Modules

- Frontend: pages, components, services, store
- Backend: `app.py`, `auth.py`, `database.py`, camera module, services, `websocket_manager.py`

## Setup Instructions

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Create a `.env` file from `.env.example` and configure the values for your environment.

Example variables:

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-email-password
FROM_EMAIL=your-email@example.com
FROM_NAME=Thermal Polaris
DATABASE_URL=sqlite:///./thermal_polaris.db
```

## API Overview

Main API routes include:

- `/api/auth`
- `/api/cameras`
- `/api/analytics`
- `/api/recordings`
- `/api/schedules`

## Documentation

- `docs/architecture.txt`
- `docs/forgot-password.md`
- `docs/performance_improvements.md`

## Future Improvements

- Docker support
- Cloud deployment
- GPU optimization
- Multi-camera scaling

## Author / Credits

Thermal Polaris

Built with React, FastAPI, YOLO, and real-time processing components for thermal camera monitoring and analytics.
