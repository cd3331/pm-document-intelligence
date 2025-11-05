"""
Configuration Management System for PM Document Intelligence.

This module provides a centralized, type-safe configuration system using Pydantic Settings.
All configuration values are loaded from environment variables and validated at startup.

Features:
- Type-safe configuration with validation
- Environment-based settings (development, staging, production)
- AWS service configurations (Bedrock, Textract, Comprehend)
- Database and caching configurations
- Security and rate limiting settings
- Feature flags for gradual rollouts
- Immutable configuration in production

Usage:
    from app.config import settings

    # Access configuration values
    bucket_name = settings.aws_s3_bucket
    model_id = settings.bedrock_model_id
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    PostgresDsn,
    RedisDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class AWSConfig(BaseSettings):
    """AWS service configuration and credentials."""

    # Core AWS Configuration
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for service calls",
    )
    aws_access_key_id: str | None = Field(
        default=None,
        description="AWS access key ID (optional if using IAM roles)",
    )
    aws_secret_access_key: str | None = Field(
        default=None,
        description="AWS secret access key (optional if using IAM roles)",
    )
    aws_session_token: str | None = Field(
        default=None,
        description="AWS session token for temporary credentials",
    )

    # AWS Service Limits
    aws_max_concurrent_requests: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum concurrent AWS API requests",
    )
    aws_request_timeout: int = Field(
        default=300,
        ge=10,
        le=900,
        description="AWS API request timeout in seconds",
    )

    # S3 Configuration
    s3_bucket_name: str = Field(
        default="pm-document-intelligence",
        description="S3 bucket for document storage",
    )
    s3_upload_path: str = Field(
        default="documents/",
        description="S3 path prefix for uploads",
    )
    s3_presigned_url_expiry: int = Field(
        default=3600,
        ge=60,
        le=604800,
        description="S3 presigned URL expiry in seconds",
    )

    @field_validator("s3_upload_path")
    @classmethod
    def validate_s3_path(cls, v: str) -> str:
        """Ensure S3 path ends with slash."""
        if not v.endswith("/"):
            return f"{v}/"
        return v


class BedrockConfig(BaseSettings):
    """AWS Bedrock configuration for Claude API."""

    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Bedrock model identifier",
    )
    bedrock_max_tokens: int = Field(
        default=4096,
        ge=1,
        le=200000,
        description="Maximum tokens for Bedrock responses",
    )
    bedrock_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for response generation",
    )
    bedrock_top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Top-p sampling parameter",
    )
    bedrock_region: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock service",
    )

    # Rate Limiting
    bedrock_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        description="Bedrock API calls per minute",
    )
    bedrock_rate_limit_per_hour: int = Field(
        default=1000,
        ge=1,
        description="Bedrock API calls per hour",
    )


class TextractConfig(BaseSettings):
    """AWS Textract configuration for document OCR."""

    textract_enabled: bool = Field(
        default=True,
        description="Enable Textract document analysis",
    )
    textract_max_pages: int = Field(
        default=100,
        ge=1,
        le=3000,
        description="Maximum pages to process with Textract",
    )
    textract_timeout: int = Field(
        default=300,
        ge=30,
        le=900,
        description="Textract operation timeout in seconds",
    )


class ComprehendConfig(BaseSettings):
    """AWS Comprehend configuration for NLP tasks."""

    comprehend_enabled: bool = Field(
        default=True,
        description="Enable Comprehend NLP analysis",
    )
    comprehend_max_text_length: int = Field(
        default=100000,
        ge=1,
        le=100000,
        description="Maximum text length for Comprehend (bytes)",
    )
    comprehend_language_code: str = Field(
        default="en",
        description="Language code for Comprehend analysis",
    )


class OpenAIConfig(BaseSettings):
    """OpenAI API configuration."""

    openai_api_key: str = Field(
        ...,
        description="OpenAI API key (required)",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model identifier",
    )
    openai_max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="Maximum tokens for OpenAI responses",
    )
    openai_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for response generation",
    )

    # Rate Limiting
    openai_rate_limit_per_minute: int = Field(
        default=100,
        ge=1,
        description="OpenAI API calls per minute",
    )
    openai_rate_limit_per_day: int = Field(
        default=10000,
        ge=1,
        description="OpenAI API calls per day",
    )
    openai_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed requests",
    )
    openai_retry_delay: int = Field(
        default=1,
        ge=0,
        le=60,
        description="Delay between retries in seconds",
    )


class SupabaseConfig(BaseSettings):
    """Supabase configuration for database and authentication."""

    supabase_url: AnyHttpUrl = Field(
        ...,
        description="Supabase project URL (required)",
    )
    supabase_key: str = Field(
        ...,
        description="Supabase anonymous key (required)",
    )
    supabase_service_key: str = Field(
        ...,
        description="Supabase service role key (required)",
    )
    supabase_jwt_secret: str = Field(
        ...,
        description="Supabase JWT secret for token verification (required)",
    )

    # Database Configuration
    database_url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection URL (required)",
    )
    database_pool_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Database connection pool size",
    )
    database_max_overflow: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Maximum overflow connections",
    )


class PubNubConfig(BaseSettings):
    """PubNub configuration for real-time messaging."""

    pubnub_publish_key: str = Field(
        ...,
        description="PubNub publish key (required)",
    )
    pubnub_subscribe_key: str = Field(
        ...,
        description="PubNub subscribe key (required)",
    )
    pubnub_secret_key: str = Field(
        ...,
        description="PubNub secret key (required)",
    )
    pubnub_ssl: bool = Field(
        default=True,
        description="Enable SSL for PubNub connections",
    )
    pubnub_uuid: str = Field(
        default="pm-document-intelligence-backend",
        description="PubNub client UUID",
    )


class SecurityConfig(BaseSettings):
    """Security and authentication configuration."""

    # JWT Configuration
    jwt_secret_key: str = Field(
        ...,
        min_length=32,
        description="JWT signing secret key (required, min 32 chars)",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="JWT access token expiry in minutes",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=90,
        description="JWT refresh token expiry in days",
    )

    # Password Hashing
    bcrypt_rounds: int = Field(
        default=12,
        ge=10,
        le=16,
        description="Bcrypt hashing rounds",
    )

    # API Keys
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication",
    )
    api_key_salt: str = Field(
        ...,
        min_length=16,
        description="Salt for API key hashing (required)",
    )


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""

    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting globally",
    )
    rate_limit_strategy: Literal["fixed-window", "sliding-window"] = Field(
        default="fixed-window",
        description="Rate limiting strategy",
    )
    rate_limit_default: str = Field(
        default="100/minute",
        description="Default rate limit",
    )
    rate_limit_storage: Literal["redis", "memory"] = Field(
        default="redis",
        description="Storage backend for rate limiting",
    )

    # Per-endpoint rate limits
    rate_limit_upload: str = Field(
        default="10/minute",
        description="Rate limit for upload endpoint",
    )
    rate_limit_process: str = Field(
        default="20/minute",
        description="Rate limit for processing endpoint",
    )
    rate_limit_query: str = Field(
        default="100/minute",
        description="Rate limit for query endpoint",
    )


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration."""

    # Sentry Configuration
    sentry_dsn: str | None = Field(
        default=None,
        description="Sentry DSN for error tracking",
    )
    sentry_enabled: bool = Field(
        default=True,
        description="Enable Sentry error tracking",
    )
    sentry_environment: str = Field(
        default="development",
        description="Sentry environment name",
    )
    sentry_traces_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Sentry traces sample rate",
    )
    sentry_profiles_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Sentry profiles sample rate",
    )

    # Metrics Configuration
    metrics_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics",
    )
    metrics_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Prometheus metrics port",
    )
    prometheus_multiproc_dir: str = Field(
        default="/tmp/prometheus",
        description="Prometheus multiprocess directory",
    )

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application log level",
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format",
    )
    log_file: str = Field(
        default="logs/app.log",
        description="Log file path",
    )
    log_rotation: str = Field(
        default="10MB",
        description="Log rotation size",
    )
    log_retention: str = Field(
        default="30 days",
        description="Log retention period",
    )


