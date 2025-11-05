# ============================================
# PM Document Intelligence - Terraform Backend
# S3 backend for state storage with DynamoDB for locking
# ============================================

terraform {
  backend "s3" {
    # S3 bucket for storing Terraform state
    # Replace with your actual bucket name
    bucket = "pm-doc-intel-terraform-state"

    # Path within the bucket
    key = "terraform.tfstate"

    # AWS region where bucket is located
    region = "us-east-1"

    # DynamoDB table for state locking
    dynamodb_table = "pm-doc-intel-terraform-locks"

    # Enable encryption at rest
    encrypt = true

    # Use AWS KMS for encryption (optional)
    # kms_key_id = "arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID"
  }
}

# ============================================
# Backend Infrastructure (one-time setup)
# ============================================
# This section creates the S3 bucket and DynamoDB table for Terraform state
# Run this once before using the backend configuration above

# Uncomment the resources below for initial setup, then comment them out
# and enable the backend configuration above

# # S3 Bucket for Terraform State
# resource "aws_s3_bucket" "terraform_state" {
#   bucket = "pm-doc-intel-terraform-state"
#
#   lifecycle {
#     prevent_destroy = true
#   }
#
#   tags = {
#     Name        = "Terraform State Bucket"
#     Environment = "all"
#     ManagedBy   = "Terraform"
#   }
# }
#
# # Enable versioning
# resource "aws_s3_bucket_versioning" "terraform_state" {
#   bucket = aws_s3_bucket.terraform_state.id
#
#   versioning_configuration {
#     status = "Enabled"
#   }
# }
#
# # Enable server-side encryption
# resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
#   bucket = aws_s3_bucket.terraform_state.id
#
#   rule {
#     apply_server_side_encryption_by_default {
#       sse_algorithm = "AES256"
#     }
#   }
# }
#
# # Block public access
# resource "aws_s3_bucket_public_access_block" "terraform_state" {
#   bucket = aws_s3_bucket.terraform_state.id
#
#   block_public_acls       = true
#   block_public_policy     = true
#   ignore_public_acls      = true
#   restrict_public_buckets = true
# }
#
# # DynamoDB Table for State Locking
# resource "aws_dynamodb_table" "terraform_locks" {
#   name         = "pm-doc-intel-terraform-locks"
#   billing_mode = "PAY_PER_REQUEST"
#   hash_key     = "LockID"
#
#   attribute {
#     name = "LockID"
#     type = "S"
#   }
#
#   lifecycle {
#     prevent_destroy = true
#   }
#
#   tags = {
#     Name        = "Terraform State Lock Table"
#     Environment = "all"
#     ManagedBy   = "Terraform"
#   }
# }
#
# # Outputs for backend setup
# output "terraform_state_bucket" {
#   value = aws_s3_bucket.terraform_state.id
# }
#
# output "terraform_lock_table" {
#   value = aws_dynamodb_table.terraform_locks.id
# }
