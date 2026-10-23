// Shared types for the Discord-clone SPA.
// These mirror the JSON shapes returned by the /api routes in modules/.

export interface User {
  id: number;
  username: string;
  display_name: string;
  avatar_color: string;
}

export interface ServerPublic {
  id: number;
  name: string;
  icon_color: string;
  owner_id: number;
  invite_code: string;
}

export interface ChannelPublic {
  id: number;
  server_id: number;
  name: string;
  topic: string;
  is_private: boolean;
  position: number;
}

export interface MemberView {
  user: User;
  nickname: string;
  role: string;
  role_color: string;
}

export interface RoleView {
  id: number;
  name: string;
  color: string;
  permissions: number;
  permission_names: string[];
}

export interface MessagePublic {
  id: number;
  channel_id: number;
  author_id: number | null;
  author_bot_id: number | null;
  content: string;
  type: number;
  created_at: string | null;
  edited_at: string | null;
}

export interface BotPublic {
  id: number;
  owner_id: number;
  name: string;
  description: string;
  is_enabled: boolean;
}

export interface BotTokenView {
  id: number;
  label: string;
  prefix: string;
  revoked: boolean;
  last_used_at: string | null;
}
