import { create } from 'zustand';

export const useCameraStore = create((set) => ({
  sessionId: null,
  connected: false,
  currentFrame: null,
  
  setSession: (sessionId) => set({ sessionId, connected: true }),
  setFrame: (frame) => set({ currentFrame: frame }),
  disconnect: () => set({ sessionId: null, connected: false, currentFrame: null }),
}));