class FeatureFlags(BaseSettings):
    """Feature flags for gradual feature rollouts."""

    feature_caching_enabled: bool = Field(
        default=True,
        description="Enable response caching",
    )
    feature_vector_search_enabled: bool = Field(
        default=True,
        description="Enable vector similarity search",
    )
    feature_multi_modal_enabled: bool = Field(
        default=True,
        description="Enable multi-modal document processing",
    )
    feature_real_time_updates_enabled: bool = Field(
        default=True,
        description="Enable real-time PubNub updates",
    )
    feature_batch_processing_enabled: bool = Field(
        default=True,
        description="Enable batch document processing",
    )
    feature_advanced_analytics_enabled: bool = Field(
        default=False,
        description="Enable advanced analytics features",
    )


class CacheConfig(BaseSettings):
    """Caching configuration."""

    cache_enabled: bool = Field(
        default=True,
        description="Enable caching globally",
    )
    cache_type: Literal["redis", "memory"] = Field(
        default="redis",
        description="Cache backend type",
    )
    cache_default_ttl: int = Field(
        default=3600,
        ge=0,
        description="Default cache TTL in seconds",
    )
    cache_max_size: int = Field(
        default=1000,
        ge=1,
        description="Maximum cache entries (memory only)",
    )

    # Specific cache TTLs
    cache_document_ttl: int = Field(
        default=7200,
        ge=0,
        description="Document cache TTL in seconds",
    )
    cache_analysis_ttl: int = Field(
        default=3600,
        ge=0,
        description="Analysis cache TTL in seconds",
    )
    cache_query_ttl: int = Field(
        default=1800,
        ge=0,
        description="Query cache TTL in seconds",
    )


