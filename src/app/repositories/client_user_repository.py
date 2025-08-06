# app/repositories/client_users_repository.py
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlmodel import Session, select, create_engine, or_
from fastapi import HTTPException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
import requests
from ..models.client_user import ClientUser, OTP, SubscriptionType, TrialConfig
import requests
from typing import Any
from datetime import datetime, timedelta  
from jose import jwt
import random
import os
import json
from urllib.parse import quote_plus
from dotenv import load_dotenv
import base64
import mimetypes
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
# You may need: pip install python-pptx
from pptx import Presentation
from pptx.util import Inches
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
from io import BytesIO
import pandas as pd
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE



# Load environment variables from .env file
load_dotenv()

def send_sms_via_msg91(phone_number: str, otp: str) -> bool:
    """
    Enhanced SMS function with detailed debugging
    """
    try:
        print("=" * 60)
        print(f"🔍 SMS DEBUG: Starting SMS send process")
        print(f"📱 Original phone number: {phone_number}")
        print(f"🔢 OTP: {otp}")
        
        # MSG91 SMS credentials from environment variables
        msg91_auth_key = os.getenv("MSG91_AUTH_KEY")
        msg91_sms_template_id = os.getenv("MSG91_SMS_TEMPLATE_ID")
        msg91_sender_id = os.getenv("MSG91_SENDER_ID", "TXTLCL")
        
        print(f"🔑 Auth Key: {'✅ Present' if msg91_auth_key else '❌ Missing'}")
        print(f"📋 Template ID: {msg91_sms_template_id if msg91_sms_template_id else '❌ Not set'}")
        print(f"📤 Sender ID: {msg91_sender_id}")
        
        if not msg91_auth_key:
            print("ERROR: MSG91_AUTH_KEY not configured")
            raise Exception("MSG91_AUTH_KEY is required")
        
        # Clean phone number with detailed logging
        clean_phone = phone_number.replace(" ", "").replace("-", "").replace("+", "")
        print(f"📱 After cleaning: {clean_phone}")
        
        # Add country code if needed
        if not clean_phone.startswith("91") and len(clean_phone) == 10:
            clean_phone = "91" + clean_phone
            print(f"📱 Added country code: {clean_phone}")
        
        # Validate phone number format
        if len(clean_phone) != 12 or not clean_phone.startswith("91"):
            print(f"⚠️ WARNING: Phone number format might be incorrect: {clean_phone}")
            print(f"   Expected format: 91XXXXXXXXXX (12 digits starting with 91)")
        
        print(f"📱 Final phone number: {clean_phone}")
        
        # Determine SMS method
        use_template = msg91_sms_template_id and msg91_sms_template_id.strip()
        print(f"🎯 SMS Method: {'Template-based' if use_template else 'Direct SMS'}")
        
        if use_template:
            # Template method
            print("📋 Using SMS template method")
            url = "https://control.msg91.com/api/v5/otp"
            headers = {
                "Content-Type": "application/json",
                "authkey": msg91_auth_key
            }
            
            sms_data = {
                "template_id": msg91_sms_template_id,
                "mobile": clean_phone,
                "authkey": msg91_auth_key,
                "sender": msg91_sender_id,
                "otp": str(otp),
                "var1": str(otp)
            }
            
            print(f"📤 Template Request URL: {url}")
            print(f"📋 Template Data: {json.dumps(sms_data, indent=2)}")
            
            response = requests.post(url, headers=headers, data=json.dumps(sms_data), timeout=30)
            
        else:
            # Direct SMS method - try multiple approaches
            print("📤 Using direct SMS method")
            
            # Try Method 1: Simple OTP API
            print("🔄 Trying Method 1: Simple OTP API")
            url1 = f"https://control.msg91.com/api/v5/otp?authkey={msg91_auth_key}&mobile={clean_phone}&sender={msg91_sender_id}&otp={otp}"
            print(f"📤 Request URL: {url1}")
            
            response1 = requests.get(url1, timeout=30)
            print(f"📥 Method 1 Response: {response1.status_code} - {response1.text}")
            
            if response1.status_code == 200:
                response = response1
            else:
                # Try Method 2: Flow API
                print("🔄 Trying Method 2: Flow API")
                url2 = "https://control.msg91.com/api/v5/flow"
                headers2 = {
                    "Content-Type": "application/json",
                    "authkey": msg91_auth_key
                }
                
                message = f"Dear User, OTP is {otp} for your login to GBusiness AI agent. Do not share OTP with anyone. For any issues, contact ONEVEGA Systems Pvt Ltd."
                
                sms_data2 = {
                    "sender": msg91_sender_id,
                    "route": "4",
                    "country": "91",
                    "sms": [
                        {
                            "message": message,
                            "to": [clean_phone]
                        }
                    ]
                }
                
                print(f"📤 Flow API URL: {url2}")
                print(f"📋 Flow Data: {json.dumps(sms_data2, indent=2)}")
                
                response2 = requests.post(url2, headers=headers2, data=json.dumps(sms_data2), timeout=30)
                print(f"📥 Method 2 Response: {response2.status_code} - {response2.text}")
                response = response2
        
        # Detailed response analysis
        print("=" * 40)
        print("📥 RESPONSE ANALYSIS:")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Raw Response: {response.text}")
        
        try:
            response_data = response.json()
            print(f"Parsed JSON: {json.dumps(response_data, indent=2)}")
            
            # Check for specific MSG91 response patterns
            if response_data.get("type") == "success":
                print("✅ MSG91 reports SUCCESS")
                
                # Check for message ID or request ID
                if "request_id" in response_data:
                    print(f"📋 Request ID: {response_data['request_id']}")
                if "message_id" in response_data:
                    print(f"📋 Message ID: {response_data['message_id']}")
                    
                print("🔍 DELIVERY STATUS CHECK:")
                print("   1. Check MSG91 dashboard → SMS → Reports")
                print("   2. Look for delivery status of this message")
                print("   3. Check if sender ID is approved")
                print("   4. Verify phone number is correct")
                
                return True
            else:
                print(f"❌ MSG91 reports ERROR: {response_data}")
                return False
                
        except json.JSONDecodeError:
            print("⚠️ Response is not JSON format")
            if "success" in response.text.lower():
                print("✅ Text response indicates SUCCESS")
                return True
            else:
                print(f"❌ Text response: {response.text}")
                return False
        
    except Exception as e:
        print(f"❌ SMS Error: {e}")
        raise e


