from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"


class DeviceType(str, enum.Enum):
    DESKTOP = "台式机"
    LAPTOP = "笔记本"
    MONITOR = "显示器"
    MOUSE = "鼠标"
    KEYBOARD = "键盘"
    PRINTER = "打印机"
    PHONE = "手机"
    TABLET = "平板"
    ROUTER = "路由器"
    SWITCH = "交换机"
    SERVER = "服务器"
    OTHER = "其他"


class DeviceStatus(str, enum.Enum):
    IDLE = "空闲"
    IN_USE = "使用中"
    REPAIRING = "维修中"
    SCRAPPED = "已报废"


class AssignmentEvent(str, enum.Enum):
    ASSIGN = "分配"
    TRANSFER = "更换/转移"
    HANDOVER = "交接"
    RETURN = "归还"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.EMPLOYEE.value)
    is_active = Column(Integer, default=1)
    can_register = Column(Integer, default=0)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    employee = relationship("Employee", back_populates="user", uselist=False)
    assignments_made = relationship("Assignment", back_populates="assigner", foreign_keys="Assignment.assigned_by")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=True, default="")
    department = Column(String(50), nullable=True, default="")
    position = Column(String(50), nullable=True, default="")
    status = Column(String(20), default="在职")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="employee", uselist=False)
    assignments = relationship("Assignment", back_populates="employee", foreign_keys="Assignment.employee_id")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_code = Column(String(100), nullable=False, index=True)
    device_type = Column(String(20), nullable=False, default=DeviceType.OTHER.value)
    brand = Column(String(50), nullable=True, default="")
    model = Column(String(100), nullable=True, default="")
    specs = Column(Text, nullable=True, default="")
    status = Column(String(20), nullable=False, default=DeviceStatus.IDLE.value)
    purchase_date = Column(String(20), nullable=True, default="")
    warranty_expiry = Column(String(20), nullable=True, default="")
    notes = Column(Text, nullable=True, default="")
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    assignments = relationship("Assignment", back_populates="device")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_type = Column(String(20), nullable=False, default=AssignmentEvent.ASSIGN.value)
    notes = Column(Text, nullable=True, default="")
    assigned_at = Column(DateTime, default=datetime.now)
    returned_at = Column(DateTime, nullable=True)

    device = relationship("Device", back_populates="assignments")
    employee = relationship("Employee", back_populates="assignments", foreign_keys=[employee_id])
    assigner = relationship("User", back_populates="assignments_made", foreign_keys=[assigned_by])
