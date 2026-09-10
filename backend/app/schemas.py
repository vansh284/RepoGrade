from pydantic import BaseModel


class CourseCreate(BaseModel):
    name: str


class CourseUpdate(BaseModel):
    name: str


class CourseOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