def send_sms(phone_number, otp):
    """
    Send SMS using MSG91 instead of the old SMS service
    """
    try:
        success = send_sms_via_msg91(phone_number, otp)
        if success:
            print("SMS sent successfully via MSG91.")
            return True
        else:
            raise Exception("MSG91 SMS sending failed")
    except Exception as e:
        print(f"Failed to send SMS via MSG91: {e}")
        raise Exception(f"SMS sending failed: {e}")

def send_email_via_msg91(receiver_email: str, otp: str) -> bool:
    """
    Send email OTP using MSG91 template
    """
    try:
        print(f"Sending OTP {otp} to email {receiver_email} via MSG91 template")
        
        # MSG91 credentials from environment variables
        msg91_auth_key = os.getenv("MSG91_AUTH_KEY")
        msg91_template_id = os.getenv("MSG91_EMAIL_TEMPLATE_ID")
        
        # Get domain configuration
        msg91_sender_email = os.getenv("MSG91_SENDER_EMAIL", "noreply@wtyy8j.mailer91.com")
        msg91_sender_name = os.getenv("MSG91_SENDER_NAME", "GBusiness AI")
        msg91_domain = os.getenv("MSG91_DOMAIN", "wtyy8j.mailer91.com")
        
        # Validate required credentials
        if not msg91_auth_key:
            raise Exception("MSG91_AUTH_KEY is required")
        
        if not msg91_template_id:
            raise Exception("MSG91_EMAIL_TEMPLATE_ID is required for template method")
        
        print(f"Using domain: {msg91_domain}")
        print(f"Sender email: {msg91_sender_email}")
        print(f"Template ID: {msg91_template_id}")
        
        # MSG91 Email API endpoint
        url = "https://control.msg91.com/api/v5/email/send"
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "authkey": msg91_auth_key
        }
        
        # Template-based email data (much cleaner)
        email_data = {
            "to": [
                {
                    "email": receiver_email,
                    "name": "User"
                }
            ],
            "from": {
                "email": msg91_sender_email,
                "name": msg91_sender_name
            },
            "domain": msg91_domain,
            "template_id": msg91_template_id,
            "variables": {
                "otp": str(otp),
                "user_name": "User",
                "company_name": "ONEVEGA Systems Pvt Ltd"
            }
        }
        
        print(f"Sending template-based email request...")
        
        # Send the request
        response = requests.post(
            url, 
            headers=headers, 
            data=json.dumps(email_data),
            timeout=30
        )
        
        print(f"MSG91 API Response Status: {response.status_code}")
        print(f"MSG91 API Response: {response.text}")
        
        # Handle response
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"Parsed response: {response_data}")
                
                # Check for success indicators
                if (response_data.get("type") == "success" or 
                    response_data.get("status") == "success" or
                    "success" in str(response_data).lower() or
                    not response_data.get("hasError", True)):
                    print(f"✅ Template email sent successfully to {receiver_email}")
                    return True
                else:
                    print(f"❌ MSG91 template API error: {response_data}")
                    raise Exception(f"MSG91 template API error: {response_data}")
                    
            except json.JSONDecodeError:
                # Handle plain text responses
                if "success" in response.text.lower() or "sent" in response.text.lower():
                    print(f"✅ Template email sent successfully to {receiver_email}")
                    return True
                else:
                    print(f"❌ MSG91 unexpected template response: {response.text}")
                    raise Exception(f"MSG91 unexpected template response: {response.text}")
        
        elif response.status_code == 422:
            try:
                response_data = response.json()
                errors = response_data.get("errors", {})
                
                if "template_id" in errors:
                    template_error = errors["template_id"][0] if isinstance(errors["template_id"], list) else errors["template_id"]
                    print(f"❌ MSG91 Template Error: {template_error}")
                    print("🔧 Solutions:")
                    print("   1. Check if template ID is correct in .env file")
                    print("   2. Verify template exists in MSG91 dashboard")
                    print("   3. Ensure template has {{otp}} variable")
                    raise Exception(f"MSG91 Template Error: {template_error}")
                
                print(f"❌ MSG91 Template Validation Error: {response_data}")
                raise Exception(f"MSG91 Template Validation Error: {response_data}")
                    
            except json.JSONDecodeError:
                print(f"❌ MSG91 Template Error (422): {response.text}")
                raise Exception(f"MSG91 Template Error (422): {response.text}")
        
        else:
            print(f"❌ MSG91 Template API Error - Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            raise Exception(f"MSG91 Template API Error {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ MSG91 API request timed out")
        raise Exception("MSG91 API request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ MSG91 API connection error")
        raise Exception("MSG91 API connection error")
    except Exception as e:
        print(f"❌ Error with MSG91 template: {e}")
        raise e
    
class ClientUsersRepository:
    def __init__(self):
        try:
            # Get the values from the environment
            db_user = os.getenv("DB_USER")
            db_password = os.getenv("DB_PASSWORD")
            db_host = os.getenv("DB_HOST")
            db_port = os.getenv("DB_PORT")
            db_name = os.getenv("DB_NAME")
            
            # TEMPORARY FIX: Override with correct values for Cloud SQL Proxy
            if ":" in str(db_host):
                print("⚠️  Detected old Cloud SQL format, overriding with proxy settings")
                db_host = "127.0.0.1"
                db_port = "5433"
                print(f"✅ Using proxy connection: {db_host}:{db_port}")
            
            print(f"Connection attempt with: {db_user}@{db_host}:{db_port}/{db_name}")
            
            
            # Validate required environment variables
            if not all([db_user, db_password, db_host, db_name]):
                missing_vars = []
                if not db_user: missing_vars.append("DB_USER")
                if not db_password: missing_vars.append("DB_PASSWORD") 
                if not db_host: missing_vars.append("DB_HOST")
                if not db_name: missing_vars.append("DB_NAME")
                raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
            
            # Use urllib.parse to properly encode the password for a database URL
            from urllib.parse import quote_plus
            db_password_encoded = quote_plus(db_password)
            
            # For Cloud SQL Proxy connection (localhost)
            if db_host == "127.0.0.1" or db_host == "localhost":
                print("✅ Using Cloud SQL Proxy connection")
                
                if db_port:
                    try:
                        port_num = int(db_port)
                        if port_num <= 0 or port_num > 65535:
                            raise ValueError("Port must be between 1 and 65535")
                    except ValueError as e:
                        raise Exception(f"Invalid port number '{db_port}': {e}")
                    
                    self.database_url = f"postgresql://{db_user}:{db_password_encoded}@{db_host}:{db_port}/{db_name}"
                else:
                    self.database_url = f"postgresql://{db_user}:{db_password_encoded}@{db_host}:5432/{db_name}"
                    
            else:
                # Handle other connection types as before
                if ":" in db_host and not db_port:
                    print("Detected Cloud SQL connection name format")
                    self.database_url = f"postgresql+psycopg2://{db_user}:{db_password_encoded}@/{db_name}?host=/cloudsql/{db_host}"
                    
                elif db_port:
                    print("Using standard host:port connection")
                    try:
                        port_num = int(db_port)
                        if port_num <= 0 or port_num > 65535:
                            raise ValueError("Port must be between 1 and 65535")
                    except ValueError as e:
                        raise Exception(f"Invalid port number '{db_port}': {e}")
                    
                    self.database_url = f"postgresql://{db_user}:{db_password_encoded}@{db_host}:{db_port}/{db_name}"
                    
                else:
                    print("Using host with default port (5432)")
                    self.database_url = f"postgresql://{db_user}:{db_password_encoded}@{db_host}:5432/{db_name}"
            
            
            print(f"Final database URL format: {self.database_url.replace(db_password_encoded, '***')}")
            
            # Create engine with the URL
            self.engine = create_engine(
                self.database_url,
                echo=True,  # Set to False in production
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600   # Recycle connections every hour
            )
            
            # Test connection
            with self.engine.connect() as conn:
                print("✅ Database connection successful!")
                
            # Create tables
            ClientUser.metadata.create_all(self.engine)
            OTP.metadata.create_all(self.engine)
            print("✅ Database tables created/verified!")
            
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            print("\n🔧 TROUBLESHOOTING TIPS:")
            print("1. Make sure Cloud SQL Proxy is running:")
            print("   cloud-sql-proxy --port 5433 'reliable-vector-429905-e8:us-central1:backend-database'")
            print("2. Check your .env file has:")
            print("   DB_HOST=127.0.0.1")
            print("   DB_PORT=5433")
            print("3. Verify database credentials are correct")
            print(f"4. Current connection: {db_user}@{db_host}:{db_port}/{db_name}")
            
            # Don't raise in production, but useful for debugging
            raise e
        
    def _generate_otp(self, length: int = 6) -> str:
        return random.randint(100000, 999999)

    def _validate_phone_number_uniqueness(self, customer_number: str, professional_contact_number: str, user_id: Optional[int] = None):
        """
        Validates that phone numbers are unique across both primary and secondary fields.
        A number can only be used once as either primary or secondary number.
        """
        with Session(self.engine) as session:
            # Check if customer_number already exists as primary or secondary number
            if customer_number:
                stmt = select(ClientUser).where(
                    or_(
                        ClientUser.customer_number == customer_number,
                        ClientUser.professional_contact_number == customer_number
                    )
                )
                if user_id:  # For updates, exclude current user
                    stmt = stmt.where(ClientUser.id != user_id)
                
                existing_user = session.exec(stmt).first()
                if existing_user:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Phone number {customer_number} is already in use as {'primary' if existing_user.customer_number == customer_number else 'secondary'} contact number"
                    )
            
            # Check if professional_contact_number already exists as primary or secondary number
            if professional_contact_number:
                stmt = select(ClientUser).where(
                    or_(
                        ClientUser.customer_number == professional_contact_number,
                        ClientUser.professional_contact_number == professional_contact_number
                    )
                )
                if user_id:  # For updates, exclude current user
                    stmt = stmt.where(ClientUser.id != user_id)
                
                existing_user = session.exec(stmt).first()
                if existing_user:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Phone number {professional_contact_number} is already in use as {'primary' if existing_user.customer_number == professional_contact_number else 'secondary'} contact number"
                    )

    def _validate_trial_eligibility(self, customer_number: str, email: str, professional_contact_number: str = None):
        """
        Check if user is eligible for trial subscription.
        A user can only use trial once across all their contact details.
        """
        with Session(self.engine) as session:
            # Check if any user with same email, primary phone, or secondary phone has used trial
            conditions = [
                ClientUser.email == email,
                ClientUser.customer_number == customer_number
            ]
            
            if professional_contact_number:
                conditions.extend([
                    ClientUser.customer_number == professional_contact_number,
                    ClientUser.professional_contact_number == professional_contact_number
                ])
            
            if customer_number:
                conditions.append(ClientUser.professional_contact_number == customer_number)
            
            stmt = select(ClientUser).where(
                or_(*conditions),
                ClientUser.trial_used == True
            )
            
            existing_trial_user = session.exec(stmt).first()
            if existing_trial_user:
                raise HTTPException(
                    status_code=400,
                    detail="Trial subscription has already been used with these contact details. Please subscribe to GOLD plan or use different contact information."
                )

    def _setup_subscription(self, user: ClientUser, trial_days: int = 30):
        """
        Setup subscription details based on subscription type.
        """
        current_time = datetime.utcnow()
        
        if user.subscription == SubscriptionType.GOLD:
            # Gold subscription - permanent access
            user.subscription_start_date = current_time
            user.subscription_end_date = None  # No expiry for Gold
            user.is_subscription_active = True
            user.trial_used = False  # Gold users don't use trial
            user.total_trial_days_used = 0
            
        elif user.subscription == SubscriptionType.BASIC:
            # Basic subscription - trial period
            user.subscription_start_date = current_time
            user.subscription_end_date = current_time + timedelta(days=trial_days)
            user.is_subscription_active = True
            user.trial_used = True
            user.total_trial_days_used = trial_days
        
        return user

    def create_user(self, user: ClientUser, trial_days: int = 30) -> Any:
        # Validate phone number uniqueness before creating
        self._validate_phone_number_uniqueness(
            user.customer_number, 
            user.professional_contact_number
        )
        
        # Validate trial eligibility if subscription is BASIC
        if user.subscription == SubscriptionType.BASIC:
            self._validate_trial_eligibility(
                user.customer_number,
                user.email,
                user.professional_contact_number
            )
        
        # Setup subscription details
        user = self._setup_subscription(user, trial_days)
        
        with Session(self.engine) as session:
            db_user = user
            session.add(db_user)
            try:
                session.commit()
                session.refresh(db_user)
                return db_user
            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=400, detail=str(e))

    def check_subscription_status(self, user_id: int) -> dict:
        """
        Check and update subscription status for a user.
        Returns subscription details and access status.
        """
        with Session(self.engine) as session:
            user = session.get(ClientUser, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            current_time = datetime.utcnow()
            subscription_info = {
                "user_id": user.id,
                "subscription_type": user.subscription,
                "is_active": user.is_subscription_active,
                "has_access": False,
                "message": "",
                "days_remaining": None,
                "trial_used": user.trial_used
            }
            
            if user.subscription == SubscriptionType.GOLD:
                subscription_info["has_access"] = user.is_subscription_active
                subscription_info["message"] = "Gold subscription - Permanent access" if user.is_subscription_active else "Gold subscription inactive"
                
            elif user.subscription == SubscriptionType.BASIC:
                if user.subscription_end_date and current_time <= user.subscription_end_date:
                    # Trial is still active
                    days_remaining = (user.subscription_end_date - current_time).days
                    subscription_info["has_access"] = True
                    subscription_info["days_remaining"] = days_remaining
                    subscription_info["message"] = f"Basic trial active - {days_remaining} days remaining"
                else:
                    # Trial has expired
                    user.is_subscription_active = False
                    subscription_info["has_access"] = False
                    subscription_info["message"] = "Basic trial expired - Please upgrade to Gold subscription"
                    
                    # Update user status in database
                    session.add(user)
                    session.commit()
            
            return subscription_info

    def upgrade_to_gold(self, user_id: int) -> Any:
        """
        Upgrade user from Basic to Gold subscription.
        """
        with Session(self.engine) as session:
            user = session.get(ClientUser, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if user.subscription == SubscriptionType.GOLD:
                raise HTTPException(status_code=400, detail="User already has Gold subscription")
            
            # Upgrade to Gold
            user.subscription = SubscriptionType.GOLD
            user.subscription_start_date = datetime.utcnow()
            user.subscription_end_date = None  # No expiry for Gold
            user.is_subscription_active = True
            user.updated_at = datetime.utcnow()
            
            try:
                session.add(user)
                session.commit()
                session.refresh(user)
                return user
            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=400, detail=str(e))

    def get_users(self) -> List[ClientUser]:
        with Session(self.engine) as session:
            statement = select(ClientUser)
            return session.exec(statement).all()

    def get_user(self, user_id: int) -> Optional[ClientUser]:
        with Session(self.engine) as session:
            statement = select(ClientUser).where(ClientUser.id == user_id)
            user = session.exec(statement).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return user

    def update_user(self, user_id: int, user: ClientUser) -> Any:
        with Session(self.engine) as session:
            db_user = session.get(ClientUser, user_id)
            if not db_user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Validate phone number uniqueness before updating
            self._validate_phone_number_uniqueness(
                user.customer_number, 
                user.professional_contact_number,
                user_id=user_id
            )
            
            user_data = user.dict(exclude_unset=True)
            user_data["updated_at"] = datetime.utcnow()
            
            # Don't allow direct subscription changes through update
            # Use specific methods for subscription management
            if "subscription" in user_data:
                del user_data["subscription"]
            
            for key, value in user_data.items():
                setattr(db_user, key, value)
            
            try:
                session.add(db_user)
                session.commit()
                session.refresh(db_user)
                return db_user
            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=400, detail=str(e))

    def delete_user(self, user_id: int) -> Any:
        with Session(self.engine) as session:
            user = session.get(ClientUser, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            session.delete(user)
            session.commit()
            return user

    def login_user(self, user_data: ClientUser) -> Any:
        with Session(self.engine) as session:
            statement = select(ClientUser).where(
                ClientUser.email == user_data.email,
                ClientUser.password == user_data.password
            )
            user = session.exec(statement).first()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # Check subscription status on login
            subscription_status = self.check_subscription_status(user.id)
            
            return {
                "user": user,
                "subscription_status": subscription_status
            }
        

    def send_email(self, receiver_email, otp):
        """
        Send OTP email using MSG91 API only.
        Raises exception if MSG91 fails.
        """
        print(f"Sending OTP to {receiver_email} via MSG91")
        
        try:
            success = send_email_via_msg91(receiver_email, otp)
            if success:
                print(f"✅ Email sent successfully to {receiver_email}")
                return True
            else:
                raise Exception("MSG91 email sending failed")
                
        except Exception as e:
            print(f"❌ Failed to send email via MSG91: {e}")
            # Re-raise the exception so calling code knows it failed
            raise Exception(f"Email sending failed: {e}")
    

    def store_otp(self, identifier: str, is_email: bool = False) -> str:
        otp = self._generate_otp()
        with Session(self.engine) as session:
            # Delete any existing OTP for this identifier
            statement = select(OTP).where(
                OTP.email == identifier if is_email else OTP.phone_number == identifier
            )
            existing_otp = session.exec(statement).first()
            if existing_otp:
                session.delete(existing_otp)
            
            # Create new OTP
            new_otp = OTP(
                phone_number=None if is_email else identifier,
                email=identifier if is_email else None,
                otp=str(otp),  # Ensure otp is stored as string
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=10)
            )
            session.add(new_otp)
            session.commit()

            # Send OTP via appropriate channel
            # OTP always goes to primary number (customer_number), not secondary
            if is_email:
                self.send_email(identifier, otp)
            else:
                send_sms(identifier, otp)

            return str(otp)

    def validate_otp(self, identifier: str, otp: str, is_email: bool = False) -> bool:
        with Session(self.engine) as session:
            statement = select(OTP).where(
                OTP.email == identifier if is_email else OTP.phone_number == identifier,
                OTP.otp == otp,
                OTP.expires_at > datetime.utcnow()
            )
            db_otp = session.exec(statement).first()
            
            if db_otp:
                # session.delete(db_otp)
                # session.commit()
                return True
            return False

    def delete_otp(self, identifier: str, is_email: bool = False):
        with Session(self.engine) as session:
            statement = select(OTP).where(
                OTP.email == identifier if is_email else OTP.phone_number == identifier
            )
            db_otp = session.exec(statement).first()
            if db_otp:
                session.delete(db_otp)
                session.commit()

    def get_user_by_phone(self, phone_number: str) -> Optional[ClientUser]:
        """
        Get user by primary phone number (customer_number only).
        OTP functionality uses only the primary contact number.
        """
        with Session(self.engine) as session:
            statement = select(ClientUser).where(ClientUser.customer_number == phone_number)
            return session.exec(statement).first()

    def get_user_by_email(self, email: str) -> Optional[ClientUser]:
        with Session(self.engine) as session:
            statement = select(ClientUser).where(ClientUser.email == email)
            return session.exec(statement).first()

    def get_user_by_any_phone(self, phone_number: str) -> Optional[ClientUser]:
        """
        Get user by either primary or secondary phone number.
        This can be used for general lookups but not for OTP functionality.
        """
        with Session(self.engine) as session:
            statement = select(ClientUser).where(
                or_(
                    ClientUser.customer_number == phone_number,
                    ClientUser.professional_contact_number == phone_number
                )
            )
            return session.exec(statement).first()

    def get_expired_trials(self) -> List[ClientUser]:
        """
        Get all users with expired trial subscriptions.
        """
        with Session(self.engine) as session:
            current_time = datetime.utcnow()
            statement = select(ClientUser).where(
                ClientUser.subscription == SubscriptionType.BASIC,
                ClientUser.subscription_end_date < current_time,
                ClientUser.is_subscription_active == True
            )
            return session.exec(statement).all()

    def deactivate_expired_trials(self) -> int:
        """
        Deactivate all expired trial subscriptions.
        Returns count of deactivated users.
        """
        expired_users = self.get_expired_trials()
        count = 0
        
        with Session(self.engine) as session:
            for user in expired_users:
                user.is_subscription_active = False
                user.updated_at = datetime.utcnow()
                session.add(user)
                count += 1
            
            session.commit()
        
        return count
    
    def send_password_reset_otp(self, email: str) -> str:
        """
        Send OTP for password reset to user's email.
        Returns the OTP if successful, raises exception if user not found or email fails.
        """
        # Check if user exists with this email
        user = self.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="No user found with this email address"
            )
        
        # Delete any existing OTP for this email
        self.delete_otp(email, is_email=True)
        
        try:
            # Generate and store new OTP
            otp = self.store_otp(email, is_email=True)
            return str(otp)
        except Exception as e:
            print(f"❌ Failed to send password reset OTP: {e}")
            raise Exception(f"Failed to send password reset email: {e}")

    def verify_password_reset_otp(self, email: str, otp: str) -> bool:
        """
        Verify OTP for password reset.
        Returns True if OTP is valid and not expired.
        """
        return self.validate_otp(email, otp, is_email=True)

    def update_user_password(self, email: str, new_password: str) -> bool:
        """
        Update user's password after successful OTP verification.
        Returns True if password updated successfully.
        """
        with Session(self.engine) as session:
            # Get user by email
            statement = select(ClientUser).where(ClientUser.email == email)
            user = session.exec(statement).first()
            
            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
            
            try:
                # Update password and timestamp
                user.password = new_password
                user.updated_at = datetime.utcnow()
                
                session.add(user)
                session.commit()
                session.refresh(user)
                
                print(f"✅ Password updated successfully for user: {email}")
                return True
                
            except Exception as e:
                session.rollback()
                print(f"❌ Failed to update password for user {email}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update password: {e}"
                )

    def reset_password_complete(self, email: str, otp: str, new_password: str) -> dict:
        """
        Complete password reset process: verify OTP and update password.
        Returns user info if successful.
        """
        # Verify OTP first
        if not self.verify_password_reset_otp(email, otp):
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OTP"
            )
        
        # Update password
        success = self.update_user_password(email, new_password)
        
        if success:
            # Delete the OTP after successful password reset
            self.delete_otp(email, is_email=True)
            
            # Get updated user info
            user = self.get_user_by_email(email)
            
            return {
                "message": "Password reset successful",
                "user_id": user.id,
                "email": user.email,
                "user_name": user.name
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to reset password"
            )
            

    
