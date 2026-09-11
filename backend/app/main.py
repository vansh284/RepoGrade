from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes.assignments import router as assignments_router
from app.routes.courses import router as courses_router
from app.routes.students import router as students_router
from app.routes.backup import router as backup_router
from app.routes.submissions import router as submissions_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RepoGrade")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses_router)
app.include_router(students_router)
app.include_router(assignments_router)
app.include_router(submissions_router)
app.include_router(backup_router)
