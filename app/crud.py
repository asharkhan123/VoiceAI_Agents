from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import Patient
from app.schemas import PatientCreate, PatientUpdate

def get_patients(
    db: Session,
    last_name: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    phone_number: Optional[str] = None,
    include_deleted: bool = False
) -> List[Patient]:
    query = db.query(Patient)
    if not include_deleted:
        query = query.filter(Patient.deleted_at == None)
    if last_name:
        query = query.filter(Patient.last_name.ilike(f"%{last_name}%"))
    if date_of_birth:
        query = query.filter(Patient.date_of_birth == date_of_birth)
    if phone_number:
        query = query.filter(Patient.phone_number == phone_number)
    return query.order_by(Patient.created_at.desc()).all()

def get_patient_by_id(db: Session, patient_id: str, include_deleted: bool = False) -> Optional[Patient]:
    query = db.query(Patient).filter(Patient.patient_id == patient_id)
    if not include_deleted:
        query = query.filter(Patient.deleted_at == None)
    return query.first()

def get_patient_by_phone(db: Session, phone_number: str, include_deleted: bool = False) -> Optional[Patient]:
    query = db.query(Patient).filter(Patient.phone_number == phone_number)
    if not include_deleted:
        query = query.filter(Patient.deleted_at == None)
    return query.first()

def create_patient(db: Session, patient_in: PatientCreate) -> Patient:
    patient_data = patient_in.model_dump()
    db_patient = Patient(**patient_data)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

def update_patient(db: Session, db_patient: Patient, update_in: PatientUpdate) -> Patient:
    update_data = update_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_patient, field, value)
    db_patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_patient)
    return db_patient

def soft_delete_patient(db: Session, db_patient: Patient) -> Patient:
    db_patient.deleted_at = datetime.utcnow()
    db.commit()
    return db_patient