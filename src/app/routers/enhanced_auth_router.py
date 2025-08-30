# app/routers/enhanced_auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import timedelta, datetime
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

from app.models.enhanced_auth import (
    SendOTPRequest, VerifyOTPRequest, ResetPasswordRequest, 
    ChangePasswordRequest, LoginOTPRequest, StandardResponse, 
    AuthResponse, IdentifierType, OTPPurpose
)
from app.models.client_user import ClientUser
from app.repositories.enhanced_auth_repository import EnhancedAuthRepository
from app.repositories.client_user_repository import ClientUsersRepository, create_access_token
from app.exceptions import UserNotFoundException, EmailAlreadyInUseException, InternalServerErrorException
from sqlalchemy import text

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

router = APIRouter(prefix="/auth", tags=["Enhanced Authentication"])

# Repository instances
enhanced_auth_repo = EnhancedAuthRepository()
users_repository = ClientUsersRepository()

# ===============================
# OTP MANAGEMENT ENDPOINTS
# ===============================

@router.post("/send-otp", response_model=StandardResponse)
async def send_otp(request: SendOTPRequest):
    """
    Send OTP for various purposes (login, reset password, change password, verify email)
    
    - **identifier**: Phone number or email address
    - **identifier_type**: "PHONE" or "EMAIL" 
    - **purpose**: "LOGIN", "RESET_PASSWORD", "CHANGE_PASSWORD", "VERIFY_EMAIL"
    """
    try:
        # If purpose is not LOGIN, find the user first
        user_id = None
        if request.purpose != OTPPurpose.LOGIN:
            user = enhanced_auth_repo._find_user_by_identifier(request.identifier, request.identifier_type)
            if not user:
                return StandardResponse(
                    success=False,
                    message="User not found with this identifier"
                )
            user_id = user.id
        
        # Send OTP
        success, message = enhanced_auth_repo.send_otp(
            identifier=request.identifier,
            identifier_type=request.identifier_type,
            purpose=request.purpose,
            user_id=user_id
        )
        
        return StandardResponse(success=success, message=message)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending OTP: {str(e)}"
        )

@router.post("/verify-otp", response_model=StandardResponse)
async def verify_otp(request: VerifyOTPRequest):
    """
    Verify OTP (for non-login purposes)
    
    This endpoint only verifies the OTP but doesn't perform any action.
    Use specific endpoints like /reset-password or /change-password for actions.
    """
    try:
        success, message, otp_record = enhanced_auth_repo.verify_otp(
            identifier=request.identifier,
            otp_code=request.otp_code,
            purpose=request.purpose
        )
        
        return StandardResponse(
            success=success, 
            message=message,
            data={"verified": success} if success else None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying OTP: {str(e)}"
        )

# ===============================
# LOGIN ENDPOINTS
# ===============================

@router.post("/login-with-otp", response_model=AuthResponse)
async def login_with_otp(request: LoginOTPRequest):
    """
    Login using OTP (alternative to password login)
    
    - **identifier**: Phone number or email address
    - **identifier_type**: "PHONE" or "EMAIL"
    - **otp_code**: 6-digit OTP code
    """
    try:
        # Verify OTP
        success, message, otp_record = enhanced_auth_repo.verify_otp(
            identifier=request.identifier,
            otp_code=request.otp_code,
            purpose=OTPPurpose.LOGIN
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        
        # Find user by identifier
        user = enhanced_auth_repo._find_user_by_identifier(request.identifier, request.identifier_type)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Generate access token
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, 
            expires_delta=expires_delta
        )
        
        # Check trial status
        is_trial_active = True
        if user.subscription == "Trial" and user.trial_end_date:
            is_trial_active = user.trial_end_date > datetime.utcnow()
        
        # Clean up verified OTP
        enhanced_auth_repo._delete_otp_by_id(otp_record.id)
        
        return AuthResponse(
            access_token=access_token,
            user_id=user.id,
            user_name=user.name or "",
            email=user.email,
            role=user.role,
            subscription=user.subscription,
            trial_end_date=user.trial_end_date.isoformat() if user.trial_end_date else None,
            is_trial_active=is_trial_active
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )

# ===============================
# PASSWORD MANAGEMENT ENDPOINTS
# ===============================

