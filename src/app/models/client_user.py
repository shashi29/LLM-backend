# app/models/client_user.py
from datetime import datetime, timedelta
from typing import List, Optional
from sqlmodel import SQLModel, Field
from pydantic import EmailStr, validator
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CONSULTANT = "CONSULTANT"
    END_USER = "END_USER"

class SubscriptionType(str, Enum):
    GOLD = "GOLD"
    BASIC = "BASIC"

class PhoneRequestForm(SQLModel):
    phone_number: str

class EmailRequestForm(SQLModel):
    email: str

class OTPVerificationForm(SQLModel):
    phone_number: str
    otp: str

class EmailOTPVerificationForm(SQLModel):
    email: str
    otp: str

class LoginClientUser(SQLModel):
    email: str
    password: str

class SubscriptionUpdateForm(SQLModel):
    user_id: int
    subscription_type: SubscriptionType
    trial_days: Optional[int] = Field(default=30, ge=1, le=30)  # For BASIC subscription only

# NEW PASSWORD RESET FORMS
class PasswordResetRequestForm(SQLModel):
    email: str

class PasswordResetOTPVerificationForm(SQLModel):
    email: str
    otp: str

class NewPasswordForm(SQLModel):
    email: str
    otp: str
    new_password: str = Field(min_length=6, description="New password (minimum 6 characters)")
    confirm_password: str = Field(min_length=6, description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class ClientUser(SQLModel, table=True):
    __tablename__ = "ClientUsers"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None, index=True)
    username: Optional[str] = Field(default=None)
    password: str
    email: str = Field(unique=True, index=True)
    client_number: Optional[str] = Field(default=None)
    customer_number: Optional[str] = Field(default=None, index=True)  # Primary contact number
    professional_contact_number: Optional[str] = Field(default=None, index=True)  # Secondary contact number
    subscription: Optional[str] = Field(default=SubscriptionType.BASIC)  # GOLD or BASIC
    role: Optional[str] = Field(default=UserRole.END_USER)
    customer_other_details: Optional[str] = Field(default=None)
    
    # Subscription management fields
    subscription_start_date: Optional[datetime] = Field(default=None)
    subscription_end_date: Optional[datetime] = Field(default=None)
    trial_used: Optional[bool] = Field(default=False, index=True)  # Track if user has used trial
    is_subscription_active: Optional[bool] = Field(default=True, index=True)  # Active status
    total_trial_days_used: Optional[int] = Field(default=0)  # Track total trial days used
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "name": "Shashi Raj",
                    "username": "shashi_raj",
                    "email": "shashiraj.newproject@gmail.com",
                    "password": "admin",
                    "client_number": "001",
                    "customer_number": "9952974037",
                    "professional_contact_number": "9876543210",
                    "subscription": "GOLD",
                    "role": "ADMIN",
                    "customer_other_details": "Other details"
                }
            ]
        }

class OTP(SQLModel, table=True):
    __tablename__ = "OTPs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: Optional[str] = Field(default=None, index=True)
    email: Optional[str] = Field(default=None, index=True)
    otp: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=10)
    )

# Configuration model for trial settings
class TrialConfig(SQLModel):
    max_trial_days: int = Field(default=30, ge=1, le=30)
    
    @classmethod
    def get_max_trial_days(cls) -> int:
        """Get maximum trial days allowed (can be made configurable)"""
        return 30
