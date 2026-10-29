from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models import Assignment, Device, Employee, User, AssignmentEvent, DeviceStatus
from schemas import AssignmentCreate, AssignmentOut
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/assignments", tags=["设备分配"])


@router.get("", response_model=List[AssignmentOut])
def list_assignments(
    employee_id: int = 0,
    device_id: int = 0,
    event_type: str = "",
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Assignment)
    if employee_id:
        query = query.filter(Assignment.employee_id == employee_id)
    if device_id:
        query = query.filter(Assignment.device_id == device_id)
    if event_type:
        query = query.filter(Assignment.event_type == event_type)
    if active_only:
        query = query.filter(Assignment.returned_at.is_(None))

    records = query.order_by(Assignment.assigned_at.desc()).all()

    result = []
    for a in records:
        device = db.query(Device).filter(Device.id == a.device_id).first()
        employee = db.query(Employee).filter(Employee.id == a.employee_id).first()
        assigner = db.query(User).filter(User.id == a.assigned_by).first()
        result.append(
            AssignmentOut(
                id=a.id,
                device_id=a.device_id,
                employee_id=a.employee_id,
                assigned_by=a.assigned_by,
                event_type=a.event_type,
                notes=a.notes,
                assigned_at=a.assigned_at,
                returned_at=a.returned_at,
                device_code=device.device_code if device else None,
                device_type=device.device_type if device else None,
                employee_name=employee.name if employee else None,
                assigner_name=assigner.username if assigner else None,
            )
        )
    return result


@router.post("/assign", response_model=AssignmentOut)
def assign_device(
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    device = db.query(Device).filter(Device.id == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    if device.status == DeviceStatus.SCRAPPED.value:
        raise HTTPException(status_code=400, detail="该设备已报废，无法分配")

    # Check if device is already assigned
    active = db.query(Assignment).filter(
        Assignment.device_id == data.device_id, Assignment.returned_at.is_(None)
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="该设备已被分配，请先归还后再分配")

    employee = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")

    a = Assignment(
        device_id=data.device_id,
        employee_id=data.employee_id,
        assigned_by=current_user.id,
        event_type=AssignmentEvent.ASSIGN.value,
        notes=data.notes,
    )
    device.status = DeviceStatus.IN_USE.value
    db.add(a)
    db.commit()
    db.refresh(a)

    return AssignmentOut(
        id=a.id, device_id=a.device_id, employee_id=a.employee_id,
        assigned_by=a.assigned_by, event_type=a.event_type, notes=a.notes,
        assigned_at=a.assigned_at, returned_at=a.returned_at,
        device_code=device.device_code, device_type=device.device_type,
        employee_name=employee.name, assigner_name=current_user.username,
    )


@router.post("/transfer", response_model=AssignmentOut)
def transfer_device(
    device_id: int,
    from_employee_id: int,
    to_employee_id: int,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # Find active assignment from old employee
    active = db.query(Assignment).filter(
        Assignment.device_id == device_id,
        Assignment.employee_id == from_employee_id,
        Assignment.returned_at.is_(None),
    ).first()
    if not active:
        raise HTTPException(status_code=400, detail="该设备当前未被此员工使用")

    to_emp = db.query(Employee).filter(Employee.id == to_employee_id).first()
    if not to_emp:
        raise HTTPException(status_code=404, detail="目标员工不存在")

    # Close old assignment
    active.returned_at = datetime.now()

    # Create new assignment
    new_a = Assignment(
        device_id=device_id,
        employee_id=to_employee_id,
        assigned_by=current_user.id,
        event_type=AssignmentEvent.TRANSFER.value,
        notes=f"从员工ID {from_employee_id} 转移至员工ID {to_employee_id}" + (f"；{notes}" if notes else ""),
    )
    db.add(new_a)
    db.commit()
    db.refresh(new_a)

    return AssignmentOut(
        id=new_a.id, device_id=new_a.device_id, employee_id=new_a.employee_id,
        assigned_by=new_a.assigned_by, event_type=new_a.event_type, notes=new_a.notes,
        assigned_at=new_a.assigned_at, returned_at=new_a.returned_at,
        device_code=device.device_code, device_type=device.device_type,
        employee_name=to_emp.name, assigner_name=current_user.username,
    )


@router.post("/handover", response_model=AssignmentOut)
def handover_device(
    device_id: int,
    from_employee_id: int,
    to_employee_id: int,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """设备交接登记：同时完成归还和分配，记录交接信息"""
    return transfer_device(
        device_id=device_id,
        from_employee_id=from_employee_id,
        to_employee_id=to_employee_id,
        notes=notes,
        db=db,
        current_user=current_user,
    )


@router.post("/return", response_model=AssignmentOut)
def return_device(
    device_id: int,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    active = db.query(Assignment).filter(
        Assignment.device_id == device_id, Assignment.returned_at.is_(None)
    ).first()
    if not active:
        raise HTTPException(status_code=400, detail="该设备当前未被分配")

    active.returned_at = datetime.now()
    active.notes = active.notes + ("; " + notes) if active.notes else notes

    device.status = DeviceStatus.IDLE.value
    db.commit()
    db.refresh(active)

    employee = db.query(Employee).filter(Employee.id == active.employee_id).first()
    return AssignmentOut(
        id=active.id, device_id=active.device_id, employee_id=active.employee_id,
        assigned_by=active.assigned_by, event_type="归还", notes=active.notes,
        assigned_at=active.assigned_at, returned_at=active.returned_at,
        device_code=device.device_code, device_type=device.device_type,
        employee_name=employee.name if employee else None,
        assigner_name=current_user.username,
    )


@router.post("/replace", response_model=AssignmentOut)
def replace_device(
    old_device_id: int,
    new_device_id: int,
    employee_id: int,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """设备更换：归还旧设备并分配新设备"""
    old_device = db.query(Device).filter(Device.id == old_device_id).first()
    new_device = db.query(Device).filter(Device.id == new_device_id).first()
    if not old_device or not new_device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # Return old device
    active_old = db.query(Assignment).filter(
        Assignment.device_id == old_device_id,
        Assignment.employee_id == employee_id,
        Assignment.returned_at.is_(None),
    ).first()
    if active_old:
        active_old.returned_at = datetime.now()
        active_old.event_type = AssignmentEvent.RETURN.value
        old_device.status = DeviceStatus.IDLE.value

    # Assign new device
    active_new = db.query(Assignment).filter(
        Assignment.device_id == new_device_id, Assignment.returned_at.is_(None)
    ).first()
    if active_new:
        raise HTTPException(status_code=400, detail="新设备已被分配")

    new_a = Assignment(
        device_id=new_device_id,
        employee_id=employee_id,
        assigned_by=current_user.id,
        event_type="更换",
        notes=f"更换设备（旧设备: {old_device.device_code}）" + (f"；{notes}" if notes else ""),
    )
    new_device.status = DeviceStatus.IN_USE.value
    db.add(new_a)
    db.commit()
    db.refresh(new_a)

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    return AssignmentOut(
        id=new_a.id, device_id=new_a.device_id, employee_id=new_a.employee_id,
        assigned_by=new_a.assigned_by, event_type=new_a.event_type, notes=new_a.notes,
        assigned_at=new_a.assigned_at, returned_at=new_a.returned_at,
        device_code=new_device.device_code, device_type=new_device.device_type,
        employee_name=employee.name if employee else None,
        assigner_name=current_user.username,
    )
