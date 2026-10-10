# Preventual Health Service

Dedicated microservice for monitoring the live status of all Preventual internal background services:
- **Airflow 3:** Live DAGs active/paused tracking via REST API (`/api/v2/dags`)
- **Spark Cluster:** Master node & worker health via Spark JSON API (`/json/`)
- **Services Database:** Live PostgreSQL check on `preventual_dev_services`
- **Auth Database:** Live PostgreSQL check on `preventual_dev_auth`
- **Secret Manager:** Secrets Vault / Key Management Service connectivity
- **SMTP Email:** SMTP server handshake and authentication

---

## 🚀 Quick Start

### 1. Run with Python
```bash
cd /home/karthik/preventual-health-service
pip install -r requirements.txt
python3 main.py
```
Default port is `6190`.

### 2. Run with Docker
```bash
docker build -t preventual-health-service .
docker run -d -p 6190:6190 --name preventual-health preventual-health-service
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /health/services` | JSON | Aggregated live health status across all 6 services |
| `GET /health/services/{service}` | JSON | Live check for a single service (`airflow`, `spark`, `services_db`, `auth_db`, `secret_manager`, `smtp`) |
| `GET /dashboard` | HTML | Auto-refreshing visual dashboard with green/red status boxes |
| `GET /health` | JSON | Liveness ping |
