# ==========================================
# JoyofPM Website Infrastructure
# ==========================================

# S3 bucket policy for CloudFront access
resource "aws_s3_bucket_policy" "website" {
  bucket = "joyofpm-website"

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
        Resource = "arn:aws:s3:::joyofpm-website/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.website.arn
          }
        }
      }
    ]
  })
}

# CloudFront Origin Access Control
resource "aws_cloudfront_origin_access_control" "website" {
  name                              = "joyofpm-website-oac"
  description                       = "Origin Access Control for JoyofPM website"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Distribution for Homepage
resource "aws_cloudfront_distribution" "website" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "JoyofPM Homepage"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"  # US, Canada, Europe
  aliases             = ["joyofpm.com", "www.joyofpm.com"]

  origin {
    domain_name              = "joyofpm-website.s3.us-east-1.amazonaws.com"
    origin_id                = "S3-joyofpm-website"
    origin_access_control_id = aws_cloudfront_origin_access_control.website.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-joyofpm-website"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # Custom error responses
  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/error.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 403
    response_page_path = "/error.html"
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
    Name        = "joyofpm-website-distribution"
    Environment = "production"
  }
}

# Route53 record for homepage (root domain)
resource "aws_route53_record" "website_root" {
  zone_id = "Z0686139VDJE21NA059A"
  name    = "joyofpm.com"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.website.domain_name
    zone_id                = aws_cloudfront_distribution.website.hosted_zone_id
    evaluate_target_health = false
  }
}

# Route53 record for www subdomain
resource "aws_route53_record" "website_www" {
  zone_id = "Z0686139VDJE21NA059A"
  name    = "www.joyofpm.com"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.website.domain_name
    zone_id                = aws_cloudfront_distribution.website.hosted_zone_id
    evaluate_target_health = false
  }
}

# Output CloudFront distribution domain
output "website_cloudfront_domain" {
  value       = aws_cloudfront_distribution.website.domain_name
  description = "CloudFront distribution domain for website"
}

output "website_url" {
  value       = "https://joyofpm.com"
  description = "Website URL"
}
