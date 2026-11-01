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

export interface GameQuestion {
  id: number;
  text: string;
  options: string[] | null;
  question_type: GameMode;
  letter: string | null;
}

export interface GameSessionStart {
  session_id: number;
  topic_id: number;
  questions: GameQuestion[];
  content_context: GameContentContext | null;
}

export interface GameContentContext {
  selection: {
    category_id: number | null;
    category_name: string | null;
    difficulty: number | null;
    difficulty_unknown: boolean;
  };
  questions: {
    question_id: number;
    category_id: number | null;
    category_name: string | null;
    difficulty: number | null;
  }[];
}

export interface GameAvailability {
  topic_id: number;
  game_mode: GameMode;
  total_questions: number;
  combinations: { category_id: number | null; category_name: string | null; difficulty: number | null; count: number }[];
}

export interface TrivialFilters {
  category_id?: number;
  difficulty?: number;
  difficulty_unknown?: boolean;
}

export async function getTrivialAvailability(topicId: number): Promise<GameAvailability> {
  const response = await api.get<GameAvailability>(`/game/availability/${topicId}`, {
    params: { mode: "TRIVIAL" },
  });
  return response.data;
}

export async function startTrivialGame(topicId: number, filters: TrivialFilters = {}): Promise<GameSessionStart> {
  const response = await api.post<GameSessionStart>(`/game/start/${topicId}`, null, {
    params: { mode: "TRIVIAL", ...filters },
  });
  return response.data;
}

export interface TrivialAnswer {
  question_id: number;
  selected_index: number;
  response_time_ms?: number;
}

export interface GameCorrection {
  question_id: number;
  selected_index: number | null;
  correct_option_index: number | null;
  is_correct: boolean;
}

export interface GameResult {
  score: number;
  total_questions: number;
  corrections: GameCorrection[];
}

export async function submitTrivialGame(sessionId: number, answers: TrivialAnswer[]): Promise<GameResult> {
  try {
    const response = await api.post<GameResult>(`/game/submit/${sessionId}`, { answers });
    return response.data;
  } catch (error: unknown) {
    if (!axios.isAxiosError(error) || error.response?.status !== 409) throw error;
    // A previous submission may have succeeded even if its response was lost.
    const { data } = await api.get<GameHistorySummary & { answer_logs: GameCorrection[] }>(`/game/history/${sessionId}`);
    if (!data.is_completed) throw error;
    return {
      score: data.score,
      total_questions: data.question_ids.length,
      corrections: data.answer_logs,
    };
  }
}

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
  content_context: GameContentContext | null;
}

export interface AnswerHistory {
  question_id: number;
  question_text: string;
  question_type: GameMode;
  options: string[] | null;
  letter: string | null;
  selected_index: number | null;
  text_answer: string | null;
  correct_option_index: number | null;
  exact_word: string | null;
  accepted_answers: string[] | null;
  is_correct: boolean;
  response_time_ms: number | null;
  answered_at: string;
}

export interface GameHistoryDetail extends GameHistorySummary {
  answer_logs: AnswerHistory[];
}

export async function getRecentGames(): Promise<GameHistorySummary[]> {
  const response = await api.get<GameHistorySummary[]>("/game/history", {
    params: { limit: 5 },
  });
  return response.data;
}

export interface ActivityCounts {
  started: number;
  completed: number;
  unfinished: number;
}

export interface GameProgress extends ActivityCounts {
  by_mode: Record<GameMode, ActivityCounts>;
}

export async function getGameProgress(): Promise<GameProgress> {
  const response = await api.get<GameProgress>("/game/progress");
  return response.data;
}

export async function getHistoryPage(skip: number, limit: number): Promise<GameHistorySummary[]> {
  const response = await api.get<GameHistorySummary[]>("/game/history", { params: { skip, limit } });
  return response.data;
}

export async function getGameHistoryDetail(sessionId: number): Promise<GameHistoryDetail> {
  const response = await api.get<GameHistoryDetail>(`/game/history/${sessionId}`);
  return response.data;
}

export default api;
