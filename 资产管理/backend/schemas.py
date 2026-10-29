from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============ Auth ============
class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4)
    name: str = Field(..., min_length=1, max_length=50)
    phone: str = ""
    department: str = ""
    position: str = ""


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: int
    can_register: int
    employee_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[int] = None
    can_register: Optional[int] = None
    password: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut
    need_bind_phone: bool = False


# ============ Employee ============
class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    phone: str = ""
    department: str = ""
    position: str = ""


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    status: Optional[str] = None


class EmployeeOut(BaseModel):
    id: int
    name: str
    phone: str
    department: str
    position: str
    status: str
    created_at: datetime
    updated_at: datetime
    current_devices: List["DeviceOut"] = []

    class Config:
        from_attributes = True


# ============ Device ============
class DeviceCreate(BaseModel):
    device_code: str = Field(..., min_length=1, max_length=100)
    device_type: str = "其他"
    brand: str = ""
    model: str = ""
    specs: str = ""
    quantity: int = 1
    status: str = "使用中"
    purchase_date: str = ""
    warranty_expiry: str = ""
    notes: str = ""


class DeviceUpdate(BaseModel):
    device_code: Optional[str] = None
    device_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    specs: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None
    purchase_date: Optional[str] = None
    warranty_expiry: Optional[str] = None
    notes: Optional[str] = None


class DeviceOut(BaseModel):
    id: int
    device_code: str
    device_type: str
    brand: str
    model: str
    specs: str
    quantity: int = 1
    status: str
    purchase_date: str
    warranty_expiry: str
    notes: str
    created_at: datetime
    updated_at: datetime
    current_user: Optional[str] = None

    class Config:
        from_attributes = True


# ============ Assignment ============
class AssignmentCreate(BaseModel):
    device_id: int
    employee_id: int
    event_type: str = "分配"
    notes: str = ""


class AssignmentOut(BaseModel):
    id: int
    device_id: int
    employee_id: int
    assigned_by: int
    event_type: str
    notes: str
    assigned_at: datetime
    returned_at: Optional[datetime] = None
    device_code: Optional[str] = None
    device_type: Optional[str] = None
    employee_name: Optional[str] = None
    assigner_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============ Dashboard ============
class DashboardStats(BaseModel):
    total_devices: int
    idle_devices: int
    in_use_devices: int
    repairing_devices: int
    scrapped_devices: int
    total_employees: int
    active_employees: int
    recent_assignments: List[AssignmentOut]
    device_type_distribution: dict
