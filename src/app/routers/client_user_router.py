import os
from pathlib import Path
import random
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status, Header, Security, Query
from fastapi.security import APIKeyHeader
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from app.models.client_user import (
    ClientUser, LoginClientUser, PhoneRequestForm, OTPVerificationForm, 
    EmailRequestForm, EmailOTPVerificationForm, SubscriptionUpdateForm, 
    SubscriptionType, TrialConfig,
    # NEW IMPORTS FOR PASSWORD RESET
    PasswordResetRequestForm, PasswordResetOTPVerificationForm, NewPasswordForm,
)
from app.repositories.client_user_repository import ClientUsersRepository, send_sms
from app.exceptions import UserNotFoundException, EmailAlreadyInUseException, InternalServerErrorException
from app.authentication import verify_token


router = APIRouter(prefix="/client-users", tags=["Client Users"])

# Creating an instance of the UsersRepository
users_repository = ClientUsersRepository()

@router.post("/", response_model=ClientUser)
async def create_user(
    user: ClientUser, 
    trial_days: Optional[int] = Query(default=30, ge=1, le=30, description="Trial days for BASIC subscription (1-30 days)"),
    token: str = Depends(verify_token)
):
    
    """
    Create a new user with subscription management.
    
    - **GOLD**: Permanent access to all features
    - **BASIC**: Trial access for specified days (max 30 days)
    
    Trial can only be used once per contact details (email, phone numbers).
    """
    try:
        created_user = users_repository.create_user(user, trial_days)
        return created_user
    except EmailAlreadyInUseException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use")
    except HTTPException as e:
        # Re-raise HTTPExceptions from repository (like phone number uniqueness validation)
        raise e
    except InternalServerErrorException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[ClientUser])
async def get_users(token: str = Depends(verify_token)):
    users = users_repository.get_users()
    return users

@router.get("/{user_id}", response_model=ClientUser)
async def get_user(user_id: int, token: str = Depends(verify_token)):
    try:
        user = users_repository.get_user(user_id)
        if not user:
            raise UserNotFoundException
        return user
    except UserNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClientUser not found")

@router.put("/{user_id}", response_model=ClientUser)
async def update_user(user_id: int, user: ClientUser, token: str = Depends(verify_token)):
    """
    Update user details. 
    Note: Subscription changes should be done through dedicated subscription endpoints.
    """
    try:
        updated_user = users_repository.update_user(user_id, user)
        if not updated_user:
            raise UserNotFoundException
        return updated_user
    except EmailAlreadyInUseException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use")
    except UserNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClientUser not found")
    except HTTPException as e:
        # Re-raise HTTPExceptions from repository (like phone number uniqueness validation)
        raise e
    except InternalServerErrorException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{user_id}", response_model=dict)
async def delete_user(user_id: int, token: str = Depends(verify_token)):
    try:
        deleted_user = users_repository.delete_user(user_id)
        if not deleted_user:
            raise UserNotFoundException
        response_data = {"status_code": 200, "detail": "ClientUser deleted successfully"}
        return response_data
    except UserNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClientUser not found")
    except InternalServerErrorException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/login", response_model=dict)
def login(user_data: LoginClientUser, token: str = Depends(verify_token)):
    """
    Login user with subscription status check.
    Returns user details along with current subscription status.
    """
    try:
        login_result = users_repository.login_user(user_data)
        if not login_result:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        user = login_result["user"]
        subscription_status = login_result["subscription_status"]

        response_data = {
            "user_id": user.id,
            "user_name": user.name,
            "email": user.email,
            "role": user.role,
            "subscription": user.subscription,
            "customer_other_details": user.customer_other_details,
            "customer_number": user.customer_number,
            "professional_contact_number": user.professional_contact_number,
            "subscription_status": subscription_status,
            # Add other user details as needed
        }

        return JSONResponse(content=response_data)
    except HTTPException as e:
        raise e
    except InternalServerErrorException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
@router.post("/forgot-password", response_model=dict)
async def forgot_password(form_data: PasswordResetRequestForm, token: str = Depends(verify_token)):
    """
    Initiate password reset process by sending OTP to user's email.
    User must exist in the system to receive OTP.
    """
    try:
        otp = users_repository.send_password_reset_otp(form_data.email)
        return {
            "message": f"Password reset OTP sent successfully to {form_data.email}",
            "email": form_data.email,
            "otp": otp  # Remove this in production for security
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        # Handle MSG91 email errors specifically
        if "MSG91" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Email service error: {str(e)}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send password reset email: {str(e)}"
            )

