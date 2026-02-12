import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
});

// LOGIN (OAuth2 compliant)
export const authAPI = {
  login: ({ username, password }) => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    return API.post("/api/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
  },

  signup: (data) =>
    API.post("/api/auth/signup", data),

  me: (token) =>
    API.get("/api/auth/me", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
};
// ================= CAMERA =================
export const cameraAPI = {
  connect: (data, token) =>
    API.post("/api/camera/connect", data, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),

  disconnect: (session_id, token) =>
    API.post(
      "/api/camera/disconnect",
      { session_id },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    ),
};