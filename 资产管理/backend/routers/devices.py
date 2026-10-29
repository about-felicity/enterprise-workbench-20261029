from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Device, Assignment, Employee, User, AssignmentEvent, DeviceStatus
from schemas import DeviceCreate, DeviceUpdate, DeviceOut
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/devices", tags=["设备管理"])


def _get_current_user_name(device_id: int, db: Session) -> str | None:
    active = (
        db.query(Assignment)
        .filter(Assignment.device_id == device_id, Assignment.returned_at.is_(None))
        .first()
    )
    if active:
        emp = db.query(Employee).filter(Employee.id == active.employee_id).first()
        return emp.name if emp else None
    return None


@router.get("", response_model=List[DeviceOut])
def list_devices(
    search: str = "",
    device_type: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Device)
    if search:
        query = query.filter(
            Device.device_code.contains(search)
            | Device.brand.contains(search)
            | Device.model.contains(search)
        )
    if device_type:
        query = query.filter(Device.device_type == device_type)
    if status:
        query = query.filter(Device.status == status)

    devices = query.order_by(Device.created_at.desc()).all()
    return [
        DeviceOut(
            id=d.id, device_code=d.device_code, device_type=d.device_type,
            brand=d.brand, model=d.model, specs=d.specs, status=d.status,
            purchase_date=d.purchase_date, warranty_expiry=d.warranty_expiry,
            notes=d.notes, created_at=d.created_at, updated_at=d.updated_at,
            current_user=_get_current_user_name(d.id, db),
        )
        for d in devices
    ]


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="设备不存在")
    return DeviceOut(
        id=d.id, device_code=d.device_code, device_type=d.device_type,
        brand=d.brand, model=d.model, specs=d.specs, status=d.status,
        purchase_date=d.purchase_date, warranty_expiry=d.warranty_expiry,
        notes=d.notes, created_at=d.created_at, updated_at=d.updated_at,
        current_user=_get_current_user_name(d.id, db),
    )


@router.post("", response_model=DeviceOut)
def create_device(
    data: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = Device(**data.model_dump())
    # 自动分配给当前用户（仅当状态为"使用中"时）
    should_assign = d.status == DeviceStatus.IN_USE.value and current_user.employee_id
    if should_assign:
        d.status = DeviceStatus.IN_USE.value
    db.add(d)
    db.flush()
    # 创建分配记录
    if should_assign:
        a = Assignment(
            device_id=d.id,
            employee_id=current_user.employee_id,
            assigned_by=current_user.id,
            event_type=AssignmentEvent.ASSIGN.value,
            notes="",
        )
        db.add(a)
    db.commit()
    db.refresh(d)
    return DeviceOut(
        id=d.id, device_code=d.device_code, device_type=d.device_type,
        brand=d.brand, model=d.model, specs=d.specs, quantity=d.quantity, status=d.status,
        purchase_date=d.purchase_date, warranty_expiry=d.warranty_expiry,
        notes=d.notes, created_at=d.created_at, updated_at=d.updated_at,
        current_user=_get_current_user_name(d.id, db),
    )


@router.put("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    data: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="设备不存在")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    for k, v in update_data.items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return DeviceOut(
        id=d.id, device_code=d.device_code, device_type=d.device_type,
        brand=d.brand, model=d.model, specs=d.specs, status=d.status,
        purchase_date=d.purchase_date, warranty_expiry=d.warranty_expiry,
        notes=d.notes, created_at=d.created_at, updated_at=d.updated_at,
        current_user=_get_current_user_name(d.id, db),
    )


@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="设备不存在")
    # Delete all assignment history
    db.query(Assignment).filter(Assignment.device_id == device_id).delete()
    db.delete(d)
    db.commit()
    return {"message": "删除成功"}
