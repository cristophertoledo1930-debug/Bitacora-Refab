import uuid
from datetime import datetime, time, date
from decimal import Decimal
from zoneinfo import ZoneInfo
from pathlib import Path
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Header, Form, Request, HTTPException, status, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from lab_hub.config import get_settings
from lab_hub.db.session import get_db
from lab_hub.db.models import WasteType, Material, Machine, Cause, WasteRecord
from lab_hub.api.schemas import CatalogsResponse, WasteRecordCreate, WasteRecordResponse
from lab_hub.services.records import (
    create_waste_record,
    resolve_qr_token,
    ValidationError,
    ConflictError,
)

settings = get_settings()
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


@router.get("/r/{token}", response_class=HTMLResponse)
def get_qr_form(request: Request, token: str, db: Session = Depends(get_db)):
    """Serves the mobile registration form for an authorized QR token."""
    qr_ctx = resolve_qr_token(db, token)
    if not qr_ctx:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"message": "Código QR no válido, no configurado o revocado."},
            status_code=status.HTTP_404_NOT_FOUND
        )

    waste_types = db.query(WasteType).filter(WasteType.is_active.is_(True)).order_by(WasteType.name).all()
    materials = db.query(Material).filter(Material.is_active.is_(True)).order_by(Material.name).all()
    machines = db.query(Machine).filter(Machine.is_active.is_(True)).order_by(Machine.name).all()
    causes = db.query(Cause).filter(Cause.is_active.is_(True)).order_by(Cause.name).all()

    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={
            "token": token,
            "qr_label": qr_ctx.label,
            "waste_types": waste_types,
            "materials": materials,
            "machines": machines,
            "causes": causes,
            "selected_waste_type": str(qr_ctx.waste_type_id) if qr_ctx.waste_type_id else "",
            "selected_material": str(qr_ctx.material_id) if qr_ctx.material_id else "",
            "selected_machine": str(qr_ctx.machine_id) if qr_ctx.machine_id else "",
            "selected_cause": str(qr_ctx.cause_id) if qr_ctx.cause_id else "",
            "weight": "",
            "unit": "g",
            "idempotency_key": str(uuid.uuid4()),
            "error": None
        }
    )


