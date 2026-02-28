import { create } from 'zustand';

function getStoredUser() {
  const userStr = localStorage.getItem('user');
  try {
    return userStr ? JSON.parse(userStr) : null;
  } catch {
    return null;
  }
}

export const useAuthStore = create((set) => ({
  user: getStoredUser(),
  token: localStorage.getItem('token'),

  setAuth: (user, token) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    set({ user, token });
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({ user: null, token: null });
  },
}));