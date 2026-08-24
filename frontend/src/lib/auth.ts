import api from "./api";
import type {
  ApiResponse,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  User,
} from "@/types";

export async function login(credentials: LoginRequest): Promise<User> {
  const response = await api.post<ApiResponse<TokenResponse>>(
    "/auth/login",
    credentials
  );

  const token = response.data.data.access_token;

  localStorage.setItem("access_token", token);

  return getCurrentUser();
}

export async function register(
  data: RegisterRequest
): Promise<User> {
  await api.post("/auth/register", {
    ...data,
    role: data.role ?? "CUSTOMER",
  });

  return login({
    email: data.email,
    password: data.password,
  });
}

export async function getCurrentUser(): Promise<User> {
  const response = await api.get<ApiResponse<User>>("/auth/me");
  return response.data.data;
}

export function logout(): void {
  localStorage.removeItem("access_token");
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  return Boolean(localStorage.getItem("access_token"));
}