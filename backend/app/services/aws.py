"""
AWS Services Management for PM Document Intelligence.

This module handles AWS service initialization, health checks, and client management
for Bedrock, Textract, Comprehend, and S3.

Features:
- Lazy client initialization
- Service health checks
- Connection pooling
- Error handling and retries

Usage:
    from app.services.aws import get_bedrock_client, get_s3_client

    # Get Bedrock client
    bedrock = await get_bedrock_client()

    # Use for inference
    response = await bedrock.invoke_model(...)
"""

from typing import Any, Dict, Optional

import aioboto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.utils.exceptions import BedrockError, S3Error, TextractError, ComprehendError
from app.utils.logger import get_logger


logger = get_logger(__name__)


# Global session for AWS clients
_session: Optional[aioboto3.Session] = None


def get_aws_session() -> aioboto3.Session:
    """
    Get or create AWS session.

    Returns:
        aioboto3 Session instance
    """
    global _session

    if _session is None:
        credentials = settings.get_aws_credentials()

        _session = aioboto3.Session(
            aws_access_key_id=credentials.get("aws_access_key_id"),
            aws_secret_access_key=credentials.get("aws_secret_access_key"),
            aws_session_token=credentials.get("aws_session_token"),
            region_name=credentials.get("region_name"),
        )

        logger.info(f"AWS session created for region {credentials.get('region_name')}")

    return _session


def get_boto_config(service_name: str) -> Config:
    """
    Get boto3 configuration for a service.

    Args:
        service_name: AWS service name

    Returns:
        Boto3 Config object
    """
    return Config(
        region_name=settings.aws.aws_region,
        connect_timeout=30,
        read_timeout=settings.aws.aws_request_timeout,
        retries={
            "max_attempts": 3,
            "mode": "adaptive",
        },
        max_pool_connections=settings.aws.aws_max_concurrent_requests,
    )


async def get_bedrock_client():
    """
    Get AWS Bedrock Runtime client.

    Returns:
        Bedrock Runtime client

    Raises:
        BedrockError: If client creation fails
    """
    try:
        session = get_aws_session()
        config = get_boto_config("bedrock-runtime")

        async with session.client(
            "bedrock-runtime",
            region_name=settings.bedrock.bedrock_region,
            config=config,
        ) as client:
            return client

    except Exception as e:
        logger.error(f"Failed to create Bedrock client: {e}", exc_info=True)
        raise BedrockError(
            message="Failed to initialize Bedrock client",
            details={"error": str(e)},
        )


async def get_textract_client():
    """
    Get AWS Textract client.

    Returns:
        Textract client

    Raises:
        TextractError: If client creation fails
    """
    try:
        session = get_aws_session()
        config = get_boto_config("textract")

        async with session.client("textract", config=config) as client:
            return client

    except Exception as e:
        logger.error(f"Failed to create Textract client: {e}", exc_info=True)
        raise TextractError(
            message="Failed to initialize Textract client",
            details={"error": str(e)},
        )


async def get_comprehend_client():
    """
    Get AWS Comprehend client.

    Returns:
        Comprehend client

    Raises:
        ComprehendError: If client creation fails
    """
    try:
        session = get_aws_session()
        config = get_boto_config("comprehend")

        async with session.client("comprehend", config=config) as client:
            return client

    except Exception as e:
        logger.error(f"Failed to create Comprehend client: {e}", exc_info=True)
        raise ComprehendError(
            message="Failed to initialize Comprehend client",
            details={"error": str(e)},
        )


async def get_s3_client():
    """
    Get AWS S3 client.

    Returns:
        S3 client

    Raises:
        S3Error: If client creation fails
    """
    try:
        session = get_aws_session()
        config = get_boto_config("s3")

        async with session.client("s3", config=config) as client:
            return client

    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}", exc_info=True)
        raise S3Error(
            message="Failed to initialize S3 client",
            details={"error": str(e)},
        )


