# Video Detection Performance Overview

## Overview

Thermal Polaris captures live thermal camera frames and overlays YOLO detections while keeping the stream responsive. The current design uses cached detection results and asynchronous persistence to avoid blocking the main streaming loop.

## Goals

- Keep live stream smooth
- Preserve stable detection overlays
- Avoid blocking YOLO inference in the main loop
- Enable smart event recording and screenshot capture
- Support both CPU-only and GPU-assisted environments

## Current Design

The backend sends frames to the frontend over `/ws/video/{session_id}`. Detection is executed on a subset of frames, and the most recent detections are cached and reused for subsequent frames.

### Design principles

- Detection runs in a controlled interval to reduce CPU load.
- Cached detection overlays are sent with every frame.
- Detection results are saved in background worker threads.
- Smart recording buffers pre-event frames and finalizes clips after event activity.

## How It Works

1. The frontend opens a WebSocket to `/ws/video/{session_id}`.
2. Backend captures camera frames from `camera_handler`.
3. Every few frames, YOLO inference runs and updates the session cache.
4. Cached bounding boxes are drawn on each frame and sent to the client.
5. Detection records are persisted asynchronously and screenshots are generated when needed.

## Benefits

- Smooth live video streaming
- Stable overlays that do not blink between detection cycles
- Better responsiveness for connected clients
- Reduced impact from database writes and file I/O
- Support for smart recording and screenshot features without interrupting stream delivery

## Smart Recording

Smart recording uses a pre-event frame buffer and keeps recording after the last detection for a configurable post-event duration. This saves storage by only writing clips around real events.

### Smart recording features

- Pre-event buffer for context before detections
- Post-event tail recording after detections stop
- Automatic clip finalization
- Storage cleanup via `/api/smart-recording/cleanup`
- Smart clips listed under `/api/smart-recording/clips`

## API Support

- `GET /ws/video/{session_id}`: live video stream frames
- `GET /api/detection/list`: detection history
- `POST /api/screenshot/capture`: save a screenshot from the live stream
- `POST /api/smart-recording/cleanup`: cleanup old clips
- `GET /api/smart-recording/clips`: list smart event clips

## Practical Tips

- Use detection only when needed to maximize FPS.
- Tune confidence thresholds for your environment.
- Use dashboard stats and notifications for workflow visibility.
- Run manual cleanup or configure smart recording storage limits to avoid stale clips.

## Notes

This implementation prioritizes user experience by separating frame delivery from heavier detection and persistence tasks. Cached detection overlays and asynchronous writes provide a stable, real-time viewing experience while keeping the system extensible for future optimization.
