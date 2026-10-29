from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from database import get_db
from models import User, Employee
from schemas import UserLogin, UserCreate, UserOut, Token, UserUpdate
from auth import hash_password, verify_password, create_access_token, get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["认证"])


class PhoneBind(BaseModel):
    phone: str


@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    token = create_access_token({"sub": str(user.id), "role": user.role})

    # 管理员检查是否需要绑定手机号
    need_bind_phone = False
    if user.role == "admin" and user.employee and not user.employee.phone:
        need_bind_phone = True

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserOut(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            can_register=user.can_register,
            employee_id=user.employee_id,
            created_at=user.created_at,
        ),
        "need_bind_phone": need_bind_phone,
    }


@router.post("/bind-phone")
def bind_phone(data: PhoneBind, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """绑定手机号"""
    phone = data.phone.strip()
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="未关联员工信息")
    if not phone or len(phone) < 7:
        raise HTTPException(status_code=400, detail="请输入有效的手机号")
    emp = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
    emp.phone = phone
    db.commit()
    return {"message": "手机号绑定成功", "phone": phone}


@router.post("/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    # Check if any admin exists; if not, first user becomes admin
    admin_count = db.query(User).filter(User.role == "admin").count()

    if admin_count > 0:
        # Check if there's any user with can_register=1
        open_user = db.query(User).filter(User.can_register == 1, User.is_active == 1).first()
        if not open_user:
            raise HTTPException(status_code=403, detail="当前未开放注册，请联系管理员")

    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # Create employee record
    employee = Employee(name=data.name, phone=data.phone, department=data.department, position=data.position)
    db.add(employee)
    db.flush()

    # Create user
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role="admin" if admin_count == 0 else "employee",
        is_active=1,
        can_register=0,
        employee_id=employee.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        can_register=user.can_register,
        employee_id=user.employee_id,
        created_at=user.created_at,
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
        can_register=current_user.can_register,
        employee_id=current_user.employee_id,
        created_at=current_user.created_at,
    )


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    users = db.query(User).all()
    return [
        UserOut(
            id=u.id,
            username=u.username,
            role=u.role,
            is_active=u.is_active,
            can_register=u.can_register,
            employee_id=u.employee_id,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.can_register is not None:
        user.can_register = data.can_register
    if data.password:
        user.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        can_register=user.can_register,
        employee_id=user.employee_id,
        created_at=user.created_at,
    )


@router.post("/toggle-register/{user_id}")
def toggle_register(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.can_register = 1 if user.can_register == 0 else 0
    db.commit()
    return {"can_register": user.can_register}
