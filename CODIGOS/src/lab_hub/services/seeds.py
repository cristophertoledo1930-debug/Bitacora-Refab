import hashlib
from sqlalchemy.orm import Session
from lab_hub.db.models import WasteType, Material, Machine, Cause, QRContext


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def seed_catalogs(db: Session) -> dict[str, dict]:
    """
    Seeds initial synthetic catalogs and returns mapping of codes to objects.
    Idempotent: skips existing codes.
    """
    waste_types_data = [
        {"code": "resin", "name": "Resina"},
        {"code": "laser_cut", "name": "Retazo láser"},
    ]
    materials_data = [
        {"code": "pla", "name": "PLA"},
        {"code": "abs", "name": "ABS"},
        {"code": "acrylic", "name": "Acrílico"},
        {"code": "mdf", "name": "MDF"},
        {"code": "photopolymer", "name": "Fotopolímero"},
    ]
    machines_data = [
        {"code": "laser_cutter_1", "name": "Cortadora Láser #1"},
        {"code": "laser_cutter_2", "name": "Cortadora Láser #2"},
        {"code": "sla_printer_1", "name": "Impresora SLA #1"},
        {"code": "fdm_printer_1", "name": "Impresora FDM #1"},
    ]
    causes_data = [
        {"code": "support_material", "name": "Soporte desprendido"},
        {"code": "failed_print", "name": "Fallo de impresión"},
        {"code": "cut_margin", "name": "Margen de corte"},
        {"code": "design_error", "name": "Error de diseño"},
        {"code": "machine_abort", "name": "Parada de máquina"},
        {"code": "material_defect", "name": "Defecto de material"},
    ]

    catalogs = {
        "waste_types": {},
        "materials": {},
        "machines": {},
        "causes": {},
        "qr_contexts": {}
    }

    for item in waste_types_data:
        obj = db.query(WasteType).filter_by(code=item["code"]).first()
        if not obj:
            obj = WasteType(code=item["code"], name=item["name"])
            db.add(obj)
            db.flush()
        catalogs["waste_types"][item["code"]] = obj

    for item in materials_data:
        obj = db.query(Material).filter_by(code=item["code"]).first()
        if not obj:
            obj = Material(code=item["code"], name=item["name"])
            db.add(obj)
            db.flush()
        catalogs["materials"][item["code"]] = obj

    for item in machines_data:
        obj = db.query(Machine).filter_by(code=item["code"]).first()
        if not obj:
            obj = Machine(code=item["code"], name=item["name"])
            db.add(obj)
            db.flush()
        catalogs["machines"][item["code"]] = obj

    for item in causes_data:
        obj = db.query(Cause).filter_by(code=item["code"]).first()
        if not obj:
            obj = Cause(code=item["code"], name=item["name"])
            db.add(obj)
            db.flush()
        catalogs["causes"][item["code"]] = obj

    # Seed QR Contexts
    qr_data = [
        {
            "token": "token-laser-01",
            "label": "Estación Cortadora Láser 1",
            "machine_code": "laser_cutter_1",
            "waste_type_code": "laser_cut",
            "material_code": "acrylic",
            "cause_code": "cut_margin",
        },
        {
            "token": "token-sla-01",
            "label": "Estación Impresora SLA 1",
            "machine_code": "sla_printer_1",
            "waste_type_code": "resin",
            "material_code": "photopolymer",
            "cause_code": "support_material",
        },
        {
            "token": "token-general",
            "label": "QR General de Laboratorio",
            "machine_code": None,
            "waste_type_code": None,
            "material_code": None,
            "cause_code": None,
        },
    ]

    for item in qr_data:
        th = hash_token(item["token"])
        qr = db.query(QRContext).filter_by(token_hash=th).first()
        if not qr:
            qr = QRContext(
                token_hash=th,
                label=item["label"],
                machine_id=catalogs["machines"][item["machine_code"]].id if item["machine_code"] else None,
                waste_type_id=catalogs["waste_types"][item["waste_type_code"]].id if item["waste_type_code"] else None,
                material_id=catalogs["materials"][item["material_code"]].id if item["material_code"] else None,
                cause_id=catalogs["causes"][item["cause_code"]].id if item["cause_code"] else None,
            )
            db.add(qr)
            db.flush()
        catalogs["qr_contexts"][item["token"]] = qr

    db.commit()
    return catalogs

