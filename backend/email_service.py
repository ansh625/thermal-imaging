import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "CSIO ThermalStream")
        
        # Log SMTP configuration (without password)
        logger.info(f"Email Service initialized with:")
        logger.info(f"  SMTP Host: {self.smtp_host}")
        logger.info(f"  SMTP Port: {self.smtp_port}")
        logger.info(f"  From Email: {self.from_email}")
        logger.info(f"  From Name: {self.from_name}")
        
        # Validate configuration
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP_USER or SMTP_PASSWORD not configured - Email sending will fail")
    
    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send HTML email with detailed error handling"""
        if not self.smtp_user or not self.smtp_password:
            logger.error("SMTP credentials not configured. Cannot send email.")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            logger.debug(f"Connecting to {self.smtp_host}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                logger.debug("Starting TLS...")
                server.starttls()
                
                logger.debug(f"Logging in as {self.smtp_user}")
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                
                logger.debug(f"Sending message to {to_email}")
                server.send_message(msg)
            
            logger.info(f"✓ Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"✗ SMTP Authentication failed: {e}")
            logger.error("Check SMTP_USER and SMTP_PASSWORD in .env file")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"✗ SMTP Error: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Error sending email: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            return False
    
    def send_password_reset_email(self, to_email: str, reset_token: str, 
                                  base_url: str = "http://localhost:5173") -> bool:
        """Send password reset email"""
        logger.info(f"Preparing password reset email for {to_email}")
        reset_link = f"{base_url}/reset-password?token={reset_token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1a90ff 0%, #0066cc 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #1a90ff; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>CSIO ThermalStream</h1>
                    <p>Password Reset Request</p>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #1a90ff;">{reset_link}</p>
                    <p><strong>This link will expire in 1 hour.</strong></p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>© 2025 CSIR CSIO ThermalStream. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, "Password Reset Request - CSIO ThermalStream", html_content)

email_service = EmailService()
