import json
from typing import Optional
from fastapi import FastAPI, Depends, Query, Path, Request, status
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.schemas import PatientCreate, PatientUpdate, PatientOut, APIResponse
from app import crud

app = FastAPI(title="Voice AI Patient Registration API", version="1.0.0")

# Root redirect to Dashboard
@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/dashboard")

# Seed initial demonstration patient safely without locking SQLite
@app.on_event("startup")
def startup_populate_seed():
    db = SessionLocal()
    try:
        existing = crud.get_patients(db)
        if not existing:
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
    finally:
        db.close()

# --- Standardized REST API Endpoints ---

@app.get("/patients", response_model=APIResponse)
def list_patients(
    last_name: Optional[str] = Query(None),
    date_of_birth: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    patients = crud.get_patients(
        db,
        last_name=last_name,
        date_of_birth=date_of_birth,
        phone_number=phone_number
    )
    data = [PatientOut.model_validate(p).model_dump() for p in patients]
    return APIResponse(data=data, error=None)

@app.get("/patients/{patient_id}", response_model=APIResponse)
def get_patient(patient_id: str = Path(...), db: Session = Depends(get_db)):
    patient = crud.get_patient_by_id(db, patient_id)
    if not patient:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse(data=None, error=f"Patient with ID {patient_id} not found").model_dump()
        )
    return APIResponse(data=PatientOut.model_validate(patient).model_dump(), error=None)

@app.post("/patients", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    try:
        patient = crud.create_patient(db, payload)
        return APIResponse(data=PatientOut.model_validate(patient).model_dump(), error=None)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=APIResponse(data=None, error=str(e)).model_dump()
        )

@app.put("/patients/{patient_id}", response_model=APIResponse)
def update_patient(patient_id: str, payload: PatientUpdate, db: Session = Depends(get_db)):
    db_patient = crud.get_patient_by_id(db, patient_id)
    if not db_patient:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse(data=None, error=f"Patient with ID {patient_id} not found").model_dump()
        )
    updated = crud.update_patient(db, db_patient, payload)
    return APIResponse(data=PatientOut.model_validate(updated).model_dump(), error=None)

@app.delete("/patients/{patient_id}", response_model=APIResponse)
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    db_patient = crud.get_patient_by_id(db, patient_id)
    if not db_patient:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse(data=None, error=f"Patient with ID {patient_id} not found").model_dump()
        )
    crud.soft_delete_patient(db, db_patient)
    return APIResponse(data={"message": f"Patient {patient_id} soft deleted successfully"}, error=None)

# --- Voice Agent Webhook Integration (Vapi Tool Server) ---

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

# --- Dashboard Web UI (Self-Contained, Zero-Hang) ---

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(db: Session = Depends(get_db)):
    patients = crud.get_patients(db)
    
    rows = ""
    for p in patients:
        sex_str = p.sex.value if hasattr(p.sex, 'value') else str(p.sex)
        rows += f"""
        <tr style="border-bottom: 1px solid #334155;">
            <td style="padding: 12px; font-weight: 600;">{p.first_name} {p.last_name}</td>
            <td style="padding: 12px; font-size: 11px; color: #94a3b8;">{p.patient_id}</td>
            <td style="padding: 12px;">{p.phone_number}</td>
            <td style="padding: 12px;">{p.date_of_birth} ({sex_str})</td>
            <td style="padding: 12px;">{p.city}, {p.state} {p.zip_code}</td>
        </tr>
        """
        
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Patient Registration Dashboard</title>
        <style>
            body {{ background-color: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 30px; margin: 0; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid #334155; padding-bottom: 16px; }}
            table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }}
            th {{ background: #334155; padding: 12px; text-align: left; font-size: 13px; color: #cbd5e1; }}
            button {{ background: #4f46e5; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; }}
            button:hover {{ background: #4338ca; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h2 style="margin: 0 0 6px 0;">Voice AI Patient Intake Records</h2>
                    <span style="font-size: 13px; color: #94a3b8;">Live SQLite Data Feed</span>
                </div>
                <button onclick="location.reload()">Refresh Data</button>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Full Name</th>
                        <th>Patient ID</th>
                        <th>Phone</th>
                        <th>DOB (Sex)</th>
                        <th>Address</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="5" style="padding: 24px; text-align: center; color: #94a3b8;">No registered patients found.</td></tr>'}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """