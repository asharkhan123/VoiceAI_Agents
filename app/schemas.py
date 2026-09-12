from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator
from app.database import SexEnum

# Generic Response Wrapper
class APIResponse(BaseModel):
    data: Optional[Any] = None
    error: Optional[str] = None

# Patient Validation Base
class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    date_of_birth: str = Field(..., pattern=r"^\d{2}/\d{2}/\d{4}$")
    sex: SexEnum
    phone_number: str = Field(..., pattern=r"^\d{10}$")
    email: Optional[str] = Field(None, max_length=120)
    address_line_1: str = Field(..., min_length=1, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$")
    insurance_provider: Optional[str] = Field(None, max_length=100)
    insurance_member_id: Optional[str] = Field(None, max_length=50)
    preferred_language: Optional[str] = Field("English", max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, pattern=r"^\d{10}$")

    @field_validator("state")
    def validate_state(cls, v):
        states = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
        }
        if v.upper() not in states:
            raise ValueError(f"Invalid US state code: {v}")
        return v.upper()

class PatientCreate(PatientBase):
    pass

class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    date_of_birth: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$")
    sex: Optional[SexEnum] = None
    phone_number: Optional[str] = Field(None, pattern=r"^\d{10}$")
    email: Optional[str] = Field(None, max_length=120)
    address_line_1: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, pattern=r"^\d{5}(-\d{4})?$")
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

class PatientOut(PatientBase):
    patient_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True