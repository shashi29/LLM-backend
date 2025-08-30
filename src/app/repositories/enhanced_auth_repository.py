# app/repositories/enhanced_auth_repository.py
import random
import hashlib
from typing import Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.enhanced_auth import EnhancedOTP, IdentifierType, OTPPurpose
from app.models.client_user import ClientUser

# Import the enhanced SMS/Email functions
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def send_sms_via_msg91(phone_number: str, otp: str) -> bool:
    """Enhanced SMS function from paste.txt"""
    try:
        print(f"🔍 SMS DEBUG: Starting SMS send process")
        print(f"📱 Phone number: {phone_number}, OTP: {otp}")
        
        msg91_auth_key = os.getenv("MSG91_AUTH_KEY")
        msg91_sms_template_id = os.getenv("MSG91_SMS_TEMPLATE_ID")
        msg91_sender_id = os.getenv("MSG91_SENDER_ID", "TXTLCL")
        
        if not msg91_auth_key:
            raise Exception("MSG91_AUTH_KEY is required")
        
        clean_phone = phone_number.replace(" ", "").replace("-", "").replace("+", "")
        if not clean_phone.startswith("91") and len(clean_phone) == 10:
            clean_phone = "91" + clean_phone
        
        use_template = msg91_sms_template_id and msg91_sms_template_id.strip()
        
        if use_template:
            url = "https://control.msg91.com/api/v5/otp"
            headers = {"Content-Type": "application/json", "authkey": msg91_auth_key}
            sms_data = {
                "template_id": msg91_sms_template_id,
                "mobile": clean_phone,
                "authkey": msg91_auth_key,
                "sender": msg91_sender_id,
                "otp": str(otp),
                "var1": str(otp)
            }
            response = requests.post(url, headers=headers, data=json.dumps(sms_data), timeout=30)
        else:
            url = f"https://control.msg91.com/api/v5/otp?authkey={msg91_auth_key}&mobile={clean_phone}&sender={msg91_sender_id}&otp={otp}"
            response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                return response_data.get("type") == "success"
            except:
                return "success" in response.text.lower()
        return False
        
    except Exception as e:
        print(f"❌ SMS Error: {e}")
        raise e

# def send_email_via_msg91(receiver_email: str, otp: str) -> bool:
#     """Enhanced Email function from paste.txt"""
#     try:
#         print(f"Sending OTP {otp} to email {receiver_email} via MSG91")
        
#         msg91_auth_key = os.getenv("MSG91_AUTH_KEY")
#         msg91_template_id = os.getenv("MSG91_EMAIL_TEMPLATE_ID")
#         msg91_sender_email = os.getenv("MSG91_SENDER_EMAIL", "noreply@wtyy8j.mailer91.com")
#         msg91_sender_name = os.getenv("MSG91_SENDER_NAME", "GBusiness AI")
#         msg91_domain = os.getenv("MSG91_DOMAIN", "wtyy8j.mailer91.com")
        
#         if not msg91_auth_key or not msg91_template_id:
#             raise Exception("MSG91 credentials are required for email")
        
#         url = "https://control.msg91.com/api/v5/email/send"
#         headers = {"Content-Type": "application/json", "authkey": msg91_auth_key}
        
#         email_data = {
#             "to": [{"email": receiver_email, "name": "User"}],
#             "from": {"email": msg91_sender_email, "name": msg91_sender_name},
#             "domain": msg91_domain,
#             "template_id": msg91_template_id,
#             "variables": {
#                 "otp": str(otp),
#                 "user_name": "User",
#                 "company_name": "ONEVEGA Systems Pvt Ltd"
#             }
#         }
        
#         response = requests.post(url, headers=headers, data=json.dumps(email_data), timeout=30)
        
#         if response.status_code == 200:
#             try:
#                 response_data = response.json()
#                 return (response_data.get("type") == "success" or 
#                        response_data.get("status") == "success" or
#                        not response_data.get("hasError", True))
#             except:
#                 return "success" in response.text.lower()
#         return False
        
#     except Exception as e:
#         print(f"❌ Email Error: {e}")
#         raise e

