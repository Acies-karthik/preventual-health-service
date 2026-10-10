import os
import logging
import requests

logger = logging.getLogger("health-service")


def check_spark() -> dict:
    """
    Checks Spark health live by querying the Spark Master JSON endpoint.
    GET http://<spark-master>:<port>/json/
    Workers status is inferred directly from the master response.
    """
    configured_ui_url = os.getenv("SPARK_MASTER_UI_URL", "")
    spark_master = os.getenv("SPARK_MASTER", "")
    host_ip = os.getenv("GET_HOST_URL", "52.55.42.117")

    candidate_bases = []
    if configured_ui_url:
        candidate_bases.append(configured_ui_url.rstrip("/"))

    if host_ip:
        candidate_bases.append(f"http://{host_ip}:8081")
        candidate_bases.append(f"http://{host_ip}:8080")

    if spark_master:
        host = spark_master.replace("spark://", "").split(":")[0]
        candidate_bases.append(f"http://{host}:8081")
        candidate_bases.append(f"http://{host}:8080")

    candidate_bases.extend([
        "http://spark-master-dev:8081",
        "http://spark-master-dev:8080",
        "http://localhost:8081",
        "http://localhost:8080",
    ])

    last_error = None
    for base in candidate_bases:
        try:
            url = f"{base}/json/"
            response = requests.get(url, timeout=5)
            content_type = response.headers.get("content-type", "").lower()
            if response.status_code == 200 and ("json" in content_type or response.text.strip().startswith("{")):
                data = response.json()
                workers_raw = data.get("workers", [])
                workers = []
                alive_count = 0

                for w in workers_raw:
                    state = w.get("state", "UNKNOWN")
                    if state == "ALIVE":
                        alive_count += 1
                    workers.append({
                        "id": w.get("id"),
                        "host": w.get("host"),
                        "state": state,
                        "cores": w.get("cores", 0),
                        "memory_mb": w.get("memory", 0),
                    })

                total = len(workers)
                master_status = data.get("status", "UNKNOWN")

                if master_status != "ALIVE" or (total > 0 and alive_count == 0):
                    overall = "unhealthy"
                elif alive_count < total:
                    overall = "unhealthy"
                else:
                    overall = "healthy"

                return {
                    "status": overall,
                    "reachable": True,
                    "master_url": base,
                    "master_status": master_status,
                    "alive_workers": alive_count,
                    "total_workers": total,
                    "workers": workers,
                }
            else:
                last_error = f"Endpoint {url} returned status {response.status_code} ({content_type})"
        except Exception as e:
            last_error = e
            continue

    logger.warning(f"Spark health check failed across candidates: {last_error}")
    return {
        "status": "unhealthy",
        "message": f"Cannot connect to Spark Master: {last_error}",
        "reachable": False,
        "master_url": candidate_bases[0] if candidate_bases else "",
        "workers": [],
    }
