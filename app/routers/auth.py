import base64
import io

import pyotp
import qrcode
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import AuthEvent, User

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=100)


class TwoFactorVerifyRequest(BaseModel):
    code: str


class TwoFactorDisableRequest(BaseModel):
    password: str


def _log_event(db: Session, username: str, event_type: str) -> None:
    db.add(AuthEvent(username=username, event_type=event_type))
    db.commit()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    is_first_user = db.query(User).count() == 0
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_admin=is_first_user,
        role="super_admin" if is_first_user else "customer",
    )
    db.add(user)
    db.commit()
    _log_event(db, payload.username, "register")
    return {"message": "Registered successfully"}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), otp_code: str | None = Form(None), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user.totp_enabled:
        if not otp_code or not pyotp.TOTP(user.totp_secret).verify(otp_code, valid_window=1):
            raise HTTPException(status_code=401, detail="Missing or invalid 2FA code")

    _log_event(db, user.username, "login")
    return {"access_token": create_access_token(user.username), "token_type": "bearer"}


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _log_event(db, user.username, "logout")
    return {"message": "Logged out"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "role": user.role,
        "totp_enabled": user.totp_enabled,
    }


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/2fa/setup")
def setup_2fa(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.totp_enabled = False
    db.commit()

    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.username, issuer_name="Solar Monitor")

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    return {"secret": secret, "otpauth_uri": uri, "qr_code_base64": qr_base64}


@router.post("/2fa/verify")
def verify_2fa(payload: TwoFactorVerifyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup has not been started")
    if not pyotp.TOTP(user.totp_secret).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code")

    user.totp_enabled = True
    db.commit()
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
def disable_2fa(payload: TwoFactorDisableRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    user.totp_enabled = False
    user.totp_secret = None
    db.commit()
    return {"message": "2FA disabled"}
