// API client for the Discord-clone example.
//
// Centralizes endpoint URLs, JSON shaping, error handling, and the CSRF token
// that every state-changing request must carry. The token is fetched once from
// /api/auth/csrf-token and cached here; call fetchCsrf() on app start.
import type {
  User,
  ServerPublic,
  ChannelPublic,
  MemberView,
  RoleView,
  MessagePublic,
  BotPublic,
  BotTokenView,
} from "./types.ts";

let csrfToken: string | null = null;

export function setCsrf(token: string): void {
  csrfToken = token;
}

export async function fetchCsrf(): Promise<string> {
  const res = await fetch("/api/auth/csrf-token");
  if (!res.ok) throw new Error("Could not fetch CSRF token");
  const data = await res.json();
  csrfToken = data.token;
  return data.token;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (body !== undefined && csrfToken) headers["x-csrf-token"] = csrfToken;
  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const message = (data && (data.detail || data.message)) || `Request failed (${res.status})`;
    throw new ApiError(res.status, message);
  }
  return data as T;
}

// --------------------------------------------------------------------------- //
// Auth
// --------------------------------------------------------------------------- //
export const auth = {
  me: () => request<{ user: User }>("GET", "/api/auth/me"),
  register: (username: string, email: string, password: string) =>
    request<{ user: User }>("POST", "/api/auth/register", { username, email, password }),
  login: (username: string, password: string) =>
    request<{ user: User }>("POST", "/api/auth/login", { username, password }),
  logout: () => request<{ ok: boolean }>("POST", "/api/auth/logout"),
  updateProfile: (patch: { display_name?: string; avatar_color?: string }) =>
    request<{ user: User }>("PATCH", "/api/auth/profile", patch),
};

// --------------------------------------------------------------------------- //
// Servers, channels, roles, members
// --------------------------------------------------------------------------- //
// NOTE: module root routes mount with a trailing slash, so collection endpoints
// use "/api/servers/" / "/api/bots/".
export const servers = {
  list: () => request<{ items: ServerPublic[] }>("GET", "/api/servers/"),
  create: (name: string) => request<{ server: ServerPublic }>("POST", "/api/servers/", { name }),
  get: (id: number) =>
    request<{ server: ServerPublic; permissions: string[] }>("GET", `/api/servers/${id}`),
  join: (invite_code: string) =>
    request<{ server: ServerPublic }>("POST", "/api/servers/join", { invite_code }),
  members: (id: number) => request<{ items: MemberView[] }>("GET", `/api/servers/${id}/members`),
  channels: (id: number) =>
    request<{ items: ChannelPublic[] }>("GET", `/api/servers/${id}/channels`),
  createChannel: (id: number, payload: { name: string; topic?: string; is_private?: boolean }) =>
    request<{ channel: ChannelPublic }>("POST", `/api/servers/${id}/channels`, payload),
  roles: (id: number) => request<{ items: RoleView }>("GET", `/api/servers/${id}/roles`),
  createRole: (
    id: number,
    payload: { name: string; permissions?: number; color?: string },
  ) => request<{ role: RoleView }>("POST", `/api/servers/${id}/roles`, payload),
};

// --------------------------------------------------------------------------- //
// Messages
// --------------------------------------------------------------------------- //
export const messages = {
  history: (channelId: number, before?: number, limit?: number) => {
    const q: Record<string, string> = {};
    if (before) q.before = String(before);
    if (limit) q.limit = String(limit);
    const qs = new URLSearchParams(q).toString();
    return request<{ items: MessagePublic[] }>(
      "GET",
      `/api/channels/${channelId}/messages?${qs}`,
    );
  },
  send: (channelId: number, content: string) =>
    request<{ message: MessagePublic; bot_messages: MessagePublic[] }>(
      "POST",
      `/api/channels/${channelId}/messages`,
      { content },
    ),
  remove: (channelId: number, messageId: number) =>
    request<{ ok: boolean }>("DELETE", `/api/channels/${channelId}/messages/${messageId}`),
};

// --------------------------------------------------------------------------- //
// Bot platform
// --------------------------------------------------------------------------- //
export const bots = {
  list: () => request<{ items: BotPublic[] }>("GET", "/api/bots/"),
  create: (name: string, description?: string) =>
    request<{ bot: BotPublic; token: string }>("POST", "/api/bots/", { name, description }),
  remove: (id: number) => request<{ ok: boolean }>("DELETE", `/api/bots/${id}`),
  joinServer: (id: number, server_id: number) =>
    request<{ ok: boolean }>("POST", `/api/bots/${id}/join`, { server_id }),
  tokens: (id: number) => request<{ items: BotTokenView[] }>("GET", `/api/bots/${id}/tokens`),
  createToken: (id: number, label?: string) =>
    request<{ token: string; prefix: string }>("POST", `/api/bots/${id}/tokens`, { label }),
  revokeToken: (id: number, tokenId: number) =>
    request<{ ok: boolean }>("DELETE", `/api/bots/${id}/tokens/${tokenId}`),
  createCommand: (
    id: number,
    payload: { name: string; description?: string; parameters?: unknown[]; is_enabled?: boolean },
  ) => request<{ command: { id: number; name: string; enabled: boolean } }>(
    "POST",
    `/api/bots/${id}/commands`,
    payload,
  ),
  createSubscription: (id: number, payload: { event_type: string; is_enabled?: boolean }) =>
    request<{ ok: boolean }>("POST", `/api/bots/${id}/subscriptions`, payload),
  invoke: (id: number, payload: { channel_id: number; command: string; args?: string[] }) =>
    request<{ invocation: Record<string, unknown>; messages: MessagePublic[] }>(
      "POST",
      `/api/bots/${id}/invoke`,
      payload,
    ),
};
