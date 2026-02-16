# CSIO ThermalStream - Functionality Guide

## Complete Feature Documentation

This guide explains every functionality in the CSIO ThermalStream system.

---

## 1. USER AUTHENTICATION

### Signup
**What it does**: Creates a new user account

**How it works**:
1. User provides email, password, full name, organization
2. System checks if email already exists
3. Password is hashed using bcrypt
4. User record is created in database
5. User can now login

**API Endpoint**: `POST /api/auth/signup`

**Frontend**: `frontend/src/pages/Signup.jsx`

---

### Login
**What it does**: Authenticates user and provides access token

**How it works**:
1. User provides email and password
2. System verifies credentials
3. JWT token is generated with 30-min expiration
4. Token is sent to frontend and stored in localStorage
5. All subsequent requests include this token

**API Endpoint**: `POST /api/auth/login`

**Frontend**: `frontend/src/pages/Login.jsx`

---

### Forgot Password
**What it does**: Initiates password reset process

**How it works**:
1. User enters email address
2. System generates unique reset token
3. Token is saved to database with 1-hour expiration
4. Email is sent with reset link
5. User clicks link and enters new password
6. Token is verified and password is updated

**API Endpoints**:
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`

**Frontend**: 
- `frontend/src/pages/ForgotPassword.jsx`
- `frontend/src/pages/ResetPassword.jsx`

---

## 2. CAMERA MANAGEMENT

### Connect Camera
**What it does**: Establishes connection to camera source

**Supported Formats**:
- **USB Camera**: Enter index (0, 1, 2, 3)
- **IP Address**: `192.168.1.100`
- **IP:Port**: `192.168.1.100:8080`
- **RTSP**: `rtsp://192.168.1.100/stream`
- **HTTP**: `http://192.168.1.100/video.mjpg`

**How it works**:
1. User enters camera URL
2. System parses input and generates possible URLs
3. Tries each URL until successful connection
4. Creates camera session with unique session_id
5. Saves camera to database
6. Starts frame capture loop
7. Sends notification to user

**API Endpoint**: `POST /api/camera/connect`

**Backend**: `camera_handler.py` → `CameraManager.create_session()`

**Frontend**: `frontend/src/components/ConnectionBar.jsx`

---

### Disconnect Camera
**What it does**: Stops camera stream and releases resources

**How it works**:
1. User clicks disconnect
2. System stops any active recording
3. Releases camera capture
4. Updates database status
5. Removes session from memory
6. Sends notification

**API Endpoint**: `POST /api/camera/disconnect`

---

### List Cameras
**What it does**: Shows all cameras owned by user

**What it displays**:
- Camera name
- Connection type (USB/RTSP/HTTP)
- Status (connected/disconnected)
- FPS and resolution
- Last seen timestamp

**API Endpoint**: `GET /api/camera/list`

**Frontend**: `frontend/src/pages/Cameras.jsx`

---

## 3. VIDEO STREAMING

### Live Stream
**What it does**: Displays real-time video from camera

**How it works**:
1. Frontend opens WebSocket connection
2. Backend continuously captures frames
3. Each frame is:
   - Processed (detection if enabled)
   - Encoded as JPEG
   - Converted to base64
   - Sent via WebSocket
4. Frontend decodes and displays on canvas
5. Runs at camera's FPS (typically 25-30)

**WebSocket**: `/ws/video/{session_id}`

**Backend**: `app.py` → `video_stream()` function

**Frontend**: `frontend/src/components/VideoPlayer.jsx`

**Frame Rate**: 25-30 FPS typical  
**Compression**: JPEG at 80% quality  
**Latency**: 100-200ms typical

---

## 4. OBJECT DETECTION (YOLO)

### Enable Detection
**What it does**: Activates AI-powered object detection

**Detected Objects**:
- **Persons**: People in frame
- **Vehicles**: Cars, motorcycles, buses, trucks
- **Animals**: Birds, cats, dogs

**How it works**:
1. User enables detection toggle
2. Frontend sends WebSocket message
3. Backend runs YOLOv8 on each frame
4. Detections above confidence threshold are:
   - Drawn on frame (green boxes)
   - Saved to database
   - Screenshot saved (optional)
