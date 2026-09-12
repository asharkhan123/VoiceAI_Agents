import enum
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./patients.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class SexEnum(str, enum.Enum):
    Male = "Male"
    Female = "Female"
    Other = "Other"
    DeclineToAnswer = "Decline to Answer"

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_of_birth = Column(String(10), nullable=False)
    sex = Column(SAEnum(SexEnum), nullable=False)
    phone_number = Column(String(10), nullable=False, index=True)
    email = Column(String(120), nullable=True)
    address_line_1 = Column(String(255), nullable=False)
    address_line_2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)
    insurance_provider = Column(String(100), nullable=True)
    insurance_member_id = Column(String(50), nullable=True)
    preferred_language = Column(String(50), default="English", nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()