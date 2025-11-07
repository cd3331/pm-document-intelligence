# ==========================================
# JoyofPM App Infrastructure (app.joyofpm.com)
# ==========================================

# S3 bucket policy for CloudFront access
resource "aws_s3_bucket_policy" "app" {
  bucket = "joyofpm-app"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "arn:aws:s3:::joyofpm-app/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.app.arn
          }
        }
      }
    ]
  })
}

# CloudFront Origin Access Control for App
resource "aws_cloudfront_origin_access_control" "app" {
  name                              = "joyofpm-app-oac"
  description                       = "Origin Access Control for JoyofPM App"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Distribution for App
resource "aws_cloudfront_distribution" "app" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "JoyofPM PM Document Intelligence App"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"  # US, Canada, Europe
  aliases             = ["app.joyofpm.com"]

  origin {
    domain_name              = "joyofpm-app.s3.us-east-1.amazonaws.com"
    origin_id                = "S3-joyofpm-app"
    origin_access_control_id = aws_cloudfront_origin_access_control.app.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-joyofpm-app"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = true  # Allow query strings for document IDs
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # Custom error responses for SPA routing
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = "arn:aws:acm:us-east-1:488678936715:certificate/42c8c030-cb8d-4abf-958f-f7b65a5f6c08"
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name        = "joyofpm-app-distribution"
    Environment = "production"
  }
}

# Route53 record for app subdomain
resource "aws_route53_record" "app" {
  zone_id = "Z0686139VDJE21NA059A"
  name    = "app.joyofpm.com"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.app.domain_name
    zone_id                = aws_cloudfront_distribution.app.hosted_zone_id
    evaluate_target_health = false
  }
}

# Output CloudFront distribution domain
output "app_cloudfront_domain" {
  value       = aws_cloudfront_distribution.app.domain_name
  description = "CloudFront distribution domain for app"
}

output "app_url" {
  value       = "https://app.joyofpm.com"
  description = "App URL"
}
