"""
Comprehensive health checks for liveness and readiness probes
"""

from typing import Dict, Any, Optional
from enum import Enum
import psutil
import time
from datetime import datetime
import boto3
from sqlalchemy import text
import redis


class HealthStatus(Enum):
    """Health check status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """Comprehensive health check system"""

    def __init__(self, db_session=None):
        self.db_session = db_session
        self.start_time = time.time()

    async def liveness(self) -> Dict[str, Any]:
        """
        Liveness probe - is the application running?
        Should return quickly, just checks if process is alive
        """
        return {
            "status": HealthStatus.HEALTHY.value,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
        }

    async def readiness(self) -> Dict[str, Any]:
        """
        Readiness probe - can the application serve traffic?
        Checks all dependencies
        """
        checks = {}
        overall_status = HealthStatus.HEALTHY

        # Database check
        db_health = await self.check_database()
        checks["database"] = db_health
        if db_health["status"] != HealthStatus.HEALTHY.value:
            overall_status = HealthStatus.UNHEALTHY

        # AWS services check
        aws_health = await self.check_aws_services()
        checks["aws"] = aws_health
        if aws_health["status"] == HealthStatus.UNHEALTHY.value:
            overall_status = HealthStatus.DEGRADED

        # Redis check
        redis_health = await self.check_redis()
        checks["redis"] = redis_health
        if redis_health["status"] != HealthStatus.HEALTHY.value:
            overall_status = HealthStatus.DEGRADED

        # Disk space check
        disk_health = self.check_disk_space()
        checks["disk"] = disk_health
        if disk_health["status"] != HealthStatus.HEALTHY.value:
            overall_status = HealthStatus.DEGRADED

        # Memory check
        memory_health = self.check_memory()
        checks["memory"] = memory_health
        if memory_health["status"] != HealthStatus.HEALTHY.value:
            overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        }

    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and health"""
        try:
            if not self.db_session:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": "Database session not configured",
                }

            # Simple query to check connectivity
            start = time.time()
            self.db_session.execute(text("SELECT 1"))
            latency_ms = (time.time() - start) * 1000

            return {
                "status": HealthStatus.HEALTHY.value,
                "latency_ms": round(latency_ms, 2),
                "message": "Database is accessible",
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Database error: {str(e)}",
            }

    async def check_aws_services(self) -> Dict[str, Any]:
        """Check AWS services connectivity"""
        services_status = {}
        overall_healthy = True

        # Check S3
        try:
            s3 = boto3.client("s3")
            s3.list_buckets()
            services_status["s3"] = "healthy"
        except Exception as e:
            services_status["s3"] = f"unhealthy: {str(e)}"
            overall_healthy = False

        # Check Textract
        try:
            textract = boto3.client("textract")
            # Simple service check without actual API call
            services_status["textract"] = "healthy"
        except Exception as e:
            services_status["textract"] = f"unhealthy: {str(e)}"
            overall_healthy = False

        return {
            "status": (
                HealthStatus.HEALTHY.value
                if overall_healthy
                else HealthStatus.UNHEALTHY.value
            ),
            "services": services_status,
        }

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            import os

            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))

            r = redis.Redis(host=redis_host, port=redis_port, socket_timeout=2)
            start = time.time()
            r.ping()
            latency_ms = (time.time() - start) * 1000

            return {
                "status": HealthStatus.HEALTHY.value,
                "latency_ms": round(latency_ms, 2),
                "message": "Redis is accessible",
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Redis error: {str(e)}",
            }

    def check_disk_space(self, threshold_percent: float = 90.0) -> Dict[str, Any]:
        """Check disk space usage"""
        try:
            disk = psutil.disk_usage("/")
            percent_used = disk.percent

            status = HealthStatus.HEALTHY
            if percent_used >= threshold_percent:
                status = HealthStatus.UNHEALTHY
            elif percent_used >= 80.0:
                status = HealthStatus.DEGRADED

            return {
                "status": status.value,
                "usage_percent": percent_used,
                "free_gb": round(disk.free / (1024**3), 2),
                "total_gb": round(disk.total / (1024**3), 2),
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Disk check error: {str(e)}",
            }

    def check_memory(self, threshold_percent: float = 90.0) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent

            status = HealthStatus.HEALTHY
            if percent_used >= threshold_percent:
                status = HealthStatus.UNHEALTHY
            elif percent_used >= 80.0:
                status = HealthStatus.DEGRADED

            return {
                "status": status.value,
                "usage_percent": percent_used,
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2),
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Memory check error: {str(e)}",
            }


# Global health checker instance
health_checker = HealthCheck()
