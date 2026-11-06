# main.py — FastAPI app: API endpoints + frontend serve karna
# THIS FILE connects website to Python code!
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth
import models
from database import Base, SessionLocal, engine, get_db


# ========== STARTUP (server chalte hi) ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) Database tables banao (agar pehli run hai to school.db banti hai)
    Base.metadata.create_all(bind=engine)

    # 2) Demo admin seed karo — taake pehla login kaam kare
    db = SessionLocal()
    try:
        if not db.query(models.User).first():
            db.add(models.User(
                school_name="Demo Public School",
                email="admin@demo.com",
                hashed_password=auth.hash_password("demo123"),
            ))
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title="AI Smart School API", lifespan=lifespan)

# CORS: doosre ports/domains se bhi API call ho sake (deployment ke liye)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== SCHEMAS (request/response ka shape) ==========
# Pydantic automatically validate karta hai: missing/wrong data → 422 error

class UserRegister(BaseModel):
    school_name: str = "My School"
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    school_name: str
    email: str
    model_config = {"from_attributes": True}  # ORM object → JSON


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class StudentIn(BaseModel):
    name: str
    roll_no: str
    parent_contact: str = ""
    class_id: Optional[int] = None


class TeacherIn(BaseModel):
    name: str
    subject: str = ""
    email: str = ""


class ClassIn(BaseModel):
    name: str
    section: str = ""


class AttendanceIn(BaseModel):
    student_id: int
    status: str  # "present" ya "absent"
    date: Optional[str] = None  # "2026-11-06" — na dein to aaj maan lo


# ========== HELPERS (DB object → JSON dict) ==========
def student_out(s: models.Student) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "roll_no": s.roll_no,
        "parent_contact": s.parent_contact,
        "class_id": s.class_id,
        "class_name": s.classroom.name if s.classroom else None,
    }


def class_out(c: models.ClassRoom) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "section": c.section,
        "student_count": len(c.students),
    }


def teacher_out(t: models.Teacher) -> dict:
    return {"id": t.id, "name": t.name, "subject": t.subject, "email": t.email}


# ========== AUTH ==========
@app.post("/api/auth/register", response_model=TokenOut)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(400, "Yeh email pehle se registered hai")

    user = models.User(
        school_name=data.school_name,
        email=data.email,
        hashed_password=auth.hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "access_token": auth.create_access_token(user.id),
        "token_type": "bearer",
        "user": user,
    }


@app.post("/api/auth/login", response_model=TokenOut)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user or not auth.verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Email ya password ghalat hai")
    return {
        "access_token": auth.create_access_token(user.id),
        "token_type": "bearer",
        "user": user,
    }


@app.get("/api/auth/me", response_model=UserOut)
def me(user: models.User = Depends(auth.get_current_user)):
    return user


# ========== STUDENTS CRUD ==========
@app.get("/api/students")
def list_students(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    return [student_out(s) for s in db.query(models.Student).all()]


@app.post("/api/students")
def create_student(
    data: StudentIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    if data.class_id and not db.get(models.ClassRoom, data.class_id):
        raise HTTPException(404, "Yeh class exist nahi karti")
    s = models.Student(**data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return student_out(s)


@app.put("/api/students/{student_id}")
def update_student(
    student_id: int,
    data: StudentIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    s = db.get(models.Student, student_id)
    if not s:
        raise HTTPException(404, "Student mila hi nahi")
    for field, value in data.model_dump().items():
        setattr(s, field, value)
    db.commit()
    return student_out(s)


@app.delete("/api/students/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    s = db.get(models.Student, student_id)
    if not s:
        raise HTTPException(404, "Student mila hi nahi")
    db.delete(s)  # cascade: attendance records bhi delete ho jate
    db.commit()
    return {"ok": True}


# ========== TEACHERS CRUD ==========
@app.get("/api/teachers")
def list_teachers(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    return [teacher_out(t) for t in db.query(models.Teacher).all()]


@app.post("/api/teachers")
def create_teacher(
    data: TeacherIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    t = models.Teacher(**data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return teacher_out(t)


@app.put("/api/teachers/{teacher_id}")
def update_teacher(
    teacher_id: int,
    data: TeacherIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    t = db.get(models.Teacher, teacher_id)
    if not t:
        raise HTTPException(404, "Teacher mila hi nahi")
    for field, value in data.model_dump().items():
        setattr(t, field, value)
    db.commit()
    return teacher_out(t)


@app.delete("/api/teachers/{teacher_id}")
def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    t = db.get(models.Teacher, teacher_id)
    if not t:
        raise HTTPException(404, "Teacher mila hi nahi")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ========== CLASSES CRUD ==========
@app.get("/api/classes")
def list_classes(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    return [class_out(c) for c in db.query(models.ClassRoom).all()]


@app.post("/api/classes")
def create_class(
    data: ClassIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    c = models.ClassRoom(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return class_out(c)


@app.put("/api/classes/{class_id}")
def update_class(
    class_id: int,
    data: ClassIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    c = db.get(models.ClassRoom, class_id)
    if not c:
        raise HTTPException(404, "Class mila hi nahi")
    for field, value in data.model_dump().items():
        setattr(c, field, value)
    db.commit()
    return class_out(c)


@app.delete("/api/classes/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    c = db.get(models.ClassRoom, class_id)
    if not c:
        raise HTTPException(404, "Class mila hi nahi")
    db.delete(c)
    db.commit()
    return {"ok": True}


# ========== ATTENDANCE ==========
@app.get("/api/attendance")
def list_attendance(
    date_str: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    att_date = date.fromisoformat(date_str) if date_str else date.today()
    records = db.query(models.Attendance).filter(models.Attendance.date == att_date).all()
    return [
        {"student_id": a.student_id, "date": a.date.isoformat(), "status": a.status}
        for a in records
    ]


@app.post("/api/attendance")
def mark_attendance(
    data: AttendanceIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    if data.status not in ("present", "absent"):
        raise HTTPException(400, "Status 'present' ya 'absent' hona chahiye")

    att_date = date.fromisoformat(data.date) if data.date else date.today()

    # UPSERT: agar aaj ke liye entry already hai to UPDATE karo, warna naye INSERT
    rec = db.query(models.Attendance).filter(
        models.Attendance.student_id == data.student_id,
        models.Attendance.date == att_date,
    ).first()
    if rec:
        rec.status = data.status
    else:
        db.add(models.Attendance(student_id=data.student_id, date=att_date, status=data.status))
    db.commit()
    return {"student_id": data.student_id, "date": att_date.isoformat(), "status": data.status}


# ========== DASHBOARD ==========
@app.get("/api/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    today = date.today()
    present_count = db.query(models.Attendance).filter(
        models.Attendance.date == today, models.Attendance.status == "present"
    ).count()
    marked_count = db.query(models.Attendance).filter(
        models.Attendance.date == today
    ).count()
    recent = db.query(models.Student).order_by(models.Student.id.desc()).limit(5).all()

    return {
        "students": db.query(models.Student).count(),
        "teachers": db.query(models.Teacher).count(),
        "classes": db.query(models.ClassRoom).count(),
        "present": present_count,
        "marked": marked_count,
        "recent_students": [student_out(s) for s in recent],
    }


# ========== FRONTEND SERVE (sabse aakhri line!) ==========
# http://127.0.0.1:8000 khologe to directly website khul jayegi
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
