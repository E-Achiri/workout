import { getIdToken } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestOptions {
  method?: string;
  body?: unknown;
  requireAuth?: boolean;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, requireAuth = true } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (requireAuth) {
    const token = await getIdToken();
    if (!token) {
      throw new Error("Not authenticated");
    }
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }

  return response.json();
}

// API functions
export interface Message {
  id: number;
  message: string;
  created_at: string;
}

export interface MessagesResponse {
  messages: Message[];
}

export interface UserInfo {
  id: number;
  email: string;
  cognito_sub: string;
}

export async function getMe(): Promise<UserInfo> {
  return request<UserInfo>("/auth/me");
}

export async function getMessages(): Promise<MessagesResponse> {
  return request<MessagesResponse>("/messages");
}

export async function createMessage(message: string): Promise<Message> {
  return request<Message>("/messages", {
    method: "POST",
    body: { message },
  });
}

export async function healthCheck(): Promise<{ status: string; message: string }> {
  return request("/", { requireAuth: false });
}