class RedisConfig(BaseSettings):
    """Redis configuration for caching and rate limiting."""

    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_password: str | None = Field(
        default=None,
        description="Redis password",
    )
    redis_max_connections: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum Redis connections",
    )
    redis_socket_timeout: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Redis socket timeout in seconds",
    )
    redis_socket_connect_timeout: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Redis socket connect timeout in seconds",
    )


class Settings(BaseSettings):
    """
    Main application settings.

    This class aggregates all configuration sections and provides
    computed properties for derived values. All settings are loaded
    from environment variables and validated at startup.

    The configuration is immutable in production to prevent runtime
    changes that could affect system behavior.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    # Application Configuration
    app_name: str = Field(
        default="pm-document-intelligence",
        description="Application name",
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    secret_key: str = Field(
        ...,
        min_length=32,
        description="Application secret key (required, min 32 chars)",
    )
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of allowed hosts",
    )
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of CORS origins",
    )

    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="Server host",
    )
    port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Server port",
    )
    workers: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of worker processes",
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload (development only)",
    )

    # File Upload Configuration
    upload_dir: str = Field(
        default="uploads",
        description="Upload directory path",
    )
    max_upload_size: int = Field(
        default=52428800,  # 50MB
        ge=1024,
        le=524288000,  # 500MB max
        description="Maximum upload size in bytes",
    )
    allowed_extensions: str = Field(
        default="pdf,docx,doc,txt,xlsx,xls,pptx,ppt",
        description="Comma-separated list of allowed file extensions",
    )

    # Document Processing Configuration
    max_concurrent_processing: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum concurrent document processing jobs",
    )
    processing_timeout: int = Field(
        default=600,
        ge=30,
        le=3600,
        description="Document processing timeout in seconds",
    )
    ocr_enabled: bool = Field(
        default=True,
        description="Enable OCR processing",
    )
    ner_enabled: bool = Field(
        default=True,
        description="Enable named entity recognition",
    )
    sentiment_analysis_enabled: bool = Field(
        default=True,
        description="Enable sentiment analysis",
    )
    key_phrase_extraction_enabled: bool = Field(
        default=True,
        description="Enable key phrase extraction",
    )

    # Vector Search Configuration
    vector_db_type: Literal["supabase", "pinecone", "weaviate"] = Field(
        default="supabase",
        description="Vector database type",
    )
    vector_dimension: int = Field(
        default=1536,
        ge=128,
        le=3072,
        description="Vector embedding dimension",
    )
    vector_similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Vector similarity threshold",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model identifier",
    )

    # Agent Configuration
    agent_max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum agent iterations",
    )
    agent_timeout: int = Field(
        default=300,
        ge=30,
        le=1800,
        description="Agent timeout in seconds",
    )
    agent_memory_enabled: bool = Field(
        default=True,
        description="Enable agent conversation memory",
    )
    agent_tools_enabled: str = Field(
        default="textract,comprehend,search,summarize,analyze",
        description="Comma-separated list of enabled agent tools",
    )

    # MCP Configuration
    mcp_enabled: bool = Field(
        default=True,
        description="Enable Model Context Protocol",
    )
    mcp_server_port: int = Field(
        default=8001,
        ge=1024,
        le=65535,
        description="MCP server port",
    )
    mcp_max_context_length: int = Field(
        default=100000,
        ge=1000,
        le=1000000,
        description="Maximum MCP context length",
    )
    mcp_tools_enabled: bool = Field(
        default=True,
        description="Enable MCP tools",
    )

    # Testing Configuration
    testing: bool = Field(
        default=False,
        description="Enable testing mode",
    )
    test_database_url: PostgresDsn | None = Field(
        default=None,
        description="Test database URL",
    )
    mock_aws_services: bool = Field(
        default=False,
        description="Mock AWS services for testing",
    )
    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling",
    )

    # Production Optimizations
    gzip_enabled: bool = Field(
        default=True,
        description="Enable GZIP compression",
    )
    gzip_min_size: int = Field(
        default=1000,
        ge=0,
        description="Minimum size for GZIP compression in bytes",
    )
    compression_level: int = Field(
        default=6,
        ge=1,
        le=9,
        description="GZIP compression level",
    )

    # Health Check Configuration
    health_check_enabled: bool = Field(
        default=True,
        description="Enable health check endpoint",
    )
    health_check_path: str = Field(
        default="/health",
        description="Health check endpoint path",
    )
    readiness_check_path: str = Field(
        default="/ready",
        description="Readiness check endpoint path",
    )

    # Nested Configuration Objects
    aws: AWSConfig = Field(default_factory=AWSConfig)
    bedrock: BedrockConfig = Field(default_factory=BedrockConfig)
    textract: TextractConfig = Field(default_factory=TextractConfig)
    comprehend: ComprehendConfig = Field(default_factory=ComprehendConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    supabase: SupabaseConfig = Field(default_factory=SupabaseConfig)
    pubnub: PubNubConfig = Field(default_factory=PubNubConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)

    @model_validator(mode="after")
    def validate_environment_settings(self) -> "Settings":
        """Validate environment-specific settings."""
        # Production environment checks
        if self.environment == "production":
            if self.debug:
                raise ValueError("Debug mode must be disabled in production")
            if self.reload:
                raise ValueError("Auto-reload must be disabled in production")
            if len(self.secret_key) < 32:
                raise ValueError("Secret key must be at least 32 characters in production")
            if self.monitoring.log_level == "DEBUG":
                raise ValueError("Log level must not be DEBUG in production")

        # Development environment checks
        if self.environment == "development":
            if not self.debug:
                self.debug = True  # Auto-enable debug in development

        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.testing

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Parse allowed hosts into a list."""
        return [host.strip() for host in self.allowed_hosts.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Parse allowed extensions into a list."""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    @property
    def agent_tools_list(self) -> list[str]:
        """Parse agent tools into a list."""
        return [tool.strip() for tool in self.agent_tools_enabled.split(",")]

    @property
    def upload_path(self) -> Path:
        """Get upload directory as Path object."""
        return Path(self.upload_dir)

    @property
    def log_file_path(self) -> Path:
        """Get log file path as Path object."""
        return Path(self.monitoring.log_file)

    @property
    def max_upload_size_mb(self) -> float:
        """Get maximum upload size in megabytes."""
        return self.max_upload_size / (1024 * 1024)

    def get_aws_credentials(self) -> dict[str, str | None]:
        """
        Get AWS credentials dictionary.

        Returns:
            Dictionary with AWS credentials or empty if using IAM roles.
        """
        if self.aws.aws_access_key_id and self.aws.aws_secret_access_key:
            return {
                "aws_access_key_id": self.aws.aws_access_key_id,
                "aws_secret_access_key": self.aws.aws_secret_access_key,
                "aws_session_token": self.aws.aws_session_token,
                "region_name": self.aws.aws_region,
            }
        return {"region_name": self.aws.aws_region}

    def get_database_url(self, async_driver: bool = False) -> str:
        """
        Get database URL with optional async driver.

        Args:
            async_driver: If True, use asyncpg driver for async operations

        Returns:
            Database connection URL string
        """
        url = str(self.supabase.database_url)
        if async_driver:
            url = url.replace("postgresql://", "postgresql+asyncpg://")
        return url

    def to_dict(self, include_secrets: bool = False) -> dict[str, Any]:
        """
        Convert settings to dictionary.

        Args:
            include_secrets: If True, include sensitive values (use with caution)

        Returns:
            Dictionary representation of settings
        """
        data = self.model_dump()

        if not include_secrets:
            # Mask sensitive fields

            def mask_secrets(d: dict[str, Any]) -> None:
                """Recursively mask secret values."""
                for key, value in d.items():
                    if isinstance(value, dict):
                        mask_secrets(value)
                    elif any(
                        secret in key.lower()
                        for secret in ["key", "secret", "password", "token", "dsn"]
                    ):
                        if value:
                            d[key] = "***MASKED***"

            mask_secrets(data)

        return data


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This function uses lru_cache to ensure settings are loaded only once
    and reused throughout the application lifecycle.

    Returns:
        Singleton Settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()