@router.post("/r/{token}", response_class=HTMLResponse)
def post_qr_form(
    request: Request,
    token: str,
    waste_type_id: str = Form(...),
    material_id: str = Form(...),
    machine_id: str = Form(...),
    cause_id: str = Form(...),
    weight: str = Form(...),
    unit: str = Form("g"),
    idempotency_key: str = Form(...),
    db: Session = Depends(get_db)
):
    """Processes mobile form submission and preserves input if validation fails."""
    qr_ctx = resolve_qr_token(db, token)
    if not qr_ctx:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"message": "Código QR no válido o revocado."},
            status_code=status.HTTP_404_NOT_FOUND
        )

    try:
        record, was_created = create_waste_record(
            db,
            idempotency_key=idempotency_key,
            qr_token=token,
            waste_type_id=uuid.UUID(waste_type_id),
            material_id=uuid.UUID(material_id),
            machine_id=uuid.UUID(machine_id),
            cause_id=uuid.UUID(cause_id),
            weight_str=weight,
            unit=unit,
            source="manual"
        )
        local_time = record.recorded_at.astimezone(settings.timezone).strftime("%Y-%m-%d %H:%M:%S")
        return templates.TemplateResponse(
            request=request,
            name="success.html",
            context={
                "token": token,
                "record": record,
                "recorded_at_local": local_time
            }
        )
    except (ValidationError, ConflictError, ValueError) as exc:
        waste_types = db.query(WasteType).filter(WasteType.is_active.is_(True)).order_by(WasteType.name).all()
        materials = db.query(Material).filter(Material.is_active.is_(True)).order_by(Material.name).all()
        machines = db.query(Machine).filter(Machine.is_active.is_(True)).order_by(Machine.name).all()
        causes = db.query(Cause).filter(Cause.is_active.is_(True)).order_by(Cause.name).all()

        return templates.TemplateResponse(
            request=request,
            name="form.html",
            context={
                "token": token,
                "qr_label": qr_ctx.label,
                "waste_types": waste_types,
                "materials": materials,
                "machines": machines,
                "causes": causes,
                "selected_waste_type": waste_type_id,
                "selected_material": material_id,
                "selected_machine": machine_id,
                "selected_cause": cause_id,
                "weight": weight,
                "unit": unit,
                "idempotency_key": idempotency_key,
                "error": str(exc)
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


@router.get("/api/v1/catalogs", response_model=CatalogsResponse)
def get_catalogs(db: Session = Depends(get_db)):
    """Returns all active catalog items."""
    return CatalogsResponse(
        waste_types=db.query(WasteType).filter(WasteType.is_active.is_(True)).order_by(WasteType.name).all(),
        materials=db.query(Material).filter(Material.is_active.is_(True)).order_by(Material.name).all(),
        machines=db.query(Machine).filter(Machine.is_active.is_(True)).order_by(Machine.name).all(),
        causes=db.query(Cause).filter(Cause.is_active.is_(True)).order_by(Cause.name).all(),
    )


@router.post("/api/v1/records", response_model=WasteRecordResponse)
def post_record(
    payload: WasteRecordCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db)
):
    """
    Records waste entry with idempotency protection.
    Returns 201 Created on new insertion, 200 OK on idempotent retry, 409 Conflict on payload mismatch.
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Falta la cabecera requerida 'Idempotency-Key'."
        )

    try:
        record, was_created = create_waste_record(
            db,
            idempotency_key=idempotency_key,
            qr_token=payload.qr_token,
            waste_type_id=payload.waste_type_id,
            material_id=payload.material_id,
            machine_id=payload.machine_id,
            cause_id=payload.cause_id,
            weight_str=payload.weight,
            unit=payload.unit,
            source=payload.source
        )
        status_code = status.HTTP_201_CREATED if was_created else status.HTTP_200_OK
        return JSONResponse(
            status_code=status_code,
            content={
                "id": str(record.id),
                "recorded_at": record.recorded_at.isoformat(),
                "weight_g": str(record.weight_g),
                "waste_type_id": str(record.waste_type_id),
                "material_id": str(record.material_id),
                "machine_id": str(record.machine_id),
                "cause_id": str(record.cause_id),
                "source": record.source,
                "idempotency_key": record.idempotency_key
            }
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": exc.message, "field": exc.field}
        )
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message
        )


from datetime import date
from sqlalchemy import and_
from lab_hub.api.auth import require_admin
from lab_hub.services.aggregations import get_aggregations


@router.get("/api/v1/stats")
def get_stats(
    start_date: date | None = None,
    end_date: date | None = None,
    waste_type_id: uuid.UUID | None = None,
    material_id: uuid.UUID | None = None,
    machine_id: uuid.UUID | None = None,
    cause_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _admin: bool = Depends(require_admin)
):
    """Returns aggregated metrics and charts series. Protected by admin session/key."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="Rango de fechas inválido.")
    return get_aggregations(
        db,
        start_date=start_date,
        end_date=end_date,
        waste_type_id=waste_type_id,
        material_id=material_id,
        machine_id=machine_id,
        cause_id=cause_id
    )


@router.get("/api/v1/records")
def list_records(
    start_date: date | None = None,
    end_date: date | None = None,
    waste_type_id: uuid.UUID | None = None,
    material_id: uuid.UUID | None = None,
    machine_id: uuid.UUID | None = None,
    cause_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
    _admin: bool = Depends(require_admin)
):
    """Returns paginated and filtered waste records. Protected by admin session/key."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="Rango de fechas inválido.")
    filters = []
    if start_date:
        start_utc = datetime.combine(start_date, time.min, tzinfo=settings.timezone).astimezone(ZoneInfo("UTC"))
        filters.append(WasteRecord.recorded_at >= start_utc)
    if end_date:
        end_utc = datetime.combine(end_date + relativedelta(days=1), time.min, tzinfo=settings.timezone).astimezone(ZoneInfo("UTC"))
        filters.append(WasteRecord.recorded_at < end_utc)
    if waste_type_id:
        filters.append(WasteRecord.waste_type_id == waste_type_id)
    if material_id:
        filters.append(WasteRecord.material_id == material_id)
    if machine_id:
        filters.append(WasteRecord.machine_id == machine_id)
    if cause_id:
        filters.append(WasteRecord.cause_id == cause_id)

    query = db.query(WasteRecord)
    if filters:
        query = query.filter(and_(*filters))

    total = query.count()
    records = query.order_by(WasteRecord.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for r in records:
        local_recorded = r.recorded_at.astimezone(settings.timezone).strftime("%Y-%m-%d %H:%M:%S")
        items.append({
            "id": str(r.id),
            "recorded_at": r.recorded_at.isoformat(),
            "recorded_at_local": local_recorded,
            "waste_type": r.waste_type.name if r.waste_type else "",
            "material": r.material.name if r.material else "",
            "machine": r.machine.name if r.machine else "",
            "cause": r.cause.name if r.cause else "",
            "weight_g": str(r.weight_g),
            "weight_kg": str((r.weight_g / Decimal("1000")).quantize(Decimal("0.001"))),
            "source": r.source,
            "idempotency_key": r.idempotency_key
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size > 0 else 1,
        "items": items
    }


from fastapi.responses import FileResponse
from lab_hub.db.models import ReportRun, ReportDelivery


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: Session = Depends(get_db), _admin: bool = Depends(require_admin)):
    return templates.TemplateResponse(request=request, name="reports.html", context={
        "reports": list_reports(db, True),
        "current_period": datetime.now(settings.timezone).strftime("%Y-%m"),
    })


@router.post("/reports/generate")
def generate_report(request: Request, period: str = Form(...), db: Session = Depends(get_db), _admin: bool = Depends(require_admin)):
    from lab_hub.jobs.monthly_report import process_monthly_report
    from fastapi.responses import RedirectResponse
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=403, detail="Origen no permitido.")
    try:
        parsed = date.fromisoformat(period + "-01")
        if len(period) != 7 or parsed > datetime.now(settings.timezone).date().replace(day=1):
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=422, detail="Periodo inválido.")
    process_monthly_report(db, period)
    return RedirectResponse("/reports", status_code=303)


@router.get("/api/v1/reports")
def list_reports(db: Session = Depends(get_db), _admin: bool = Depends(require_admin)):
    """Lists generated report runs and their delivery statuses. Protected by admin session/key."""
    runs = db.query(ReportRun).order_by(ReportRun.period.desc(), ReportRun.revision.desc()).all()
    out = []
    for r in runs:
        delivs = [
            {
                "recipient": d.recipient,
                "status": d.status,
                "attempts": d.attempts,
                "error": d.error_summary,
                "message_id": d.message_id
            }
            for d in r.deliveries
        ]
        out.append({
            "id": str(r.id),
            "period": r.period,
            "revision": r.revision,
            "status": r.status,
            "generated_at": r.generated_at.isoformat(),
            "pdf_available": bool(r.pdf_path and Path(r.pdf_path).exists()),
            "deliveries": delivs
        })
    return out


@router.get("/api/v1/reports/{report_id}/pdf")
def download_report_pdf(report_id: uuid.UUID, db: Session = Depends(get_db), _admin: bool = Depends(require_admin)):
    """Securely downloads generated report PDF. Protected by admin session/key."""
    run = db.query(ReportRun).filter(ReportRun.id == report_id).first()
    if not run or not run.pdf_path or not Path(run.pdf_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Informe PDF no encontrado.")

    filename = Path(run.pdf_path).name
    return FileResponse(
        path=run.pdf_path,
        media_type="application/pdf",
        filename=filename
    )
