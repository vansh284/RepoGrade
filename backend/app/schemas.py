from pydantic import BaseModel


# ── Course ───────────────────────────────────────────────────────


class CourseCreate(BaseModel):
    name: str


class CourseUpdate(BaseModel):
    name: str


class CourseOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ── Grading Component ───────────────────────────────────────────


class GradingComponentCreate(BaseModel):
    name: str
    max_points: int
    weight: float


class GradingComponentUpdate(BaseModel):
    name: str
    max_points: int
    weight: float


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


class EnvVarUpdate(BaseModel):
    key: str
    value: str


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


class AssignmentUpdate(BaseModel):
    name: str
    github_repo_name: str
    checks_directory: str
    evaluator_weight: float
    peer_weight: float
    grading_components: list[GradingComponentCreate] = []
    environment_variables: list[EnvVarCreate] = []


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


class StudentCreate(BaseModel):
    name: str
    student_id: str
    email: str
    github_username: str


class StudentUpdate(BaseModel):
    name: str
    student_id: str
    email: str
    github_username: str


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