5. Bounding boxes overlay on video

**Backend**: `yolo_detector.py` → `YOLODetector.detect()`

**Model**: YOLOv8 nano (yolov8n.pt)  
**Default Confidence**: 0.5 (50%)  
**Processing Time**: ~30ms per frame

---

### Detection History
**What it does**: Shows all past detections with screenshots

**Information Shown**:
- Object class (person, car, etc.)
- Confidence score
- Timestamp
- Camera that detected it
- Bounding box coordinates
- Screenshot image

**API Endpoint**: `GET /api/detection/list`

**Frontend**: Quick Actions → "Detection History"

---

## 5. VIDEO RECORDING

### Manual Recording
**What it does**: Records video on-demand

**How it works**:
1. User clicks "Start Recording"
2. System creates MP4 file with timestamp filename
3. Each frame is written to file
4. User clicks "Stop Recording"
5. File is finalized and stats saved to database
6. File available for download

**Filename Format**: `Camera1_20250116_143022.mp4`

**Video Format**: MP4  
**Codec**: H264  
**Quality**: Original camera quality

**API Endpoints**:
- `POST /api/recording/start`
- `POST /api/recording/stop`

**Backend**: `recording_manager.py`

---

### Scheduled Recording
**What it does**: Automatically records at specified times

**How it works**:
1. User creates schedule:
   - Select camera
   - Choose days (Mon-Sun)
   - Set start time (e.g., 09:00)
   - Set end time (e.g., 17:00)
2. System creates cron jobs
3. At start time: Recording begins automatically
4. At end time: Recording stops automatically
5. Files saved with scheduled flag

**API Endpoints**:
- `POST /api/schedule/create`
- `GET /api/schedule/list`
- `DELETE /api/schedule/{id}`

**Backend**: `scheduler_service.py` using APScheduler

**Frontend**: Click "Schedule Recording" button → Modal opens

---

### Download Recording
**What it does**: Allows downloading saved videos

**API Endpoint**: `GET /api/recording/download/{recording_id}`

**Frontend**: Recording list → Download button

---

### Delete Recording
**What it does**: Removes video file and database entry

**What happens**:
- File deleted from disk
- Database entry removed
- Storage stats recalculated

**API Endpoint**: `DELETE /api/recording/{recording_id}`

---

## 6. NOTIFICATIONS

### Real-time Notifications
**What it does**: Instant alerts for important events

**Notification Types**:
- **Camera Connected** (success)
- **Camera Disconnected** (info)
- **Recording Started** (info)
- **Recording Stopped** (success)
- **Detection Alert** (warning)
- **Schedule Triggered** (info)
- **System Error** (error)

**How it works**:
1. Backend event occurs
2. Notification created in database
3. Sent via WebSocket to user
4. Frontend displays toast notification
5. Also appears in notification center
6. User can mark as read

**Backend**: `notification_service.py`

**Frontend**: `frontend/src/components/NotificationCenter.jsx`

**WebSocket**: `/ws/updates/{user_id}`

---

### Notification Center
**What it does**: Shows all notifications in dropdown

**Features**:
- Unread count badge
- Mark individual as read
- Mark all as read
- Delete notifications
- Filter by type

**API Endpoints**:
- `GET /api/notifications`
- `PUT /api/notifications/{id}/read`
- `PUT /api/notifications/read-all`

---

## 7. DASHBOARD STATISTICS

### Active Cameras
**What it shows**: Number of currently connected cameras

**Updates**: Real-time via WebSocket

---

### Total Recordings
**What it shows**: Count of all saved videos

**Updates**: Real-time when recording stops

---

### Total Detections
**What it shows**: Count of all objects detected

**Updates**: Real-time when object detected

---

### Storage Used
**What it shows**: Total disk space used

**Breakdown**:
- Recordings storage
- Screenshots storage
- Detections storage

**Updates**: Real-time when files added/deleted

**API Endpoint**: `GET /api/dashboard/stats`

---

## 8. SYSTEM STATUS

### Connection Status
**Shows**: Whether camera is connected

**Indicator**: 
- 🟢 Green dot = Connected
- 🔴 Red dot = Disconnected