@router.post("/verify-reset-otp", response_model=dict)
async def verify_password_reset_otp(form_data: PasswordResetOTPVerificationForm, token: str = Depends(verify_token)):
    """
    Verify OTP for password reset.
    Returns success message if OTP is valid, allowing user to proceed with password reset.
    """
    try:
        is_valid = users_repository.verify_password_reset_otp(form_data.email, form_data.otp)
        
        if is_valid:
            # Check if user exists
            user = users_repository.get_user_by_email(form_data.email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return {
                "message": "OTP verified successfully. You can now reset your password.",
                "email": form_data.email,
                "otp_verified": True,
                "user_id": user.id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify OTP: {str(e)}"
        )

@router.post("/reset-password", response_model=dict)
async def reset_password(form_data: NewPasswordForm, token: str = Depends(verify_token)):
    """
    Complete password reset by setting new password.
    Requires valid OTP verification and matching passwords.
    """
    try:
        # The NewPasswordForm already validates that passwords match via the validator
        result = users_repository.reset_password_complete(
            form_data.email, 
            form_data.otp, 
            form_data.new_password
        )
        
        return {
            "message": "Password reset completed successfully. You can now login with your new password.",
            "email": form_data.email,
            "user_id": result["user_id"],
            "user_name": result["user_name"],
            "reset_completed": True
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )

@router.get("/password-reset-info", response_model=dict)
async def get_password_reset_info(token: str = Depends(verify_token)):
    """
    Get information about the password reset process.
    """
    return {
        "process": [
            "1. Enter your registered email address",
            "2. Check your email for OTP (valid for 10 minutes)",
            "3. Enter the OTP to verify your identity", 
            "4. Set your new password (minimum 6 characters)",
            "5. Confirm your new password",
            "6. Login with your new password"
        ],
        "requirements": {
            "password_min_length": 6,
            "otp_validity": "10 minutes",
            "email_required": "Must be registered in the system"
        },
        "notes": [
            "OTP expires after 10 minutes",
            "Password must be at least 6 characters long",
            "New password and confirm password must match",
            "Only registered users can reset password"
        ]
    }

@router.get("/{user_id}/subscription-status", response_model=dict)
async def get_subscription_status(user_id: int, token: str = Depends(verify_token)):
    """
    Get current subscription status for a user.
    """
    try:
        subscription_status = users_repository.check_subscription_status(user_id)
        return JSONResponse(content=subscription_status)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{user_id}/upgrade-to-gold", response_model=ClientUser)
async def upgrade_user_to_gold(user_id: int, token: str = Depends(verify_token)):
    """
    Upgrade user from Basic to Gold subscription.
    """
    try:
        upgraded_user = users_repository.upgrade_to_gold(user_id)
        return upgraded_user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/expired-trials/list", response_model=List[ClientUser])
async def get_expired_trials(token: str = Depends(verify_token)):
    """
    Get list of users with expired trial subscriptions.
    Admin endpoint for managing expired trials.
    """
    try:
        expired_users = users_repository.get_expired_trials()
        return expired_users
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/expired-trials/deactivate", response_model=dict)
async def deactivate_expired_trials(token: str = Depends(verify_token)):
    """
    Deactivate all expired trial subscriptions.
    Admin endpoint for cleanup.
    """
    try:
        deactivated_count = users_repository.deactivate_expired_trials()
        return {"message": f"Deactivated {deactivated_count} expired trial subscriptions"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/send-otp", response_model=dict)
async def send_otp_to_user(form_data: PhoneRequestForm, token: str = Depends(verify_token)):
    """
    Send OTP to user's primary contact number (customer_number).
    The phone_number in the request must match the user's primary contact number.
    """
    user = users_repository.get_user_by_phone(form_data.phone_number)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found with this primary contact number"
        )

    # Check subscription status before allowing OTP
    subscription_status = users_repository.check_subscription_status(user.id)
    if not subscription_status["has_access"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {subscription_status['message']}"
        )

    users_repository.delete_otp(form_data.phone_number)
    
    try:
        otp = users_repository.store_otp(form_data.phone_number)
        return {"message": f"OTP sent successfully to primary contact number: {form_data.phone_number}", "otp": otp}
    except Exception as e:
        # Handle MSG91 SMS errors specifically
        if "MSG91" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"SMS service error: {str(e)}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send SMS: {str(e)}"
            )
            
