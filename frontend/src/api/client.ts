const API_BASE = "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Course {
  id: number;
  name: string;
}

export const api = {
  courses: {
    list: () => request<Course[]>("/courses"),
    get: (id: number) => request<Course>(`/courses/${id}`),
    create: (name: string) =>
      request<Course>("/courses", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    update: (id: number, name: string) =>
      request<Course>(`/courses/${id}`, {
        method: "PUT",
        body: JSON.stringify({ name }),
      }),
    delete: (id: number) =>
      request<void>(`/courses/${id}`, { method: "DELETE" }),
  },
};