---

### Frame Rate (FPS)
**Shows**: Current video frame rate

**Typical Values**: 25-30 FPS

---

### Resolution
**Shows**: Video resolution

**Typical**: 1280x720 (720p)

---

### Latency
**Shows**: Delay between capture and display

**Typical**: 45-200ms

---

## 9. QUICK ACTIONS

### View Recordings
**What it does**: Opens recordings page

**Shows**: List of all recordings with:
- Thumbnail preview
- Duration
- File size
- Timestamp
- Download button
- Delete button

**Navigates to**: `/recordings`

---

### Detection History
**What it does**: Opens detections page

**Shows**: Gallery of all detections with:
- Object class
- Confidence
- Screenshot
- Timestamp
- Camera name

**Navigates to**: `/analytics` → Detections tab

---

### Export Data
**What it does**: Exports system data

**Export Formats**:
- CSV (recordings list)
- JSON (full data export)
- PDF (reports)

**Includes**:
- All recordings metadata
- Detection statistics
- Camera activity logs

---

### System Settings
**What it does**: Opens settings page

**Settings Available**:
- User profile
- Email preferences
- Detection sensitivity
- Storage management
- Notification preferences

**Navigates to**: `/settings`

---

## 10. RECORDING SCHEDULER UI

### Create Schedule
**Steps**:
1. Click "Schedule Recording" button
2. Modal opens with form:
   - Schedule name
   - Select camera
   - Choose days (checkboxes)
   - Start time picker
   - End time picker
3. Click "Create Schedule"
4. Schedule appears in list
5. Recording runs automatically

---

### Manage Schedules
**Actions**:
- **Toggle**: Enable/disable without deleting
- **Edit**: Modify times and days
- **Delete**: Remove schedule completely

**Status Indicators**:
- 🟢 Active
- ⚫ Disabled

---

## 11. PROFILE DROPDOWN

### Always Visible
**Location**: Top-right corner

**Contains**:
- User avatar
- User name and email
- Settings button
- Logout button

---

### Settings
**Opens**: Settings page

**Available Settings**:
- Change password
- Update profile
- Email preferences
- Notification settings

---

### Logout
**What it does**: Ends session

**Actions**:
- Clears JWT token
- Disconnects all cameras
- Redirects to login
- Clears local storage

---

## 12. TAB NAVIGATION

### Dashboard Tab
**Shows**: Overview with stats cards and main video

**Active by default**

---

### Cameras Tab
**Shows**: All cameras with details

**Actions per camera**:
- Connect/Disconnect
- View live feed
- Edit name
- Delete camera

---

### Recordings Tab
**Shows**: All recordings in grid/list view

**Features**:
- Search by name
- Filter by date
- Sort by size/duration
- Bulk actions

---

### Analytics Tab
**Shows**: Charts and statistics

**Includes**:
- Detection graphs
- Camera uptime
- Storage trends
- Activity heatmap

---

## 13. SYSTEM ACTIVE BUTTON

### Purpose
**Indicates**: System health and connectivity

**States**:
- 🟢 **Active**: All systems operational
- 🟡 **Warning**: Degraded performance
- 🔴 **Error**: System issues

**Click Action**: Opens system status modal

**Modal Shows**:
- Backend connection status
- YOLO model status
- Active cameras count
- Active recordings count
- System logs

---

## 14. REAL-TIME UPDATES

### How It Works
**Technology**: WebSocket connections

**Update Types**:
1. **Dashboard Stats**: Every 2 seconds
2. **Camera Status**: Immediate on change
3. **Notifications**: Immediate push
4. **Recording Status**: Immediate
5. **Detection Alerts**: Immediate

**Frontend Hook**: `useRealTimeData()`

**Backend**: `websocket_manager.py`

---

## 15. STORAGE MANAGEMENT

### Automatic Tracking
**Monitors**:
- Total storage used
- Per-directory usage
- File count
- Growth rate

### Cleanup (Future)
**Will include**:
- Auto-delete old recordings
- Configurable retention
- Low-storage alerts

---

This guide covers all functionalities. For technical implementation details, see `ARCHITECTURE.md`.