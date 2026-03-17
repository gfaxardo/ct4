/**
 * Cliente HTTP base para la API.
 * En desarrollo o si la app se abre en localhost → backend local (puerto 8000).
 * En producción (build) y dominio real → NEXT_PUBLIC_API_BASE_URL (api-ct4.yego.pro).
 */

function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') return 'http://localhost:8000';
  }
  if (typeof process !== 'undefined' && process.env.NODE_ENV === 'development') return 'http://localhost:8000';
  return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
}

export const API_BASE_URL = getApiBaseUrl();

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public detail?: string
  ) {
    super(detail || statusText);
    this.name = 'ApiError';
  }
}

export async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.message;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, response.statusText, detail);
  }

  const contentType = response.headers.get('content-type');
  if (!contentType || !contentType.includes('application/json')) {
    return {} as T;
  }
  return response.json();
}

export async function fetchApiFormData<T>(
  path: string,
  formData: FormData
): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.message;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, response.statusText, detail);
  }
  return response.json();
}
