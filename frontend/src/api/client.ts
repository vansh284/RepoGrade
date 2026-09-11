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

export interface DashboardCheckResult {
  check_name: string;
  passed: boolean;
  message: string;
  details: string;
  stderr: string;
}

export interface DashboardRow {
  student_name: string;
  github_username: string;
  student_db_id: number;
  clone_status: string;
  repo_url: string;
  check_results: DashboardCheckResult[];
  evaluator_grade_total: number | null;
  peer_grade_average: number | null;
  final_grade: number | null;
  penalty_count: number;
  penalty_total: number;
}

export interface Penalty {
  id: number;
  submission_id: number;
  reason: string;
  amount: number;
}

export interface PenaltyInput {
  reason: string;
  amount: number;
}

export interface PeerAssignment {
  id: number;
  assignment_id: number;
  evaluator_id: number;
  evaluator_name: string;
  evaluee_id: number;
  evaluee_name: string;
  repo_url: string;
}

export interface PeerEvalImportResult {
  imported: number;
  errors: ImportRowError[];
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

export interface CheckProgress {
  total: number;
  completed: number;
}

export interface EmailTemplate {
  id: number;
  assignment_id: number;
  name: string;
  subject_template: string;
  body_template: string;
}

export interface EmailTemplateInput {
  name: string;
  subject_template: string;
  body_template: string;
}

export interface EmailPreview {
  subject: string;
  body: string;
}

export interface BatchSendResult {
  sent: number;
  failed: number;
  errors: string[];
}

export interface AppSetting {
  key: string;
  value: string;
}

export interface BackupInfo {
  filename: string;
  created_at: string;
  size_bytes: number;
}

export interface BackupResult {
  filename: string;
  path: string;
}

export interface RestoreResult {
  message: string;
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
  checks: {
    run: (courseId: number, assignmentId: number) =>
      request<CheckProgress>(
        `/courses/${courseId}/assignments/${assignmentId}/run-checks`,
        { method: "POST" },
      ),
    progress: (courseId: number, assignmentId: number) =>
      request<CheckProgress>(
        `/courses/${courseId}/assignments/${assignmentId}/check-results/progress`,
      ),
    exportUrl: (courseId: number, assignmentId: number) =>
      `${API_BASE}/courses/${courseId}/assignments/${assignmentId}/check-results/export`,
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
    canvasExportUrl: (courseId: number, assignmentId: number) =>
      `${API_BASE}/courses/${courseId}/assignments/${assignmentId}/canvas-export`,
  },
  penalties: {
    list: (courseId: number, assignmentId: number, studentDbId: number) =>
      request<Penalty[]>(
        `/courses/${courseId}/assignments/${assignmentId}/students/${studentDbId}/penalties`,
      ),
    add: (courseId: number, assignmentId: number, studentDbId: number, data: PenaltyInput) =>
      request<Penalty>(
        `/courses/${courseId}/assignments/${assignmentId}/students/${studentDbId}/penalties`,
        { method: "POST", body: JSON.stringify(data) },
      ),
    update: (courseId: number, assignmentId: number, studentDbId: number, penaltyId: number, data: PenaltyInput) =>
      request<Penalty>(
        `/courses/${courseId}/assignments/${assignmentId}/students/${studentDbId}/penalties/${penaltyId}`,
        { method: "PUT", body: JSON.stringify(data) },
      ),
    delete: (courseId: number, assignmentId: number, studentDbId: number, penaltyId: number) =>
      request<void>(
        `/courses/${courseId}/assignments/${assignmentId}/students/${studentDbId}/penalties/${penaltyId}`,
        { method: "DELETE" },
      ),
  },
  emailTemplates: {
    list: (courseId: number, assignmentId: number) =>
      request<EmailTemplate[]>(
        `/courses/${courseId}/assignments/${assignmentId}/email-templates`,
      ),
    create: (courseId: number, assignmentId: number, data: EmailTemplateInput) =>
      request<EmailTemplate>(
        `/courses/${courseId}/assignments/${assignmentId}/email-templates`,
        { method: "POST", body: JSON.stringify(data) },
      ),
    update: (courseId: number, assignmentId: number, id: number, data: EmailTemplateInput) =>
      request<EmailTemplate>(
        `/courses/${courseId}/assignments/${assignmentId}/email-templates/${id}`,
        { method: "PUT", body: JSON.stringify(data) },
      ),
    delete: (courseId: number, assignmentId: number, id: number) =>
      request<void>(
        `/courses/${courseId}/assignments/${assignmentId}/email-templates/${id}`,
        { method: "DELETE" },
      ),
    preview: (courseId: number, assignmentId: number, templateId: number, studentId: number) =>
      request<EmailPreview>(
        `/courses/${courseId}/assignments/${assignmentId}/email-templates/${templateId}/preview?student_id=${studentId}`,
      ),
    send: (courseId: number, assignmentId: number, templateId: number, checkName: string) =>
      request<BatchSendResult>(
        `/courses/${courseId}/assignments/${assignmentId}/email-templates/${templateId}/send?check_name=${encodeURIComponent(checkName)}`,
        { method: "POST" },
      ),
  },
  settings: {
    getBackupPath: () => request<AppSetting>("/settings/backup-path"),
    setBackupPath: (path: string) =>
      request<AppSetting>("/settings/backup-path", {
        method: "PUT",
        body: JSON.stringify({ path }),
      }),
  },
  backup: {
    create: () => request<BackupResult>("/backup", { method: "POST" }),
    list: () => request<BackupInfo[]>("/backups"),
    restore: (filename: string) =>
      request<RestoreResult>("/restore", {
        method: "POST",
        body: JSON.stringify({ filename }),
      }),
  },
  peerAssignments: {
    generate: (courseId: number, assignmentId: number, count: number = 2) =>
      request<PeerAssignment[]>(
        `/courses/${courseId}/assignments/${assignmentId}/peer-assignments/generate?count=${count}`,
        { method: "POST" },
      ),
    list: (courseId: number, assignmentId: number) =>
      request<PeerAssignment[]>(
        `/courses/${courseId}/assignments/${assignmentId}/peer-assignments`,
      ),
    exportUrl: (courseId: number, assignmentId: number) =>
      `${API_BASE}/courses/${courseId}/assignments/${assignmentId}/peer-assignments/export`,
    sendEmails: (
      courseId: number,
      assignmentId: number,
      subject: string,
      body: string,
    ) =>
      request<BatchSendResult>(
        `/courses/${courseId}/assignments/${assignmentId}/peer-assignments/send-emails`,
        { method: "POST", body: JSON.stringify({ subject, body }) },
      ),
    importEvaluations: async (
      courseId: number,
      assignmentId: number,
      file: File,
    ): Promise<PeerEvalImportResult> => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(
        `${API_BASE}/courses/${courseId}/assignments/${assignmentId}/peer-evaluations/import`,
        { method: "POST", body: form },
      );
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${res.status}: ${detail}`);
      }
      return res.json();
    },
    exportEvaluationsUrl: (courseId: number, assignmentId: number) =>
      `${API_BASE}/courses/${courseId}/assignments/${assignmentId}/peer-evaluations/export`,
  },
};
