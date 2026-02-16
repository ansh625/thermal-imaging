# CSIO ThermalStream - System Architecture

## Overview
CSIO ThermalStream is a production-ready thermal camera monitoring system with real-time streaming, AI-powered object detection, and automated recording capabilities.

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104.1
- **Database**: SQLite (configurable to PostgreSQL)
- **Computer Vision**: OpenCV 4.8.1
- **Object Detection**: YOLOv8 (Ultralytics)
- **Real-time Communication**: WebSockets
- **Task Scheduling**: APScheduler
- **Authentication**: JWT (JSON Web Tokens)

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite 5
- **Styling**: TailwindCSS 3
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Real-time**: Socket.io / WebSocket
- **Animations**: Framer Motion

## System Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   React     │  │   Zustand    │  │  WebSocket       │   │
│  │   Components│  │   Store      │  │  Client          │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                    HTTP/WebSocket
                            │
┌─────────────────────────────────────────────────────────────┐
│                         BACKEND                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   FastAPI   │  │  WebSocket   │  │  APScheduler     │   │
│  │   REST API  │  │  Manager     │  │  Service         │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Camera    │  │  YOLO        │  │  Recording       │   │
│  │   Handler   │  │  Detector    │  │  Manager         │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  SQLite DB  │  │  Notification│  │  Email           │   │
│  │             │  │  Service     │  │  Service         │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                    Camera Protocols
                            │
┌─────────────────────────────────────────────────────────────┐
│                      CAMERA SOURCES                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   USB    │  │   RTSP   │  │   HTTP   │  │  IP Cam  │   │
│  │  Camera  │  │  Stream  │  │  Stream  │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Camera Handler (`camera_handler.py`)
**Purpose**: Manages camera connections and frame capture

**Key Features**:
- Support for USB, RTSP, HTTP, and IP cameras
- URL parsing and auto-detection
- Connection retry logic
- Multi-camera session management

**Flow**:
```
User Input → URL Parser → Try Connections → Create Session → Capture Frames
```

### 2. YOLO Detector (`yolo_detector.py`)
**Purpose**: Real-time object detection using YOLOv8

**Key Features**:
- Detects persons, vehicles, animals
- Draws bounding boxes on frames
- Saves detection screenshots
- Confidence threshold filtering

**Detection Classes**:
- Person (0)
- Vehicles: Car (2), Motorcycle (3), Bus (5), Truck (7)
- Animals: Bird (14), Cat (15), Dog (16)

**Flow**:
```
Frame Input → YOLO Inference → Filter Detections → Draw Boxes → Return Results
```

### 3. Recording Manager (`recording_manager.py`)
**Purpose**: Handles video recording operations

**Key Features**:
- MP4 video recording with H264 codec
- Multi-session recording support
- Automatic file naming with timestamps
- Recording statistics tracking

**Flow**:
```
Start Request → Create VideoWriter → Write Frames → Stop → Save Stats to DB
```

### 4. Scheduler Service (`scheduler_service.py`)
**Purpose**: Automated recording based on schedules

**Key Features**:
- Cron-based scheduling
- Day-of-week support
- Start/stop time configuration
- Automatic recording trigger

**Flow**:
```
Schedule Creation → Add Cron Jobs → Trigger at Time → Start/Stop Recording
```

### 5. Notification Service (`notification_service.py`)
**Purpose**: Real-time user notifications

**Key Features**:
- Database-stored notifications
- Read/unread tracking
- Real-time WebSocket push
- Multiple notification types (info, success, warning, error)

**Flow**:
```
Event Occurs → Create Notification → Save to DB → Broadcast via WebSocket
```

### 6. Email Service (`email_service.py`)
**Purpose**: Email communications

**Key Features**:
- SMTP integration (Gmail, custom)
- HTML email templates
- Password reset emails
- Background email sending

**Flow**:
```
Forgot Password → Generate Token → Send Email → User Clicks Link → Reset Password
```

### 7. WebSocket Manager (`websocket_manager.py`)
**Purpose**: Real-time bidirectional communication

**Key Features**:
- User-based connection management
- Broadcast to specific users
- Multiple connections per user
- Auto-disconnect handling

**Channels**:
- `/ws/video/{session_id}` - Video streaming
- `/ws/updates/{user_id}` - Dashboard updates

## Data Flow

### Camera Connection Flow
```
1. User enters camera URL
2. Frontend → POST /api/camera/connect
3. Backend parses URL and tries connections
4. If successful:
   - Create camera session
   - Save to database
   - Create notification
   - Broadcast to user via WebSocket
5. Frontend receives update and shows live status
```

