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

export interface Student {
  id: number;
  course_id: number;
  name: string;
  student_id: string;
  email: string;
  github_username: string;
}

export interface ImportRowError {
  row: number;
  error: string;
}

export interface ImportResult {
  imported: number;
  errors: ImportRowError[];
}

export interface GradingComponent {
  id: number;
  name: string;
  max_points: number;
  weight: number;
}

export interface GradingComponentInput {
  name: string;
  max_points: number;
  weight: number;
}

export interface EnvVar {
  id: number;
  key: string;
  value: string;
}

export interface EnvVarInput {
  key: string;
  value: string;
}

export interface Assignment {
  id: number;
  name: string;
  github_repo_name: string;
  checks_directory: string;
  evaluator_weight: number;
  peer_weight: number;
  grading_components: GradingComponent[];
  environment_variables: EnvVar[];
}

export interface AssignmentInput {
  name: string;
  github_repo_name: string;
  checks_directory: string;
  evaluator_weight: number;
  peer_weight: number;
  grading_components: GradingComponentInput[];
  environment_variables: EnvVarInput[];
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
  students: {
    list: (courseId: number) =>
      request<Student[]>(`/courses/${courseId}/students`),
    get: (courseId: number, id: number) =>
      request<Student>(`/courses/${courseId}/students/${id}`),
    create: (courseId: number, data: Omit<Student, "id" | "course_id">) =>
      request<Student>(`/courses/${courseId}/students`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (courseId: number, id: number, data: Omit<Student, "id" | "course_id">) =>
      request<Student>(`/courses/${courseId}/students/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (courseId: number, id: number) =>
      request<void>(`/courses/${courseId}/students/${id}`, { method: "DELETE" }),
    import: async (courseId: number, file: File): Promise<ImportResult> => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/courses/${courseId}/students/import`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${res.status}: ${detail}`);
      }
      return res.json();
    },
    exportUrl: (courseId: number) =>
      `${API_BASE}/courses/${courseId}/students/export`,
  },
  assignments: {
    list: (courseId: number) =>
      request<Assignment[]>(`/courses/${courseId}/assignments`),
    get: (courseId: number, id: number) =>
      request<Assignment>(`/courses/${courseId}/assignments/${id}`),
    create: (courseId: number, data: AssignmentInput) =>
      request<Assignment>(`/courses/${courseId}/assignments`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (courseId: number, id: number, data: AssignmentInput) =>
      request<Assignment>(`/courses/${courseId}/assignments/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (courseId: number, id: number) =>
      request<void>(`/courses/${courseId}/assignments/${id}`, { method: "DELETE" }),
  },
};
