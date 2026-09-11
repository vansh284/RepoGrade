from pydantic import BaseModel


# ── Course ───────────────────────────────────────────────────────


class CourseCreate(BaseModel):
    name: str


CourseUpdate = CourseCreate


class CourseOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ── Grading Component ───────────────────────────────────────────


class GradingComponentCreate(BaseModel):
    name: str
    max_points: int
    weight: float


GradingComponentUpdate = GradingComponentCreate


class GradingComponentOut(BaseModel):
    id: int
    name: str
    max_points: int
    weight: float

    model_config = {"from_attributes": True}


# ── Environment Variable ────────────────────────────────────────


class EnvVarCreate(BaseModel):
    key: str
    value: str


EnvVarUpdate = EnvVarCreate


class EnvVarOut(BaseModel):
    id: int
    key: str
    value: str

    model_config = {"from_attributes": True}


# ── Assignment ──────────────────────────────────────────────────


class AssignmentCreate(BaseModel):
    name: str
    github_repo_name: str
    checks_directory: str
    evaluator_weight: float
    peer_weight: float
    grading_components: list[GradingComponentCreate] = []
    environment_variables: list[EnvVarCreate] = []


AssignmentUpdate = AssignmentCreate


class AssignmentOut(BaseModel):
    id: int
    name: str
    github_repo_name: str
    checks_directory: str
    evaluator_weight: float
    peer_weight: float
    grading_components: list[GradingComponentOut] = []
    environment_variables: list[EnvVarOut] = []

    model_config = {"from_attributes": True}


# ── Student ─────────────────────────────────────────────────────


class StudentCreate(BaseModel):
    name: str
    student_id: str
    email: str
    github_username: str


StudentUpdate = StudentCreate


class StudentOut(BaseModel):
    id: int
    course_id: int
    name: str
    student_id: str
    email: str
    github_username: str

    model_config = {"from_attributes": True}


class ImportRowError(BaseModel):
    row: int
    error: str


class ImportResult(BaseModel):
    imported: int
    errors: list[ImportRowError]


# ── Submission ─────────────────────────────────────────────────


class SubmissionOut(BaseModel):
    id: int
    student_id: int
    assignment_id: int
    repo_url: str
    clone_status: str
    clone_path: str | None

    model_config = {"from_attributes": True, "use_enum_values": True}


class DashboardRow(BaseModel):
    student_name: str
    github_username: str
    student_db_id: int
    clone_status: str
    repo_url: str
    evaluator_grade_total: float | None = None
    peer_grade_average: float | None = None

    model_config = {"from_attributes": True}


class CloneProgress(BaseModel):
    total: int
    completed: int
    failed: int


# ── Check Result ───────────────────────────────────────────────


class CheckResultOut(BaseModel):
    id: int
    submission_id: int
    check_name: str
    passed: bool
    message: str
    details: str
    stderr: str

    model_config = {"from_attributes": True}


class CheckProgress(BaseModel):
    total: int
    completed: int


class DashboardCheckResult(BaseModel):
    check_name: str
    passed: bool
    message: str
    details: str
    stderr: str


class DashboardRowWithChecks(DashboardRow):
    check_results: list[DashboardCheckResult] = []


# ── Evaluator Grades ──────────────────────────────────────────


class EvaluatorGradeInput(BaseModel):
    grading_component_id: int
    score: float


class EvaluatorGradeSubmit(BaseModel):
    grades: list[EvaluatorGradeInput]


class EvaluatorGradeOut(BaseModel):
    id: int
    submission_id: int
    grading_component_id: int
    component_name: str
    score: float

    model_config = {"from_attributes": True}


class GradeImportResult(BaseModel):
    imported: int
    errors: list[ImportRowError]


# ── Email Template ────────────────────────────────────────────


class EmailTemplateCreate(BaseModel):
    name: str
    subject_template: str
    body_template: str


EmailTemplateUpdate = EmailTemplateCreate


class EmailTemplateOut(BaseModel):
    id: int
    assignment_id: int
    name: str
    subject_template: str
    body_template: str

    model_config = {"from_attributes": True}


class EmailPreview(BaseModel):
    subject: str
    body: str


class BatchSendResult(BaseModel):
    sent: int
    failed: int
    errors: list[str] = []


# ── App Settings / Backup ──────────────────────────────────────


class AppSettingOut(BaseModel):
    key: str
    value: str

    model_config = {"from_attributes": True}


class BackupInfo(BaseModel):
    filename: str
    created_at: str
    size_bytes: int


class BackupResult(BaseModel):
    filename: str
    path: str


class RestoreResult(BaseModel):
    message: str


# ── Peer Assignment / Evaluation ─────────────────────────────


class PeerAssignmentOut(BaseModel):
    id: int
    assignment_id: int
    evaluator_id: int
    evaluator_name: str
    evaluee_id: int
    evaluee_name: str
    repo_url: str

    model_config = {"from_attributes": True}


class PeerEmailSendRequest(BaseModel):
    subject: str
    body: str


class PeerEvaluationOut(BaseModel):
    id: int
    peer_assignment_id: int
    grading_component_id: int
    component_name: str
    score: float
    feedback: str

    model_config = {"from_attributes": True}


class PeerEvalImportResult(BaseModel):
    imported: int
    errors: list[ImportRowError]
