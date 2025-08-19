# app/models/enhanced_auth.py
from datetime import datetime, timedelta
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, validator
from enum import Enum

class IdentifierType(str, Enum):
    PHONE = "PHONE"
    EMAIL = "EMAIL"

class OTPPurpose(str, Enum):
    LOGIN = "LOGIN"
    RESET_PASSWORD = "RESET_PASSWORD"
    CHANGE_PASSWORD = "CHANGE_PASSWORD"
    VERIFY_EMAIL = "VERIFY_EMAIL"

class EnhancedOTP(BaseModel):
    id: Optional[int] = None
    identifier: str  # phone or email
    identifier_type: IdentifierType
    otp_code: str
    purpose: OTPPurpose
    user_id: Optional[int] = None
    attempts: int = 0
    max_attempts: int = 3
    is_verified: bool = False
    expires_at: datetime
    created_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# Request/Response Models
class SendOTPRequest(BaseModel):
    identifier: str  # phone or email
    identifier_type: IdentifierType
    purpose: OTPPurpose

    @validator('identifier')
    def validate_identifier(cls, v, values):
        identifier_type = values.get('identifier_type')
        if identifier_type == IdentifierType.EMAIL:
            # Basic email validation
            if '@' not in v:
                raise ValueError('Invalid email format')
        elif identifier_type == IdentifierType.PHONE:
            # Basic phone validation
            clean_phone = v.replace(" ", "").replace("-", "").replace("+", "")
            if not clean_phone.isdigit() or len(clean_phone) < 10:
                raise ValueError('Invalid phone number format')
        return v

class VerifyOTPRequest(BaseModel):
    identifier: str
    identifier_type: IdentifierType
    otp_code: str
    purpose: OTPPurpose

class ResetPasswordRequest(BaseModel):
    identifier: str
    identifier_type: IdentifierType
    otp_code: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    otp_code: str
    identifier: str
    identifier_type: IdentifierType

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class LoginOTPRequest(BaseModel):
    identifier: str
    identifier_type: IdentifierType
    otp_code: str

class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    user_name: str
    email: str
    role: Optional[str]
    subscription: Optional[str]
    trial_end_date: Optional[str]
    is_trial_active: bool

# Enhanced ClientUser model (additions to existing)
class ClientUserUpdate(BaseModel):
    email_verified: Optional[bool] = None
    email_verified_at: Optional[datetime] = None
    last_password_change: Optional[datetime] = None