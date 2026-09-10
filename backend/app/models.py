from sqlalchemy import Column, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    students = relationship("Student", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_course_student_id"),)

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    student_id = Column(String, nullable=False)
    email = Column(String, nullable=False)
    github_username = Column(String, nullable=False)

    course = relationship("Course", back_populates="students")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    github_repo_name = Column(String, nullable=False)
    checks_directory = Column(String, nullable=False)
    evaluator_weight = Column(Float, nullable=False)
    peer_weight = Column(Float, nullable=False)

    course = relationship("Course", back_populates="assignments")
    grading_components = relationship("GradingComponent", back_populates="assignment", cascade="all, delete-orphan")
    environment_variables = relationship("EnvironmentVariable", back_populates="assignment", cascade="all, delete-orphan")


class GradingComponent(Base):
    __tablename__ = "grading_components"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    max_points = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)

    assignment = relationship("Assignment", back_populates="grading_components")


class EnvironmentVariable(Base):
    __tablename__ = "environment_variables"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)

    assignment = relationship("Assignment", back_populates="environment_variables")
