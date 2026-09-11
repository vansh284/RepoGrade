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

export interface DashboardRow {
  student_name: string;
  github_username: string;
  student_db_id: number;
  clone_status: string;
  repo_url: string;
  evaluator_grade_total: number | null;
}

export interface EvaluatorGradeInput {
  grading_component_id: number;
  score: number;
}

export interface EvaluatorGradeOut {
  id: number;
  submission_id: number;
  grading_component_id: number;
  component_name: string;
  score: number;
}

export interface GradeImportResult {
  imported: number;
  errors: ImportRowError[];
}

export interface CloneProgress {
  total: number;
  completed: number;
  failed: number;
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
  submissions: {
    clone: (courseId: number, assignmentId: number) =>
      request<CloneProgress>(
        `/courses/${courseId}/assignments/${assignmentId}/clone`,
        { method: "POST" },
      ),
    dashboard: (
      courseId: number,
      assignmentId: number,
      params?: { status?: string; search?: string; sort?: string; order?: string },
    ) => {
      const q = new URLSearchParams();
      if (params?.status) q.set("status", params.status);
      if (params?.search) q.set("search", params.search);
      if (params?.sort) q.set("sort", params.sort);
      if (params?.order) q.set("order", params.order);
      const qs = q.toString();
      return request<DashboardRow[]>(
        `/courses/${courseId}/assignments/${assignmentId}/dashboard${qs ? `?${qs}` : ""}`,
      );
    },
    progress: (courseId: number, assignmentId: number) =>
      request<CloneProgress>(
        `/courses/${courseId}/assignments/${assignmentId}/clone/progress`,
      ),
  },
  grades: {
    get: (courseId: number, assignmentId: number, studentDbId: number) =>
      request<EvaluatorGradeOut[]>(
        `/courses/${courseId}/assignments/${assignmentId}/students/${studentDbId}/grades`,
      ),
    submit: (
      courseId: number,
      assignmentId: number,
      studentDbId: number,
      grades: EvaluatorGradeInput[],
    ) =>
      request<EvaluatorGradeOut[]>(
        `/courses/${courseId}/assignments/${assignmentId}/students/${studentDbId}/grades`,
        {
          method: "PUT",
          body: JSON.stringify({ grades }),
        },
      ),
    import: async (
      courseId: number,
      assignmentId: number,
      file: File,
    ): Promise<GradeImportResult> => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(
        `${API_BASE}/courses/${courseId}/assignments/${assignmentId}/grades/import`,
        { method: "POST", body: form },
      );
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${res.status}: ${detail}`);
      }
      return res.json();
    },
    exportUrl: (courseId: number, assignmentId: number) =>
      `${API_BASE}/courses/${courseId}/assignments/${assignmentId}/grades/export`,
  },
};