@router.post("/reset-password", response_model=StandardResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using OTP (forgot password flow)
    
    Steps:
    1. First call /send-otp with purpose="RESET_PASSWORD"
    2. Then call this endpoint with the OTP
    
    - **identifier**: Phone number or email address
    - **identifier_type**: "PHONE" or "EMAIL"
    - **otp_code**: 6-digit OTP code
    - **new_password**: New password (minimum 6 characters)
    """
    try:
        success, message = enhanced_auth_repo.reset_password(
            identifier=request.identifier,
            identifier_type=request.identifier_type,
            otp_code=request.otp_code,
            new_password=request.new_password
        )
        
        return StandardResponse(success=success, message=message)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting password: {str(e)}"
        )

@router.post("/change-password", response_model=StandardResponse)
async def change_password(request: ChangePasswordRequest):
    """
    Change password for authenticated user with OTP verification
    
    Steps:
    1. First call /send-otp with purpose="CHANGE_PASSWORD"
    2. Then call this endpoint with current password and OTP
    
    - **current_password**: Current password
    - **new_password**: New password (minimum 6 characters)
    - **otp_code**: 6-digit OTP code
    - **identifier**: Phone number or email address
    - **identifier_type**: "PHONE" or "EMAIL"
    """
    try:
        # Find user by identifier first
        user = enhanced_auth_repo._find_user_by_identifier(request.identifier, request.identifier_type)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        success, message = enhanced_auth_repo.change_password(
            user_id=user.id,
            current_password=request.current_password,
            new_password=request.new_password,
            identifier=request.identifier,
            otp_code=request.otp_code
        )
        
        return StandardResponse(success=success, message=message)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )

# ===============================
# EMAIL VERIFICATION ENDPOINTS
# ===============================

@router.post("/send-email-verification", response_model=StandardResponse)
async def send_email_verification(email: str):
    """
    Send email verification OTP
    
    - **email**: Email address to verify
    """
    try:
        # Find user by email
        user = enhanced_auth_repo._find_user_by_identifier(email, IdentifierType.EMAIL)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found with this email"
            )
        
        if user.email_verified:
            return StandardResponse(
                success=False,
                message="Email is already verified"
            )
        
        # Send verification OTP
        success, message = enhanced_auth_repo.send_otp(
            identifier=email,
            identifier_type=IdentifierType.EMAIL,
            purpose=OTPPurpose.VERIFY_EMAIL,
            user_id=user.id
        )
        
        return StandardResponse(success=success, message=message)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending email verification: {str(e)}"
        )

@router.post("/verify-email", response_model=StandardResponse)
async def verify_email(email: str, otp_code: str):
    """
    Verify email using OTP
    
    - **email**: Email address
    - **otp_code**: 6-digit OTP code
    """
    try:
        # Verify OTP
        success, message, otp_record = enhanced_auth_repo.verify_otp(
            identifier=email,
            otp_code=otp_code,
            purpose=OTPPurpose.VERIFY_EMAIL
        )
        
        if not success:
            return StandardResponse(success=False, message=message)
        
        # Mark email as verified
        query = text("""
            UPDATE ClientUsers 
            SET email_verified = TRUE, email_verified_at = CURRENT_TIMESTAMP
            WHERE email = :email;
        """)
        enhanced_auth_repo.execute_delete_query(query, {"email": email})
        
        # Clean up OTP
        enhanced_auth_repo._delete_otp_by_id(otp_record.id)
        
        return StandardResponse(
            success=True,
            message="Email verified successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying email: {str(e)}"
        )

# ===============================
# UTILITY ENDPOINTS
# ===============================

@router.get("/user-status/{identifier}")
async def get_user_status(identifier: str, identifier_type: IdentifierType):
    """
    Get user verification status
    
    - **identifier**: Phone number or email address
    - **identifier_type**: "PHONE" or "EMAIL"
    """
    try:
        user = enhanced_auth_repo._find_user_by_identifier(identifier, identifier_type)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "user_id": user.id,
            "email": user.email,
            "phone_number": user.phone_number,
            "email_verified": getattr(user, 'email_verified', False),
            "email_verified_at": getattr(user, 'email_verified_at', None),
            "last_password_change": getattr(user, 'last_password_change', None),
            "subscription": user.subscription,
            "trial_end_date": user.trial_end_date.isoformat() if user.trial_end_date else None
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user status: {str(e)}"
        )

# ===============================
# LEGACY ENDPOINTS (Updated)
# ===============================

@router.post("/send-otp-legacy", response_model=dict)
async def send_otp_legacy(phone_number: str):
    """
    Legacy phone OTP endpoint (for backward compatibility)
    
    - **phone_number**: Phone number
    """
    try:
        success, message = enhanced_auth_repo.send_otp(
            identifier=phone_number,
            identifier_type=IdentifierType.PHONE,
            purpose=OTPPurpose.LOGIN
        )
        
        return {"success": success, "message": message}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending OTP: {str(e)}"
        )