"""Email service for sending emails via SMTP."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


def build_email_template(
    greeting: str,
    message: str,
    button_text: str,
    button_link: str,
    note: str,
) -> str:
    """Build professional HTML email template."""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>UrbanNest</title>
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;">
            <!-- Header -->
            <div style="background-color: #1e3a2f; padding: 30px 20px; text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 600;">UrbanNest</h1>
                <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">Society OS</p>
            </div>

            <!-- Content -->
            <div style="padding: 40px 30px;">
                <h2 style="color: #1e3a2f; margin: 0 0 20px 0; font-size: 22px;">{greeting}</h2>
                
                <p style="margin: 0 0 20px 0; color: #555; font-size: 16px; line-height: 1.8;">{message}</p>

                <!-- Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{button_link}" style="display: inline-block; background-color: #1e3a2f; color: white; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 500; font-size: 16px;">
                        {button_text}
                    </a>
                </div>

                <!-- Note -->
                <p style="margin: 30px 0 0 0; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #1e3a2f; color: #666; font-size: 14px;">
                    {note}
                </p>
            </div>

            <!-- Footer -->
            <div style="background-color: #f5f5f5; padding: 20px 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                <p style="margin: 0; color: #888; font-size: 12px;">
                    © 2024 UrbanNest Society OS. All rights reserved.
                </p>
            </div>
        </div>
    </body>
    </html>
    """


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send email via SMTP.
    
    Returns True if successful, False otherwise.
    Email failures do NOT raise exceptions.
    """
    try:
        logger.info(f"[EMAIL] Starting email send to: {to_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        
        # Validate configuration
        if not settings.SMTP_HOST:
            logger.error("[EMAIL] SMTP_HOST not configured")
            return False
        if not settings.SMTP_USER:
            logger.error("[EMAIL] SMTP_USER not configured")
            return False
        if not settings.SMTP_PASSWORD:
            logger.error("[EMAIL] SMTP_PASSWORD not configured")
            return False
        if not settings.SMTP_FROM:
            logger.error("[EMAIL] SMTP_FROM not configured")
            return False

        logger.info(f"[EMAIL] SMTP config: HOST={settings.SMTP_HOST}, PORT={settings.SMTP_PORT}, USER={settings.SMTP_USER}, USE_TLS={settings.SMTP_USE_TLS}")

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email

        # Attach HTML content
        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)
        logger.info(f"[EMAIL] Message created with HTML content")

        # Send email
        logger.info(f"[EMAIL] Attempting to connect to SMTP server {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            logger.info(f"[EMAIL] Connected to SMTP server successfully")
            
            if settings.SMTP_USE_TLS:
                logger.info(f"[EMAIL] Starting TLS encryption")
                server.starttls()
                logger.info(f"[EMAIL] TLS encryption established")
            
            logger.info(f"[EMAIL] Authenticating with user: {settings.SMTP_USER}")
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            logger.info(f"[EMAIL] Authentication successful")
            
            logger.info(f"[EMAIL] Sending email from {settings.SMTP_FROM} to {to_email}")
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
            logger.info(f"[EMAIL] Email sent successfully")
        
        logger.info(f"[EMAIL] Email successfully sent to {to_email} with subject: {subject}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"[EMAIL] SMTP Authentication failed: {str(e)} | User: {settings.SMTP_USER}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"[EMAIL] SMTP error ({type(e).__name__}): {str(e)}")
        return False
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send email to {to_email}: {type(e).__name__}: {str(e)}", exc_info=True)
        return False


def send_admin_invite(
    to_email: str,
    to_name: str,
    building_name: str,
    setup_link: str,
) -> bool:
    """Send admin invitation email."""
    logger.info(f"[ADMIN_INVITE] Starting admin invite email for {to_name} ({to_email}) at {building_name}")
    
    html = build_email_template(
        greeting=f"Hello {to_name},",
        message=f"You have been invited to manage <strong>{building_name}</strong> on UrbanNest as an Admin.",
        button_text="Set Up Your Account",
        button_link=setup_link,
        note="This link expires in 48 hours.",
    )
    
    result = send_email(
        to_email=to_email,
        subject="You have been invited as Admin on UrbanNest",
        html_content=html,
    )
    
    if result:
        logger.info(f"[ADMIN_INVITE] Admin invite sent to {to_email}")
    else:
        logger.error(f"[ADMIN_INVITE] Failed to send admin invite to {to_email}")
    
    return result


def send_resident_invite(
    to_email: str,
    to_name: str,
    building_name: str,
    unit_number: str,
    setup_link: str,
) -> bool:
    """Send resident invitation email."""
    logger.info(f"[RESIDENT_INVITE] Starting resident invite email for {to_name} ({to_email}) at {building_name} {unit_number}")
    
    html = build_email_template(
        greeting=f"Hello {to_name},",
        message=f"You have been added as a resident of <strong>{unit_number}</strong>, <strong>{building_name}</strong> on UrbanNest.",
        button_text="Set Up Your Account",
        button_link=setup_link,
        note="This link expires in 48 hours.",
    )
    
    result = send_email(
        to_email=to_email,
        subject="Welcome to UrbanNest — Set up your account",
        html_content=html,
    )
    
    if result:
        logger.info(f"[RESIDENT_INVITE] Resident invite sent to {to_email}")
    else:
        logger.error(f"[RESIDENT_INVITE] Failed to send resident invite to {to_email}")
    
    return result


def send_security_invite(
    to_email: str,
    to_name: str,
    building_name: str,
    shift: str,
    setup_link: str,
) -> bool:
    """Send security guard invitation email."""
    logger.info(f"[SECURITY_INVITE] Starting security invite email for {to_name} ({to_email}) at {building_name} Shift: {shift}")
    
    html = build_email_template(
        greeting=f"Hello {to_name},",
        message=f"You have been added as a Security Guard at <strong>{building_name}</strong> on UrbanNest.",
        button_text="Set Up Your Account",
        button_link=setup_link,
        note="This link expires in 48 hours.",
    )
    
    result = send_email(
        to_email=to_email,
        subject="You have been added as Security Guard on UrbanNest",
        html_content=html,
    )
    
    if result:
        logger.info(f"[SECURITY_INVITE]  Security invite sent to {to_email}")
    else:
        logger.error(f"[SECURITY_INVITE]  Failed to send security invite to {to_email}")
    
    return result


def send_password_reset(
    to_email: str,
    to_name: str,
    reset_link: str,
) -> bool:
    """Send password reset email."""
    logger.info(f"[PASSWORD_RESET] Starting password reset email for {to_name} ({to_email})")
    
    html = build_email_template(
        greeting=f"Hello {to_name},",
        message="We received a request to reset your password.",
        button_text="Reset Password",
        button_link=reset_link,
        note="This link expires in 1 hour. If you did not request this, please ignore this email.",
    )
    
    result = send_email(
        to_email=to_email,
        subject="Reset your UrbanNest password",
        html_content=html,
    )
    
    if result:
        logger.info(f"[PASSWORD_RESET] Password reset email sent to {to_email}")
    else:
        logger.error(f"[PASSWORD_RESET] Failed to send password reset email to {to_email}")
    
    return result
