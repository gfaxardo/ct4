/**
 * Contexto de Autenticación
 * Maneja el estado de login, token y usuario
 */

'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';

// En el navegador usamos siempre el proxy (/api/auth/login) para evitar CORS.
// El servidor Next (route api/auth/login) reenvía a api-int.yego.pro.
const AUTH_API_URL =
  typeof window !== 'undefined'
    ? '/api/auth/login'
    : (process.env.NEXT_PUBLIC_AUTH_API_URL ?? 'https://api-int.yego.pro/api/auth/login');

// Types
export interface User {
  id: number;
  username: string;
  email: string;
  name: string;
  role: string;
  moduleId: number | null;
  active: boolean;
  lastLogin: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

/** Respuesta posible de la API de login (acepta snake_case o camelCase). */
interface LoginApiResponse {
  access_token?: string;
  accessToken?: string;
  token?: string;
  user?: Partial<User> & { username?: string; email?: string; name?: string };
}

export interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

// Storage keys
const TOKEN_KEY = 'ct4_access_token';
const USER_KEY = 'ct4_user';

// Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isLoading: true,
  });

  const router = useRouter();
  const pathname = usePathname();

  // Cargar sesión al iniciar
  useEffect(() => {
    const loadSession = () => {
      try {
        const token = localStorage.getItem(TOKEN_KEY);
        const userStr = localStorage.getItem(USER_KEY);

        if (token && userStr) {
          const user = JSON.parse(userStr) as User;
          setState({
            user,
            accessToken: token,
            isAuthenticated: true,
            isLoading: false,
          });
        } else {
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error('Error loading session:', error);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    loadSession();
  }, []);

  // Redirigir si no está autenticado
  useEffect(() => {
    const isLoginPage = pathname === '/login' || pathname === '/login/';
    if (!state.isLoading && !state.isAuthenticated && !isLoginPage) {
      router.push('/login');
    }
  }, [state.isLoading, state.isAuthenticated, pathname, router]);

  // Login — POST a https://api-int.yego.pro/api/auth/login con { username, password }
  const login = useCallback(async (credentials: LoginCredentials): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(AUTH_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: credentials.username,
          password: credentials.password,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData.error ?? errorData.message ?? errorData.detail ?? 'Credenciales incorrectas';
        return { success: false, error: typeof message === 'string' ? message : 'Credenciales incorrectas' };
      }

      const data = (await response.json()) as LoginApiResponse;
      const token = data.access_token ?? data.accessToken ?? data.token;

      if (!token) {
        return { success: false, error: 'La API no devolvió un token de acceso.' };
      }

      const user: User = data.user && typeof data.user === 'object'
        ? {
            id: Number((data.user as Record<string, unknown>).id) || 0,
            username: String((data.user as Record<string, unknown>).username ?? credentials.username),
            email: String((data.user as Record<string, unknown>).email ?? ''),
            name: String((data.user as Record<string, unknown>).name ?? credentials.username),
            role: String((data.user as Record<string, unknown>).role ?? 'user'),
            moduleId: typeof (data.user as Record<string, unknown>).moduleId === 'number' ? (data.user as Record<string, unknown>).moduleId as number : null,
            active: (data.user as Record<string, unknown>).active !== false,
            lastLogin: new Date().toISOString(),
          }
        : {
            id: 0,
            username: credentials.username,
            email: '',
            name: credentials.username,
            role: 'user',
            moduleId: null,
            active: true,
            lastLogin: new Date().toISOString(),
          };

      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      setState({
        user,
        accessToken: token,
        isAuthenticated: true,
        isLoading: false,
      });

      router.push('/dashboard');
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: 'Error de conexión. Por favor intenta de nuevo.',
      };
    }
  }, [router]);

  // Logout
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);

    setState({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
    });

    router.push('/login');
  }, [router]);

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

// Helper para obtener el token (útil para API calls)
export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

// Helper para verificar si está autenticado
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem(TOKEN_KEY);
}
