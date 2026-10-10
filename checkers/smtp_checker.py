import os
import ssl
import smtplib
import logging

logger = logging.getLogger("health-service")


def check_smtp() -> dict:
    """
    Checks SMTP connectivity live by performing a handshake (connect + EHLO + STARTTLS + login)
    WITHOUT sending any actual email.
    """
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_host:
        return {
            "status": "unhealthy",
            "host": smtp_host,
            "port": smtp_port,
            "message": "SMTP_HOST not configured",
        }

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            if smtp_user and smtp_password:
                smtp.login(smtp_user, smtp_password)
        return {
            "status": "healthy",
            "host": smtp_host,
            "port": smtp_port,
            "message": "SMTP handshake and login successful",
        }
    except smtplib.SMTPAuthenticationError as e:
        logger.warning(f"SMTP health check - auth failed: {e}")
        return {
            "status": "unhealthy",
            "host": smtp_host,
            "port": smtp_port,
            "message": "SMTP server reachable but authentication failed",
        }
    except ConnectionRefusedError:
        return {
            "status": "unhealthy",
            "host": smtp_host,
            "port": smtp_port,
            "message": "Connection refused - SMTP server not reachable",
        }
    except TimeoutError:
        return {
            "status": "unhealthy",
            "host": smtp_host,
            "port": smtp_port,
            "message": "SMTP connection timed out",
        }
    except Exception as e:
        logger.error(f"SMTP health check failed: {e}")
        return {
            "status": "unhealthy",
            "host": smtp_host,
            "port": smtp_port,
            "message": str(e),
        }
