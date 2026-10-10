import os
import logging
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("health-service")


def check_airflow() -> dict:
    """
    Checks Airflow health live by querying the /api/v2/dags endpoint.
    Supports JWT Bearer Token (Airflow 3 /auth/token) and HTTP Basic Auth.
    Returns real-time status and per-DAG active/paused breakdown.
    """
    configured_url = os.getenv("GET_AIRFLOW_API_URL", "")
    host_ip = os.getenv("GET_HOST_URL", "52.55.42.117")

    cred_candidates = []
    env_user = os.getenv("AIRFLOW_USERNAME")
    env_pass = os.getenv("AIRFLOW_PASSWORD")
    if env_user and env_pass:
        cred_candidates.append((env_user, env_pass))
    cred_candidates.append(("preventual", "preventual@121"))
    cred_candidates.append(("airflow", "airflow"))

    candidate_bases = []
    if configured_url:
        candidate_bases.append(configured_url.rstrip("/"))

    if host_ip:
        candidate_bases.append(f"http://{host_ip}:8080")
        candidate_bases.append(f"http://{host_ip}:8081")

    candidate_bases.extend([
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://host.docker.internal:8080",
    ])

    last_error = None
    for base in candidate_bases:
        for user, pwd in cred_candidates:
            token = _get_jwt_token(base, user, pwd)
            headers = {"Accept": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            endpoints = [
                f"{base}/api/v2/dags",
                f"{base}/dags",
                f"{base}/api/v1/dags",
            ]
            for endpoint in endpoints:
                try:
                    auth = None if token else HTTPBasicAuth(user, pwd)
                    response = requests.get(
                        endpoint,
                        headers=headers,
                        auth=auth,
                        timeout=5,
                    )
                    content_type = response.headers.get("content-type", "").lower()
                    if response.status_code == 200 and ("json" in content_type or response.text.strip().startswith("{")):
                        data = response.json()
                        if isinstance(data, dict) and "dags" in data:
                            return _build_airflow_result(dags=data["dags"], reachable=True, url=endpoint)
                    else:
                        last_error = f"Endpoint {endpoint} returned status {response.status_code}"
                except Exception as e:
                    last_error = e
                    continue

    logger.warning(f"Airflow health check failed across candidates: {last_error}")
    return {
        "status": "unhealthy",
        "message": f"Cannot connect to Airflow: {last_error}",
        "reachable": False,
        "dags": [],
    }


def _get_jwt_token(base_url: str, username: str, password: str) -> str:
    if not username or not password:
        return ""
    try:
        url = f"{base_url}/auth/token"
        res = requests.post(
            url,
            json={"username": username, "password": password},
            timeout=3,
        )
        if res.status_code in {200, 201}:
            return res.json().get("access_token", "")
    except Exception:
        pass
    return ""


def _build_airflow_result(dags: list, reachable: bool, url: str) -> dict:
    dag_statuses = []
    active_count = 0
    paused_count = 0
    error_count = 0

    for dag in dags:
        is_paused = dag.get("is_paused", True)
        is_stale = dag.get("is_stale", False)
        has_errors = dag.get("has_import_errors", False)

        if has_errors:
            dag_status = "error"
            error_count += 1
        elif is_paused:
            dag_status = "paused"
            paused_count += 1
        elif is_stale:
            dag_status = "stale"
            paused_count += 1
        else:
            dag_status = "active"
            active_count += 1

        dag_statuses.append({
            "dag_id": dag.get("dag_id"),
            "display_name": dag.get("dag_display_name", dag.get("dag_id")),
            "status": dag_status,
            "is_paused": is_paused,
            "is_stale": is_stale,
            "has_import_errors": has_errors,
            "description": dag.get("description"),
            "tags": [t.get("name") if isinstance(t, dict) else str(t) for t in dag.get("tags", [])],
        })

    total = len(dags)
    if not reachable or total == 0:
        overall = "unhealthy"
    elif error_count > 0:
        overall = "unhealthy"
    else:
        overall = "healthy"  # paused/idle DAGs are intentional, not a failure

    return {
        "status": overall,
        "reachable": reachable,
        "endpoint": url,
        "total_dags": total,
        "active_dags": active_count,
        "paused_dags": paused_count,
        "error_dags": error_count,
        "dags": dag_statuses,
    }
