# ============================================
# PM Document Intelligence - Terraform Outputs
# ============================================

# ==========================================
# VPC Outputs
# ==========================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

# ==========================================
# Load Balancer Outputs
# ==========================================

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "alb_url" {
  description = "URL of the Application Load Balancer"
  value       = "https://${aws_lb.main.dns_name}"
}

output "api_url" {
  description = "API endpoint URL"
  value       = var.domain_name != "" ? "https://api.${var.domain_name}" : "https://${aws_lb.main.dns_name}"
}

# ==========================================
# ECS Outputs
# ==========================================

output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.backend.name
}

output "ecs_task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.backend.arn
}

output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

# ==========================================
# RDS Outputs
# ==========================================

output "rds_endpoint" {
  description = "Endpoint of the RDS instance"
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "Address of the RDS instance"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "Port of the RDS instance"
  value       = aws_db_instance.main.port
}

output "rds_database_name" {
  description = "Name of the database"
  value       = aws_db_instance.main.db_name
}

output "rds_username" {
  description = "Master username for the database"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "database_url" {
  description = "Full database connection URL"
  value       = "postgresql://${aws_db_instance.main.username}:****@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

# ==========================================
# ElastiCache Outputs
# ==========================================

output "redis_endpoint" {
  description = "Endpoint of the Redis cluster"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "redis_port" {
  description = "Port of the Redis cluster"
  value       = aws_elasticache_cluster.main.cache_nodes[0].port
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:${aws_elasticache_cluster.main.cache_nodes[0].port}"
}

# ==========================================
# S3 Outputs
# ==========================================

output "documents_bucket_name" {
  description = "Name of the documents S3 bucket"
  value       = aws_s3_bucket.documents.id
}

output "documents_bucket_arn" {
  description = "ARN of the documents S3 bucket"
  value       = aws_s3_bucket.documents.arn
}

output "backups_bucket_name" {
  description = "Name of the backups S3 bucket"
  value       = aws_s3_bucket.backups.id
}

output "backups_bucket_arn" {
  description = "ARN of the backups S3 bucket"
  value       = aws_s3_bucket.backups.arn
}

# ==========================================
# Secrets Manager Outputs
# ==========================================

output "jwt_secret_arn" {
  description = "ARN of the JWT secret"
  value       = aws_secretsmanager_secret.jwt_secret.arn
}

output "openai_api_key_secret_arn" {
  description = "ARN of the OpenAI API key secret"
  value       = aws_secretsmanager_secret.openai_api_key.arn
}

output "db_password_secret_arn" {
  description = "ARN of the database password secret"
  value       = aws_secretsmanager_secret.db_password.arn
}

# ==========================================
# Security Group Outputs
# ==========================================

output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "ecs_tasks_security_group_id" {
  description = "ID of the ECS tasks security group"
  value       = aws_security_group.ecs_tasks.id
}

output "rds_security_group_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds.id
}

output "elasticache_security_group_id" {
  description = "ID of the ElastiCache security group"
  value       = aws_security_group.elasticache.id
}

# ==========================================
# CloudWatch Outputs
# ==========================================

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs.arn
}

# ==========================================
# Route53 Outputs
# ==========================================

output "route53_api_record" {
  description = "Route53 record for API endpoint"
  value       = var.domain_name != "" ? aws_route53_record.api[0].fqdn : null
}

# ==========================================
# Deployment Information
# ==========================================

output "deployment_info" {
  description = "Deployment information and next steps"
  value = {
    environment      = var.environment
    region           = var.aws_region
    project_name     = var.project_name
    api_endpoint     = var.domain_name != "" ? "https://api.${var.domain_name}" : "https://${aws_lb.main.dns_name}"
    ecs_cluster      = aws_ecs_cluster.main.name
    ecs_service      = aws_ecs_service.backend.name
    database         = aws_db_instance.main.endpoint
    redis            = "${aws_elasticache_cluster.main.cache_nodes[0].address}:${aws_elasticache_cluster.main.cache_nodes[0].port}"
    documents_bucket = aws_s3_bucket.documents.id
    backups_bucket   = aws_s3_bucket.backups.id
  }
}

# ==========================================
# Cost Estimation
# ==========================================

output "estimated_monthly_cost_usd" {
  description = "Estimated monthly cost in USD (approximate)"
  value = {
    ecs_fargate    = "~$50-150 (based on task count and size)"
    rds            = "~$100-300 (based on instance class)"
    elasticache    = "~$50-100 (based on node type)"
    alb            = "~$20-30"
    nat_gateway    = "~$35 per NAT"
    data_transfer  = "~$10-50 (variable)"
    s3             = "~$5-20 (based on storage and requests)"
    cloudwatch     = "~$5-15 (based on logs and metrics)"
    total_estimate = "~$300-700/month for staging, ~$800-2000/month for production"
  }
}

# ==========================================
# Connection Commands
# ==========================================

output "connection_commands" {
  description = "Useful connection commands"
  value = {
    ecs_exec = "aws ecs execute-command --cluster ${aws_ecs_cluster.main.name} --task <task-id> --container backend --interactive --command '/bin/bash'"

    db_connect = "psql postgresql://${aws_db_instance.main.username}:<password>@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"

    redis_connect = "redis-cli -h ${aws_elasticache_cluster.main.cache_nodes[0].address} -p ${aws_elasticache_cluster.main.cache_nodes[0].port}"

    logs = "aws logs tail /ecs/${var.project_name}/${var.environment} --follow"
  }
}
