/**
 * CampusOps AI Authentication & Authorization Types
 */

export type UserRole = "student" | "support" | "admin";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  avatar_url: string | null;
  created_at: string;
}

export interface AuthSuccessResponse {
  user: User;
  message?: string;
}

export interface ApiErrorResponse {
  detail: string | { msg: string; type: string }[];
}

