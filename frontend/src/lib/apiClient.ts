/**
 * Centralized API client for CaseClock frontend.
 *
 * Provides a single `apiFetch()` wrapper that:
 * - Attaches Content-Type header by default
 * - Normalizes HTTP errors into typed Error objects
 * - Is ready to attach auth tokens when the backend provides them
 *
 * All hooks MUST use this instead of raw fetch(), so that:
 * - Error messages are consistent
 * - Auth header can be added in one place
 * - Base URL is configurable via environment variable
 *
 * Do NOT invent endpoints here. Only provide transport infrastructure.
 */

export class ApiError extends Error {
  readonly status: number
  readonly statusText: string

  constructor(status: number, statusText: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
  let fullUrl = path.startsWith('http') ? path : `${baseUrl}${path}`
  const savedRole = localStorage.getItem('caseclock_role') || 'IO'

  const method = (options?.method || 'GET').toUpperCase()
  const isMutating = method !== 'GET' && method !== 'HEAD'

  // If GET/HEAD and 'role=' is not already in the query string, automatically attach ?role= or &role=
  if (!isMutating && !fullUrl.includes('role=')) {
    const separator = fullUrl.includes('?') ? '&' : '?'
    fullUrl = `${fullUrl}${separator}role=${encodeURIComponent(savedRole)}`
  }

  // GET/HEAD: send no custom headers so Chrome makes a simple request (no preflight).
  // The backend DevelopmentVerifier/DemoVerifier reads role from the ?role= query param.
  // Mutating methods: send Content-Type + X-Dev-Role so the backend knows the role.
  const headers: Record<string, string> = {
    ...(isMutating ? { 'Content-Type': 'application/json', 'X-Dev-Role': savedRole } : {}),
    ...(options?.headers as Record<string, string> | undefined),
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers,
  })

  if (!response.ok) {
    // Normalize all HTTP errors to ApiError with consistent shape
    let message: string
    try {
      const body = await response.json() as { detail?: string; message?: string }
      message = body.detail ?? body.message ?? response.statusText
    } catch {
      message = response.statusText
    }
    throw new ApiError(response.status, response.statusText, message)
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
