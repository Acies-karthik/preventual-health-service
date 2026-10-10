import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from checkers.airflow_checker import check_airflow
from checkers.spark_checker import check_spark
from checkers.db_checker import check_services_db, check_auth_db
from checkers.secret_checker import check_secret_manager
from checkers.smtp_checker import check_smtp

app = FastAPI(title="Preventual Health Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
@app.get("/dashboard")
@app.get("/status")
async def dashboard():
    """Serves the Preventual UI Dashboard."""
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def ping():
    return {"status": "healthy"}


@app.get("/health/services")
async def services_health_check():
    """Live health check across all 6 background services."""
    loop = asyncio.get_event_loop()
    (
        airflow_res,
        spark_res,
        services_db_res,
        auth_db_res,
        secret_res,
        smtp_res,
    ) = await asyncio.gather(
        loop.run_in_executor(None, check_airflow),
        loop.run_in_executor(None, check_spark),
        loop.run_in_executor(None, check_services_db),
        loop.run_in_executor(None, check_auth_db),
        loop.run_in_executor(None, check_secret_manager),
        loop.run_in_executor(None, check_smtp),
    )

    services = {
        "airflow": airflow_res,
        "spark": spark_res,
        "database_services": services_db_res,
        "database_auth": auth_db_res,
        "secret_manager": secret_res,
        "smtp": smtp_res,
    }

    statuses = [v.get("status", "unhealthy") for v in services.values()]
    overall = "healthy" if all(s == "healthy" for s in statuses) else "unhealthy"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("HEALTH_SERVICE_PORT", "6190"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