@router.post("/verify-otp", response_model=dict)
async def verify_otp(form_data: OTPVerificationForm, token: str = Depends(verify_token)):
    """
    Verify OTP sent to user's primary contact number.
    """
    if users_repository.validate_otp(form_data.phone_number, form_data.otp):
        user = users_repository.get_user_by_phone(form_data.phone_number)
        
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # Check subscription status
        subscription_status = users_repository.check_subscription_status(user.id)

        users_repository.delete_otp(form_data.phone_number)
        
        response_data = {
            "user_id": user.id,
            "user_name": user.name,
            "email": user.email,
            "role": user.role,
            "subscription": user.subscription,
            "customer_other_details": user.customer_other_details,
            "customer_number": user.customer_number,
            "professional_contact_number": user.professional_contact_number,
            "subscription_status": subscription_status,
            # Add other user details as needed
        }
        
        return JSONResponse(content=response_data)
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid OTP"
    )
    
    
@router.post("/send-email-otp", response_model=dict)
async def send_otp_to_email(form_data: EmailRequestForm, token: str = Depends(verify_token)):
    user = users_repository.get_user_by_email(form_data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")

    # Check subscription status before allowing OTP
    subscription_status = users_repository.check_subscription_status(user.id)
    if not subscription_status["has_access"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {subscription_status['message']}"
        )

    users_repository.delete_otp(form_data.email, is_email=True)
    
    try:
        otp = users_repository.store_otp(form_data.email, is_email=True)
        return {"message": f"OTP sent successfully to email: {form_data.email}", "otp": otp}
    except Exception as e:
        # Handle MSG91 errors specifically
        if "MSG91" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Email service error: {str(e)}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {str(e)}"
            )

@router.post("/verify-email-otp", response_model=dict)
async def verify_email_otp(form_data: EmailOTPVerificationForm, token: str = Depends(verify_token)):
    if users_repository.validate_otp(form_data.email, form_data.otp, is_email=True):  # Use is_email=True
        users_repository.delete_otp(form_data.email, is_email=True)  # Use is_email=True
        user = users_repository.get_user_by_email(form_data.email)

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # Check subscription status
        subscription_status = users_repository.check_subscription_status(user.id)

        response_data = {
            "user_id": user.id,
            "user_name": user.name,
            "email": user.email,
            "role": user.role,
            "subscription": user.subscription,
            "customer_other_details": user.customer_other_details,
            "customer_number": user.customer_number,
            "professional_contact_number": user.professional_contact_number,
            "subscription_status": subscription_status,
        }

        return JSONResponse(content=response_data)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid OTP"
    )

@router.get("/lookup-phone/{phone_number}", response_model=dict)
async def lookup_user_by_phone(phone_number: str, token: str = Depends(verify_token)):
    """
    Lookup user by any phone number (primary or secondary).
    This is for general lookup purposes, not for OTP functionality.
    """
    user = users_repository.get_user_by_any_phone(phone_number)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found with this phone number"
        )
    
    # Determine if the phone number is primary or secondary
    is_primary = user.customer_number == phone_number
    
    # Get subscription status
    subscription_status = users_repository.check_subscription_status(user.id)
    
    response_data = {
        "user_id": user.id,
        "user_name": user.name,
        "email": user.email,
        "role": user.role,
        "subscription": user.subscription,
        "customer_number": user.customer_number,
        "professional_contact_number": user.professional_contact_number,
        "phone_number_type": "primary" if is_primary else "secondary",
        "customer_other_details": user.customer_other_details,
        "subscription_status": subscription_status,
    }
    
    return JSONResponse(content=response_data)

@router.get("/subscription-config", response_model=dict)
async def get_subscription_config(token: str = Depends(verify_token)):
    """
    Get subscription configuration details.
    """
    return {
        "subscription_types": {
            "GOLD": "Permanent access to all features",
            "BASIC": "Trial access with limited duration"
        },
        "max_trial_days": TrialConfig.get_max_trial_days(),
        "trial_restrictions": [
            "Trial can only be used once per email address",
            "Trial can only be used once per phone number (primary or secondary)", 
            "After trial expiration, user must upgrade to GOLD or create new account with different contact details"
        ]
    }
    
