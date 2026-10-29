from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Employee, Assignment, Device, User
from schemas import EmployeeCreate, EmployeeUpdate, EmployeeOut, DeviceOut
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/employees", tags=["员工管理"])


@router.get("", response_model=List[EmployeeOut])
def list_employees(
    search: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(Employee)
    if search:
        query = query.filter(
            Employee.name.contains(search) | Employee.phone.contains(search) | Employee.department.contains(search)
        )
    if status:
        query = query.filter(Employee.status == status)
    employees = query.order_by(Employee.created_at.desc()).all()

    result = []
    for emp in employees:
        # Get current devices for this employee
        current_assignments = (
            db.query(Assignment)
            .filter(Assignment.employee_id == emp.id, Assignment.returned_at.is_(None))
            .all()
        )
        current_devices = []
        for a in current_assignments:
            device = db.query(Device).filter(Device.id == a.device_id).first()
            if device:
                current_devices.append(
                    DeviceOut(
                        id=device.id,
                        device_code=device.device_code,
                        device_type=device.device_type,
                        brand=device.brand,
                        model=device.model,
                        specs=device.specs,
                        status=device.status,
                        purchase_date=device.purchase_date,
                        warranty_expiry=device.warranty_expiry,
                        notes=device.notes,
                        created_at=device.created_at,
                        updated_at=device.updated_at,
                    )
                )
        result.append(
            EmployeeOut(
                id=emp.id,
                name=emp.name,
                phone=emp.phone,
                department=emp.department,
                position=emp.position,
                status=emp.status,
                created_at=emp.created_at,
                updated_at=emp.updated_at,
                current_devices=current_devices,
            )
        )
    return result


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="员工不存在")

    current_assignments = (
        db.query(Assignment)
        .filter(Assignment.employee_id == emp.id, Assignment.returned_at.is_(None))
        .all()
    )
    current_devices = []
    for a in current_assignments:
        device = db.query(Device).filter(Device.id == a.device_id).first()
        if device:
            current_devices.append(
                DeviceOut(
                    id=device.id,
                    device_code=device.device_code,
                    device_type=device.device_type,
                    brand=device.brand,
                    model=device.model,
                    specs=device.specs,
                    status=device.status,
                    purchase_date=device.purchase_date,
                    warranty_expiry=device.warranty_expiry,
                    notes=device.notes,
                    created_at=device.created_at,
                    updated_at=device.updated_at,
                )
            )
    return EmployeeOut(
        id=emp.id,
        name=emp.name,
        phone=emp.phone,
        department=emp.department,
        position=emp.position,
        status=emp.status,
        created_at=emp.created_at,
        updated_at=emp.updated_at,
        current_devices=current_devices,
    )


@router.post("", response_model=EmployeeOut)
def create_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    emp = Employee(**data.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return EmployeeOut(
        id=emp.id, name=emp.name, phone=emp.phone, department=emp.department,
        position=emp.position, status=emp.status, created_at=emp.created_at,
        updated_at=emp.updated_at, current_devices=[],
    )


@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="员工不存在")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    for k, v in update_data.items():
        setattr(emp, k, v)
    db.commit()
    db.refresh(emp)
    return EmployeeOut(
        id=emp.id, name=emp.name, phone=emp.phone, department=emp.department,
        position=emp.position, status=emp.status, created_at=emp.created_at,
        updated_at=emp.updated_at, current_devices=[],
    )


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # 禁止删除自己
    if current_user.employee_id == employee_id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="员工不存在")
    # Check if employee has active assignments
    active = db.query(Assignment).filter(
        Assignment.employee_id == employee_id, Assignment.returned_at.is_(None)
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="该员工还有未归还的设备，请先归还后再删除")
    # 禁止删除最后一个管理员
    user = db.query(User).filter(User.employee_id == employee_id).first()
    if user and user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin", User.is_active == 1).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="不能删除最后一个管理员账号")
    # Also delete associated user
    if user:
        db.delete(user)
    db.delete(emp)
    db.commit()
    return {"message": "删除成功"}
