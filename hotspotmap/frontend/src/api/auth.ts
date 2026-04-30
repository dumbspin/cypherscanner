export type AuthUser = {
  id: string;
  name: string;
  email: string;
};

type AuthResponse =
  | { success: true; token: string; user: AuthUser }
  | { success: false; message?: string };

const API_BASE =
  (import.meta as any).env?.VITE_HOTSPOT_BACKEND_BASE_URL || "";

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    credentials: "include",
  });
  return (await res.json()) as AuthResponse;
}

export async function register(name: string, email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
    credentials: "include",
  });
  return (await res.json()) as AuthResponse;
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  }).catch(() => {});
}

