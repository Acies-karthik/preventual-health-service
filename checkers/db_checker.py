import os
import logging
import psycopg2

logger = logging.getLogger("health-service")


def check_services_db() -> dict:
    """Checks live connectivity to preventual_dev_services."""
    db_name = os.getenv("DB_NAME", "preventual_dev_services")
    return _check_single_db(db_name)


def check_auth_db() -> dict:
    """Checks live connectivity to preventual_dev_auth."""
    db_name = os.getenv("AUTH_DB_NAME", "preventual_dev_auth")
    return _check_single_db(db_name)


def _check_single_db(db_name: str) -> dict:
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USERNAME", "preventual_dev_developers")
    password = os.getenv("DB_PASSWORD", "Preventual!Orbit81@DV")
    port = int(os.getenv("DB_PORT", 5432))

    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=user,
            password=password,
            host=host,
            port=port,
            sslmode="require",
            connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
        conn.close()

        if result and result[0] == 1:
            return {
                "status": "healthy",
                "database": db_name,
                "host": host,
                "message": "Connection successful",
            }
        else:
            return {
                "status": "unhealthy",
                "database": db_name,
                "host": host,
                "message": "Health query returned unexpected result",
            }
    except Exception as e:
        logger.error(f"DB {db_name} health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": db_name,
            "host": host,
            "message": str(e),
        }
