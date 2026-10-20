import axios from "axios";

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface Topic {
  id: number;
  name: string;
  description: string | null;
}

const api = axios.create({
  baseURL: "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }

  return config;
});

export async function loginUser(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const credentials = new URLSearchParams({ username: email, password });
  const response = await api.post<LoginResponse>("/auth/login", credentials, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  return response.data;
}

export async function getTopics(): Promise<Topic[]> {
  const response = await api.get<Topic[]>("/topics/");
  return response.data;
}

export default api;
