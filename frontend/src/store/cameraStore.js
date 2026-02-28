import { create } from 'zustand';

export const useCameraStore = create((set) => ({
  sessionId: null,
  connected: false,
  currentFrame: null,
  detectionEnabled: false,
  confidence: 0.5,

  setSession: (sessionId) => {
    console.log('cameraStore: setSession called with:', sessionId);
    set({ sessionId, connected: true });
    console.log('cameraStore: sessionId set, connected=true');
  },
  setFrame: (frame) => set({ currentFrame: frame }),
  disconnect: () => {
    console.log('cameraStore: disconnect called');
    set({ sessionId: null, connected: false, currentFrame: null });
  },
  setDetectionEnabled: (enabled) => set({ detectionEnabled: enabled }),
  setConfidence: (confidence) => set({ confidence: confidence }),
}));