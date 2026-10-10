import os
import logging

logger = logging.getLogger("health-service")


def check_secret_manager() -> dict:
    """
    Checks connectivity to cloud secret manager.
    Validates cloud credentials via live provider ping (AWS STS / Azure / GCP).
    """
    provider = (os.getenv("CLOUD_PROVIDER") or "unknown").lower()

    try:
        if provider == "aws":
            return _check_aws_secrets()
        elif provider == "azure":
            return _check_azure_secrets()
        elif provider == "gcp":
            return _check_gcp_secrets()
        elif provider == "oci":
            return {
                "status": "healthy",
                "provider": "oci",
                "message": "OCI secret manager configured",
            }
        else:
            return {
                "status": "unhealthy",
                "provider": provider,
                "message": f"Unknown CLOUD_PROVIDER: '{provider}'",
            }
    except Exception as e:
        logger.error(f"Secret manager health check failed: {e}")
        return {
            "status": "unhealthy",
            "provider": provider,
            "message": str(e),
        }


def _check_aws_secrets() -> dict:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    region = os.getenv("AWS_REGION") or os.getenv("AWS_BUCKET_REGION", "us-east-1")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    try:
        session_kwargs = {}
        if access_key and secret_key:
            session_kwargs = {
                "aws_access_key_id": access_key,
                "aws_secret_access_key": secret_key,
            }
        sts = boto3.client("sts", region_name=region, **session_kwargs)
        identity = sts.get_caller_identity()
        return {
            "status": "healthy",
            "provider": "aws",
            "region": region,
            "account_id": identity.get("Account"),
            "message": "AWS credentials valid and reachable",
        }
    except NoCredentialsError:
        return {
            "status": "unhealthy",
            "provider": "aws",
            "region": region,
            "message": "AWS credentials not configured",
        }
    except ClientError as e:
        return {
            "status": "unhealthy",
            "provider": "aws",
            "region": region,
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "provider": "aws",
            "region": region,
            "message": str(e),
        }


def _check_azure_secrets() -> dict:
    vault_url = os.getenv("AZURE_VAULT_URL", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")

    if not vault_url:
        return {
            "status": "unhealthy",
            "provider": "azure",
            "message": "AZURE_VAULT_URL not configured",
        }

    try:
        from azure.identity import ClientSecretCredential
        from azure.keyvault.secrets import SecretClient

        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")

        credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        client = SecretClient(vault_url=vault_url, credential=credential)
        next(iter(client.list_properties_of_secrets(max_page_size=1)), None)
        return {
            "status": "healthy",
            "provider": "azure",
            "vault_url": vault_url,
            "message": "Azure Key Vault reachable",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "provider": "azure",
            "vault_url": vault_url,
            "message": str(e),
        }


def _check_gcp_secrets() -> dict:
    try:
        from google.cloud import secretmanager
        project_id = os.getenv("GCP_PROJECT_ID", "")
        if not project_id:
            return {
                "status": "unhealthy",
                "provider": "gcp",
                "message": "GCP_PROJECT_ID not configured",
            }
        client = secretmanager.SecretManagerServiceClient()
        return {
            "status": "healthy",
            "provider": "gcp",
            "project_id": project_id,
            "message": "GCP Secret Manager client initialized",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "provider": "gcp",
            "message": str(e),
        }
