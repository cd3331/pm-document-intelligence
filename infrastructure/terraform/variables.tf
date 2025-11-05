# ============================================
# PM Document Intelligence - Terraform Variables
# ============================================

# ==========================================
# General Configuration
# ==========================================

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "pm-doc-intel"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "engineering"
}

# ==========================================
# Network Configuration
# ==========================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use"
  type        = number
  default     = 2
  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "AZ count must be between 2 and 3."
  }
}

# ==========================================
# ECS Configuration
# ==========================================

variable "ecs_task_cpu" {
  description = "CPU units for ECS task (1024 = 1 vCPU)"
  type        = string
  default     = "2048"
}

variable "ecs_task_memory" {
  description = "Memory for ECS task in MB"
  type        = string
  default     = "4096"
}

variable "ecs_service_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "ecs_autoscaling_min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 2
}

variable "ecs_autoscaling_max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 10
}

variable "ecr_repository_url" {
  description = "URL of the ECR repository"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

# ==========================================
# RDS Configuration
# ==========================================

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.4"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_name" {
  description = "Name of the database"
  type        = string
  default     = "pm_document_intelligence"
}

variable "db_username" {
  description = "Master username for database"
  type        = string
  default     = "pmadmin"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for RDS in GB"
  type        = number
  default     = 500
}

variable "db_backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "db_backup_window" {
  description = "Daily backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "Weekly maintenance window (UTC)"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

# ==========================================
# ElastiCache Configuration
# ==========================================

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.medium"
}

# ==========================================
# SSL/TLS Configuration
# ==========================================

variable "ssl_certificate_arn" {
  description = "ARN of the SSL certificate for HTTPS"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# ==========================================
# Logging Configuration
# ==========================================

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# ==========================================
# Backup Configuration
# ==========================================

variable "backup_retention_days" {
  description = "S3 backup retention in days"
  type        = number
  default     = 30
}

# ==========================================
# Environment-Specific Configurations
# ==========================================

# Development
variable "dev_config" {
  description = "Development environment configuration"
  type = object({
    ecs_task_cpu              = string
    ecs_task_memory           = string
    ecs_service_desired_count = number
    db_instance_class         = string
    redis_node_type           = string
  })
  default = {
    ecs_task_cpu              = "1024"
    ecs_task_memory           = "2048"
    ecs_service_desired_count = 1
    db_instance_class         = "db.t3.small"
    redis_node_type           = "cache.t3.micro"
  }
}

# Staging
variable "staging_config" {
  description = "Staging environment configuration"
  type = object({
    ecs_task_cpu              = string
    ecs_task_memory           = string
    ecs_service_desired_count = number
    db_instance_class         = string
    redis_node_type           = string
  })
  default = {
    ecs_task_cpu              = "2048"
    ecs_task_memory           = "4096"
    ecs_service_desired_count = 2
    db_instance_class         = "db.t3.medium"
    redis_node_type           = "cache.t3.small"
  }
}

# Production
variable "prod_config" {
  description = "Production environment configuration"
  type = object({
    ecs_task_cpu              = string
    ecs_task_memory           = string
    ecs_service_desired_count = number
    db_instance_class         = string
    redis_node_type           = string
  })
  default = {
    ecs_task_cpu              = "4096"
    ecs_task_memory           = "8192"
    ecs_service_desired_count = 3
    db_instance_class         = "db.r6g.xlarge"
    redis_node_type           = "cache.r6g.large"
  }
}

# ==========================================
# Feature Flags
# ==========================================

variable "enable_container_insights" {
  description = "Enable ECS Container Insights"
  type        = bool
  default     = true
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for production resources"
  type        = bool
  default     = true
}

variable "enable_multi_az" {
  description = "Enable Multi-AZ for RDS and ElastiCache"
  type        = bool
  default     = false
}

variable "enable_performance_insights" {
  description = "Enable RDS Performance Insights"
  type        = bool
  default     = true
}

# ==========================================
# Tags
# ==========================================

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