async def test_bedrock_availability() -> bool:
    """
    Test Bedrock service availability.

    Returns:
        True if available, False otherwise
    """
    if settings.is_testing or settings.mock_aws_services:
        return True

    try:
        session = get_aws_session()
        config = get_boto_config("bedrock")

        async with session.client(
            "bedrock",
            region_name=settings.bedrock.bedrock_region,
            config=config,
        ) as client:
            # List foundation models to test access
            response = await client.list_foundation_models()
            logger.debug(
                f"Bedrock available with {len(response.get('modelSummaries', []))} models"
            )
            return True

    except Exception as e:
        logger.warning(f"Bedrock availability check failed: {e}")
        return False


async def test_s3_availability() -> bool:
    """
    Test S3 service availability.

    Returns:
        True if available, False otherwise
    """
    if settings.is_testing or settings.mock_aws_services:
        return True

    try:
        session = get_aws_session()
        config = get_boto_config("s3")

        async with session.client("s3", config=config) as client:
            # Try to head the bucket
            await client.head_bucket(Bucket=settings.aws.s3_bucket_name)
            logger.debug(f"S3 bucket '{settings.aws.s3_bucket_name}' accessible")
            return True

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            logger.warning(f"S3 bucket '{settings.aws.s3_bucket_name}' not found")
        elif error_code == "403":
            logger.warning(
                f"Access denied to S3 bucket '{settings.aws.s3_bucket_name}'"
            )
        else:
            logger.warning(f"S3 availability check failed: {e}")
        return False

    except Exception as e:
        logger.warning(f"S3 availability check failed: {e}")
        return False


async def test_textract_availability() -> bool:
    """
    Test Textract service availability.

    Returns:
        True if available, False otherwise
    """
    if not settings.textract.textract_enabled:
        return False

    if settings.is_testing or settings.mock_aws_services:
        return True

    try:
        session = get_aws_session()
        config = get_boto_config("textract")

        async with session.client("textract", config=config) as client:
            # Simple API call to test access (list adapter versions is a lightweight call)
            # Note: This might fail with access denied if permissions are limited
            # but that's okay for basic availability check
            await client.get_document_analysis(JobId="test")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        # InvalidJobIdException means service is available but job doesn't exist (expected)
        if error_code == "InvalidJobIdException":
            logger.debug("Textract service available")
            return True
        else:
            logger.warning(f"Textract availability check failed: {error_code}")
            return False

    except Exception as e:
        logger.warning(f"Textract availability check failed: {e}")
        return False


async def test_comprehend_availability() -> bool:
    """
    Test Comprehend service availability.

    Returns:
        True if available, False otherwise
    """
    if not settings.comprehend.comprehend_enabled:
        return False

    if settings.is_testing or settings.mock_aws_services:
        return True

    try:
        session = get_aws_session()
        config = get_boto_config("comprehend")

        async with session.client("comprehend", config=config) as client:
            # Try to detect sentiment on a simple text
            response = await client.detect_sentiment(
                Text="test",
                LanguageCode=settings.comprehend.comprehend_language_code,
            )
            logger.debug("Comprehend service available")
            return True

    except Exception as e:
        logger.warning(f"Comprehend availability check failed: {e}")
        return False


async def test_aws_services() -> Dict[str, Any]:
    """
    Test availability of all AWS services.

    Returns:
        Dictionary with service availability status
    """
    results = {
        "bedrock": False,
        "s3": False,
        "textract": False,
        "comprehend": False,
        "all_available": False,
    }

    # Test each service
    results["bedrock"] = await test_bedrock_availability()
    results["s3"] = await test_s3_availability()
    results["textract"] = await test_textract_availability()
    results["comprehend"] = await test_comprehend_availability()

    # Check if all enabled services are available
    enabled_services = []
    if settings.textract.textract_enabled:
        enabled_services.append("textract")
    if settings.comprehend.comprehend_enabled:
        enabled_services.append("comprehend")

    # Core services that should always be available
    core_services = ["bedrock", "s3"]

    all_available = all(
        results.get(service, False) for service in core_services + enabled_services
    )

    results["all_available"] = all_available

    logger.info(f"AWS services status: {results}")

    return results
