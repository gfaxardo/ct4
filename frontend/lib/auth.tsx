/**
 * Contexto de Autenticación
 * Maneja el estado de login, token y usuario
 */

'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';

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

export interface LoginResponse {
  accessToken: string;
  user: User;
}

export interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

// Auth API URL - usa el backend como proxy
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
const AUTH_API_URL = `${API_BASE_URL}/api/v1/auth/login`;

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
    if (!state.isLoading && !state.isAuthenticated && pathname !== '/login') {
      router.push('/login');
    }
  }, [state.isLoading, state.isAuthenticated, pathname, router]);

  // Login
  const login = useCallback(async (credentials: LoginCredentials): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(AUTH_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          success: false,
          error: errorData.error || 'Credenciales incorrectas',
        };
      }

      const data: LoginResponse = await response.json();

      // Guardar en localStorage
      localStorage.setItem(TOKEN_KEY, data.accessToken);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));

      // Actualizar estado
      setState({
        user: data.user,
        accessToken: data.accessToken,
        isAuthenticated: true,
        isLoading: false,
      });

      // Redirigir al dashboard
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
