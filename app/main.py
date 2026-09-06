from fastapi import FastAPI, Depends, Query, Path, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.database import get_db, Base, engine, Patient
from app.schemas import PatientCreate, PatientUpdate, PatientOut, APIResponse
from app import crud

app = FastAPI(title="Voice AI Patient Registration API", version="1.0.0")
templates = Jinja2Templates(directory="app/templates")

# Seed initial demonstration patient
@app.on_event("startup")
def startup_populate_seed():
    db = next(get_db())
    if not crud.get_patients(db):
        seed_patient = PatientCreate(
            first_name="Jane",
            last_name="Doe",
            date_of_birth="04/15/1988",
            sex="Female",
            phone_number="5551234567",
            email="jane.doe@example.com",
            address_line_1="100 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
            insurance_provider="BlueCross",
            insurance_member_id="BC998231",
            preferred_language="English"
        )
        crud.create_patient(db, seed_patient)

# --- Standardized REST API Endpoints ---

@app.get("/patients", response_model=APIResponse)
def list_patients(
    last_name: Optional[str] = Query(None),
    date_of_birth: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    patients = crud.get_patients(db, last_name=last_name, dob=date_of_birth, phone=phone_number)
    data = [PatientOut.from_orm(p).model_dump() for p in patients]
    return APIResponse(data=data, error=None)

@app.get("/patients/{patient_id}", response_model=APIResponse)
def get_patient(patient_id: str = Path(...), db: Session = Depends(get_db)):
    patient = crud.get_patient_by_id(db, patient_id)
    if not patient:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse(data=None, error=f"Patient with ID {patient_id} not found").model_dump()
        )
    return APIResponse(data=PatientOut.from_orm(patient).model_dump(), error=None)

@app.post("/patients", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    try:
        patient = crud.create_patient(db, payload)
        return APIResponse(data=PatientOut.from_orm(patient).model_dump(), error=None)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=APIResponse(data=None, error=str(e)).model_dump()
        )

@app.put("/patients/{patient_id}", response_model=APIResponse)
def update_patient(patient_id: str, payload: PatientUpdate, db: Session = Depends(get_db)):
    updated = crud.update_patient(db, patient_id, payload)
    if not updated:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse(data=None, error=f"Patient with ID {patient_id} not found").model_dump()
        )
    return APIResponse(data=PatientOut.from_orm(updated).model_dump(), error=None)

@app.delete("/patients/{patient_id}", response_model=APIResponse)
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    success = crud.soft_delete_patient(db, patient_id)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse(data=None, error=f"Patient with ID {patient_id} not found").model_dump()
        )
    return APIResponse(data={"message": f"Patient {patient_id} soft deleted successfully"}, error=None)

# --- Voice Agent Webhook Integration (Vapi / Retell Tool Server) ---

@app.post("/webhook/vapi")
async def handle_vapi_tools(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    message = payload.get("message", {})
    
    if message.get("type") == "tool-calls":
        tool_calls = message.get("toolCalls", [])
        results = []
        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name")
            args = json.loads(function.get("arguments", "{}")) if isinstance(function.get("arguments"), str) else function.get("arguments", {})

            if name == "check_existing_patient":
                phone = args.get("phone_number")
                existing = crud.get_patient_by_phone(db, phone)
                if existing:
                    results.append({
                        "toolCallId": call.get("id"),
                        "result": json.dumps({"exists": True, "first_name": existing.first_name, "last_name": existing.last_name, "patient_id": existing.patient_id})
                    })
                else:
                    results.append({"toolCallId": call.get("id"), "result": json.dumps({"exists": False})})

            elif name == "register_patient":
                try:
                    patient_in = PatientCreate(**args)
                    created = crud.create_patient(db, patient_in)
                    results.append({
                        "toolCallId": call.get("id"),
                        "result": json.dumps({"success": True, "patient_id": created.patient_id, "first_name": created.first_name})
                    })
                except Exception as e:
                    results.append({
                        "toolCallId": call.get("id"),
                        "result": json.dumps({"success": False, "error": str(e)})
                    })

        return JSONResponse(content={"results": results})
    return JSONResponse(content={"status": "ignored"})

# --- Dashboard Web UI ---

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    patients = crud.get_patients(db)
    return templates.TemplateResponse("dashboard.html", {"request": request, "patients": patients})