def send_email_via_msg91(email: str, otp: str, purpose: str = "login") -> bool:
    """Send OTP via MSG91 email template"""
    try:
        print(f"📧 Sending {purpose} OTP to {email}")

        auth_key = os.getenv("MSG91_AUTH_KEY")
        template_id = os.getenv("MSG91_EMAIL_TEMPLATE_ID")
        sender_email = os.getenv("MSG91_SENDER_EMAIL")
        sender_name = os.getenv("MSG91_SENDER_NAME")
        domain = os.getenv("MSG91_DOMAIN")

        if not all([auth_key, template_id]):
            raise Exception("MSG91 credentials not configured")

        url = "https://control.msg91.com/api/v5/email/send"
        headers = {
            "Content-Type": "application/json",
            "authkey": auth_key
        }

        # Email template variables
        email_data = {
            "to": [{"email": email, "name": "User"}],
            "from": {
                "email": sender_email,
                "name": sender_name
            },
            "domain": domain,
            "template_id": template_id,
            "variables": {
                "otp": str(otp),
                "user_name": "User",
                "company_name": "GBusiness AI",
                "purpose": purpose.replace("_", " ").title()
            }
        }

        print(f"📤 Sending email via MSG91...")
        response = requests.post(url, headers=headers, data=json.dumps(email_data), timeout=30)

        print(f"📥 Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            try:
                response_data = response.json()
                if (response_data.get("type") == "success" or
                    "success" in str(response_data).lower()):
                    print(f"✅ Email sent successfully to {email}")
                    return True
                else:
                    print(f"❌ MSG91 Error: {response_data}")
                    return False
            except json.JSONDecodeError:
                if "success" in response.text.lower():
                    print(f"✅ Email sent successfully to {email}")
                    return True
                else:
                    print(f"❌ Unexpected response: {response.text}")
                    return False
        else:
            print(f"❌ HTTP Error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False

class EnhancedAuthRepository(BaseRepository):
    def __init__(self):
        super().__init__('OTPs')
        
        # Create enhanced OTPs table
        create_otp_table_query = text("""
            CREATE TABLE IF NOT EXISTS OTPs (
                id SERIAL PRIMARY KEY,
                identifier VARCHAR(255) NOT NULL,
                identifier_type VARCHAR(10) NOT NULL CHECK (identifier_type IN ('PHONE', 'EMAIL')),
                otp_code VARCHAR(6) NOT NULL,
                purpose VARCHAR(20) NOT NULL CHECK (purpose IN ('LOGIN', 'RESET_PASSWORD', 'CHANGE_PASSWORD', 'VERIFY_EMAIL')),
                user_id INTEGER REFERENCES ClientUsers(id) ON DELETE CASCADE,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                is_verified BOOLEAN DEFAULT FALSE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP NULL
            );
        """)
        
        # Add indexes
        create_indexes_query = text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_otp_identifier_purpose 
            ON OTPs (identifier, purpose) WHERE is_verified = FALSE;
            
            CREATE INDEX IF NOT EXISTS idx_otp_expires ON OTPs (expires_at);
        """)
        
        # Add columns to ClientUsers if they don't exist
        add_columns_query = text("""
            ALTER TABLE ClientUsers 
            ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP NULL,
            ADD COLUMN IF NOT EXISTS last_password_change TIMESTAMP NULL;
        """)
        
        try:
            self.create_table(create_otp_table_query)
            self.create_table(create_indexes_query)
            self.create_table(add_columns_query)
        except Exception as e:
            print(f"Table creation warning: {e}")

    def generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return str(random.randint(100000, 999999))

    def send_otp(self, identifier: str, identifier_type: IdentifierType, 
                 purpose: OTPPurpose, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Send OTP via SMS or Email
        Returns: (success, message)
        """
        try:
            # Clean up expired OTPs
            self._cleanup_expired_otps()
            
            # Delete any existing unverified OTP for this identifier and purpose
            self._delete_existing_otp(identifier, purpose)
            
            # Generate new OTP
            otp_code = self.generate_otp()
            expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes expiry
            
            # Store OTP in database
            otp_record = EnhancedOTP(
                identifier=identifier,
                identifier_type=identifier_type,
                otp_code=otp_code,
                purpose=purpose,
                user_id=user_id,
                expires_at=expires_at
            )
            
            stored_otp = self._store_otp(otp_record)
            if not stored_otp:
                return False, "Failed to store OTP"
            
            # Send OTP via appropriate channel
            if identifier_type == IdentifierType.PHONE:
                success = send_sms_via_msg91(identifier, otp_code)
                channel = "SMS"
            else:  # EMAIL
                success = send_email_via_msg91(identifier, otp_code, purpose.value.lower())
                channel = "Email"
            
            if success:
                return True, f"OTP sent successfully via {channel}"
            else:
                # Clean up stored OTP if sending failed
                self._delete_otp_by_id(stored_otp.id)
                return False, f"Failed to send OTP via {channel}"
                
        except Exception as e:
            return False, f"Error sending OTP: {str(e)}"

    def verify_otp(self, identifier: str, otp_code: str, purpose: OTPPurpose) -> Tuple[bool, str, Optional[EnhancedOTP]]:
        """
        Verify OTP
        Returns: (success, message, otp_record)
        """
        try:
            # Get OTP record
            otp_record = self._get_active_otp(identifier, purpose)
            
            if not otp_record:
                return False, "No active OTP found for this identifier", None
            
            # Check if expired
            if datetime.utcnow() > otp_record.expires_at:
                self._delete_otp_by_id(otp_record.id)
                return False, "OTP has expired", None
            
            # Check attempts
            if otp_record.attempts >= otp_record.max_attempts:
                self._delete_otp_by_id(otp_record.id)
                return False, "Maximum OTP attempts exceeded", None
            
            # Increment attempts
            self._increment_otp_attempts(otp_record.id)
            
            # Verify OTP
            if otp_record.otp_code == otp_code:
                # Mark as verified
                self._mark_otp_verified(otp_record.id)
                otp_record.is_verified = True
                otp_record.verified_at = datetime.utcnow()
                return True, "OTP verified successfully", otp_record
            else:
                return False, "Invalid OTP code", None
                
        except Exception as e:
            return False, f"Error verifying OTP: {str(e)}", None

    def reset_password(self, identifier: str, identifier_type: IdentifierType, 
                      otp_code: str, new_password: str) -> Tuple[bool, str]:
        """Reset user password using OTP"""
        try:
            # Verify OTP
            success, message, otp_record = self.verify_otp(identifier, otp_code, OTPPurpose.RESET_PASSWORD)
            
            if not success:
                return False, message
            
            # Find user by identifier
            user = self._find_user_by_identifier(identifier, identifier_type)
            if not user:
                return False, "User not found"
            
            # Update password
            success = self._update_user_password(user.id, new_password)
            if success:
                # Clean up OTP
                self._delete_otp_by_id(otp_record.id)
                return True, "Password reset successfully"
            else:
                return False, "Failed to update password"
                
        except Exception as e:
            return False, f"Error resetting password: {str(e)}"

    def change_password(self, user_id: int, current_password: str, new_password: str,
                       identifier: str, otp_code: str) -> Tuple[bool, str]:
        """Change user password with OTP verification"""
        try:
            # Verify current password
            user = self._get_user_by_id(user_id)
            if not user or user.password != current_password:
                return False, "Current password is incorrect"
            
            # Verify OTP
            success, message, otp_record = self.verify_otp(identifier, otp_code, OTPPurpose.CHANGE_PASSWORD)
            
            if not success:
                return False, message
            
            # Update password
            success = self._update_user_password(user_id, new_password)
            if success:
                # Clean up OTP
                self._delete_otp_by_id(otp_record.id)
                return True, "Password changed successfully"
            else:
                return False, "Failed to update password"
                
        except Exception as e:
            return False, f"Error changing password: {str(e)}"

    # Private helper methods
    def _store_otp(self, otp: EnhancedOTP) -> Optional[EnhancedOTP]:
        """Store OTP in database"""
        query = text("""
            INSERT INTO OTPs (identifier, identifier_type, otp_code, purpose, user_id, expires_at)
            VALUES (:identifier, :identifier_type, :otp_code, :purpose, :user_id, :expires_at)
            RETURNING id, identifier, identifier_type, otp_code, purpose, user_id, 
                      attempts, max_attempts, is_verified, expires_at, created_at, verified_at;
        """)
        
        values = {
            "identifier": otp.identifier,
            "identifier_type": otp.identifier_type.value,
            "otp_code": otp.otp_code,
            "purpose": otp.purpose.value,
            "user_id": otp.user_id,
            "expires_at": otp.expires_at
        }
        
        result = self.execute_query(query, values)
        if result:
            return EnhancedOTP(**dict(zip(EnhancedOTP.__annotations__, result)))
        return None

    def _get_active_otp(self, identifier: str, purpose: OTPPurpose) -> Optional[EnhancedOTP]:
        """Get active OTP for identifier and purpose"""
        query = text("""
            SELECT id, identifier, identifier_type, otp_code, purpose, user_id, 
                   attempts, max_attempts, is_verified, expires_at, created_at, verified_at
            FROM OTPs 
            WHERE identifier = :identifier AND purpose = :purpose AND is_verified = FALSE
            ORDER BY created_at DESC LIMIT 1;
        """)
        
        values = {"identifier": identifier, "purpose": purpose.value}
        result = self.execute_query(query, values)
        
        if result:
            return EnhancedOTP(**dict(zip(EnhancedOTP.__annotations__, result)))
        return None

    def _delete_existing_otp(self, identifier: str, purpose: OTPPurpose) -> None:
        """Delete existing unverified OTP"""
        query = text("""
            DELETE FROM OTPs 
            WHERE identifier = :identifier AND purpose = :purpose AND is_verified = FALSE;
        """)
        values = {"identifier": identifier, "purpose": purpose.value}
        self.execute_delete_query(query, values)

    def _delete_otp_by_id(self, otp_id: int) -> None:
        """Delete OTP by ID"""
        query = text("DELETE FROM OTPs WHERE id = :otp_id;")
        self.execute_delete_query(query, {"otp_id": otp_id})

    def _increment_otp_attempts(self, otp_id: int) -> None:
        """Increment OTP attempts"""
        query = text("UPDATE OTPs SET attempts = attempts + 1 WHERE id = :otp_id;")
        self.execute_delete_query(query, {"otp_id": otp_id})

    def _mark_otp_verified(self, otp_id: int) -> None:
        """Mark OTP as verified"""
        query = text("""
            UPDATE OTPs 
            SET is_verified = TRUE, verified_at = CURRENT_TIMESTAMP 
            WHERE id = :otp_id;
        """)
        self.execute_delete_query(query, {"otp_id": otp_id})

    def _cleanup_expired_otps(self) -> None:
        """Clean up expired OTPs"""
        query = text("DELETE FROM OTPs WHERE expires_at < CURRENT_TIMESTAMP;")
        self.execute_delete_query(query)

    def _find_user_by_identifier(self, identifier: str, identifier_type: IdentifierType) -> Optional[ClientUser]:
        """Find user by phone or email"""
        if identifier_type == IdentifierType.EMAIL:
            column = "email"
        else:
            column = "phone_number"
            
        query = text(f"SELECT * FROM ClientUsers WHERE {column} = :identifier;")
        result = self.execute_query(query, {"identifier": identifier})
        
        if result:
            return ClientUser(**result._mapping)#ClientUser(**dict(zip(ClientUser.__annotations__, result)))
        return None

    def _get_user_by_id(self, user_id: int) -> Optional[ClientUser]:
        """Get user by ID"""
        query = text("SELECT * FROM ClientUsers WHERE id = :user_id;")
        result = self.execute_query(query, {"user_id": user_id})
        
        if result:
            return ClientUser(**result._mapping)
        return None

    def _update_user_password(self, user_id: int, new_password: str) -> bool:
        """Update user password"""
        query = text("""
            UPDATE ClientUsers 
            SET password = :password, last_password_change = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = :user_id;
        """)
        
        try:
            self.execute_delete_query(query, {"password": new_password, "user_id": user_id})
            return True
        except:
            return False