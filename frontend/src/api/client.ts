// frontend/src/api/client.ts
const API_BASE = "http://localhost:8080";


// Define a custom error type
export class ApiError extends Error {
    status: number;
    data?: unknown;

    constructor(status: number, message: string, data?: unknown) {
        super(message);
        this.status = status;
        this.data = data;
        this.name = 'ApiError';
    }
}

export async function apiClient<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`;

    const response = await fetch(url, {
        ...options,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
    });
    if (response.status === 401) {
        if (!endpoint.includes('/auth/me')) {
            window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        }
        throw new ApiError(401, 'Unauthorized');
    };
    // If 204 No Content, return empty object
    if (response.status === 204) {
        return {} as T;
    }
    let data: any = {};
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
    data = await response.json();
    }
    if (!response.ok) {
        throw new ApiError(
            response.status,
            data.detail || `HTTP error ${response.status}`,
            data
        );
    }
    return data as T;
};