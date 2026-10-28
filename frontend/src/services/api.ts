import axios from "axios";

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
}

export interface UserResponse {
  id: string;
  name: string;
  email: string;
  role: "admin" | "teacher" | "student";
}

export async function registerUser(data: RegisterData): Promise<UserResponse> {
  const response = await api.post<UserResponse>("/auth/register", data);
  return response.data;
}

export interface Topic {
  id: number;
  name: string;
  description: string | null;
}

const api = axios.create({
  baseURL: "http://localhost:8000",
});

function isPublicAuthRequest(url?: string): boolean {
  const path = new URL(url ?? "", api.defaults.baseURL).pathname.replace(/\/$/, "");
  return path === "/auth/login" || path === "/auth/register";
}

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("token");

    if (token && !isPublicAuthRequest(config.url)) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      typeof window !== "undefined" &&
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      !isPublicAuthRequest(error.config?.url)
    ) {
      const token = window.localStorage.getItem("token");
      // A delayed rejection of an old token must not clear a newer login.
      // Removing the token also makes simultaneous 401s redirect only once.
      if (token && error.config?.headers.Authorization === `Bearer ${token}`) {
        window.localStorage.removeItem("token");
        window.location.replace("/login?session=expired");
      }
    }
    return Promise.reject(error);
  },
);

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

export type GameMode = "TRIVIAL" | "PASAPALABRA";

export async function getTopics(mode?: GameMode): Promise<Topic[]> {
  const response = await api.get<Topic[]>("/topics/", { params: mode ? { mode } : undefined });
  return response.data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await api.get<UserResponse>("/auth/me");
  return response.data;
}

export interface GameHistorySummary {
  id: number;
  topic_id: number;
  game_mode: GameMode;
  score: number;
  is_completed: boolean;
  created_at: string;
  question_ids: number[];
}

export async function getRecentGames(): Promise<GameHistorySummary[]> {
  const response = await api.get<GameHistorySummary[]>("/game/history", {
    params: { limit: 5 },
  });
  return response.data;
}

export default api;