### Video Streaming Flow
```
1. Frontend connects to WebSocket /ws/video/{session_id}
2. Backend continuously:
   - Captures frame from camera
   - Runs YOLO detection (if enabled)
   - Writes to recording (if active)
   - Encodes frame as JPEG
   - Sends to frontend
3. Frontend displays frame in video player
```

### Recording Flow
```
1. User clicks "Start Recording"
2. Frontend → POST /api/recording/start
3. Backend:
   - Creates VideoWriter
   - Starts writing frames
   - Creates database entry
   - Sends notification
4. User clicks "Stop Recording"
5. Frontend → POST /api/recording/stop
6. Backend:
   - Stops VideoWriter
   - Updates database with stats
   - Calculates storage
   - Sends notification
```

### Detection Flow
```
1. User enables detection
2. Frontend sends WebSocket message
3. Backend runs YOLO on each frame
4. Detected objects:
   - Draw bounding boxes
   - Save to database
   - Save screenshot (optional)
   - Send notification (if new detection)
5. Frontend displays boxes on video
```

### Scheduler Flow
```
1. User creates schedule
2. Frontend → POST /api/schedule/create
3. Backend:
   - Saves to database
   - Creates cron jobs
   - Schedules start/stop times
4. At scheduled time:
   - APScheduler triggers
   - Starts/stops recording automatically
   - Sends notification
```

## Database Schema

### Users
- Authentication and profile data
- Password reset tokens

### Cameras
- Connection details
- Status tracking
- Session management

### Recordings
- File metadata
- Duration and size
- Scheduled flag

### Detections
- Object class and confidence
- Bounding box coordinates
- Screenshot paths

### RecordingSchedules
- Schedule configuration
- Days and times
- Enable/disable flag

### Notifications
- User notifications
- Read status
- Additional data

## Security Features

1. **Authentication**
   - JWT tokens with expiration
   - Bcrypt password hashing
   - Token refresh mechanism

2. **Authorization**
   - User-specific data isolation
   - Role-based access (admin, operator, viewer)

3. **Password Reset**
   - Secure token generation
   - Time-limited tokens (1 hour)
   - Email verification

4. **API Security**
   - CORS configuration
   - Rate limiting (planned)
   - Input validation

## Real-time Features

1. **Live Video Streaming**
   - WebSocket-based
   - ~25 FPS typical
   - JPEG compression

2. **Dashboard Updates**
   - Active camera count
   - Recording status
   - Detection alerts
   - Storage updates

3. **Notifications**
   - Instant push to frontend
   - Camera connect/disconnect
   - Recording start/stop
   - Detection events

## Storage Management

### Directory Structure
```
backend/
├── recordings/          # Video recordings
├── screenshots/         # Manual screenshots
├── detections/          # Detection screenshots
└── thumbnails/          # Video thumbnails (planned)
```

### Storage Tracking
- Real-time calculation
- Per-directory statistics
- Dashboard display
- Automatic cleanup (planned)

## Scalability Considerations

### Current Capacity
- **Cameras**: Up to 10 concurrent
- **Recordings**: Limited by storage
- **Users**: Unlimited (database-dependent)

### Future Enhancements
- Horizontal scaling with load balancer
- Redis for session management
- PostgreSQL for production
- Cloud storage integration (S3, Azure Blob)
- CDN for video delivery

## Performance Optimization

1. **Video Processing**
   - JPEG compression (80% quality)
   - Efficient frame encoding
   - Asynchronous operations

2. **Detection**
   - YOLOv8 nano model (fastest)
   - Optional detection toggle
   - Confidence threshold filtering

3. **Database**
   - Indexed queries
   - Connection pooling
   - Lazy loading

4. **WebSocket**
   - Efficient message serialization
   - Connection reuse
   - Auto-reconnect

## Monitoring & Logging

### Health Check Endpoint
```
GET /health
```
Returns:
- System status
- YOLO model status
- Active cameras
- Active recordings

### Logging Levels
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Failures requiring attention
- CRITICAL: System-level failures

## Deployment

### Development
```bash
# Backend
cd backend
source venv/bin/activate
python app.py

# Frontend
cd frontend
npm run dev
```

### Production (Docker)
```bash
docker-compose up -d
```

### Environment Variables
See `.env` file for configuration options.

## API Documentation

FastAPI provides automatic interactive documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Support & Maintenance

For technical support:
- Email: support@csio.com
- Documentation: docs.csio.com
- Issue Tracker: github.com/csio/thermalstream

---

**Version**: 2.0.0  
**Last Updated**: 2025-01-XX  
**Maintained by**: CSIR CSIO Development Team