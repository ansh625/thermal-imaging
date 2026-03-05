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
  token: localStorage.getItem('token') || null,

  // 🔐 Set auth on login
  setAuth: (user, token) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));

    set({ user, token });
  },

  // ✅ NEW: Update user (for profile updates)
  setUser: (updatedUser) =>
    set((state) => {
      const newUser = {
        ...state.user,
        ...updatedUser,
      };

      // Update localStorage also
      localStorage.setItem('user', JSON.stringify(newUser));

      return { user: newUser };
    }),

  // 🚪 Logout
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');

    set({ user: null, token: null });
  },
}));