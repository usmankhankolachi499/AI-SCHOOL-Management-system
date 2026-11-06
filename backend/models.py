# models.py — Database ki tables (design) yahan define hoti hain
# Har class = Database ki 1 table (sheet). Har variable = 1 column.

from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """Login users (school admin). Har school ka apna admin account."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    school_name = Column(String, default="My School")
    email = Column(String, unique=True, index=True, nullable=False)
    # Password KABHI plain text me save nahi hota — iska hash (encoded
    # fingerprint) save hota hai. Yeh security ka rule #1 hai.
    hashed_password = Column(String, nullable=False)


class ClassRoom(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)      # e.g. "Class 5"
    section = Column(String, default="")       # e.g. "A"

    # RELATIONSHIP: 1 class me multiple students ho sakte hain
    students = relationship("Student", back_populates="classroom")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    roll_no = Column(String, nullable=False)
    parent_contact = Column(String, default="")

    # RELATIONSHIP: student ka link uski class se (class_id = classes.id)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    classroom = relationship("ClassRoom", back_populates="students")

    # Student delete ho to uski attendance bhi delete ho jaye (cascade)
    attendance = relationship(
        "Attendance", back_populates="student", cascade="all, delete-orphan"
    )


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subject = Column(String, default="")
    email = Column(String, default="")


class Attendance(Base):
    __tablename__ = "attendance"

    # Rule: 1 student ki 1 din me sirf 1 attendance entry ho sakti hai
    __table_args__ = (UniqueConstraint("student_id", "date"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False)    # "present" ya "absent"

    student = relationship("Student", back_populates="attendance")
