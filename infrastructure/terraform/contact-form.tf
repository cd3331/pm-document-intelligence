# ==========================================
# JoyofPM Contact Form Infrastructure
# ==========================================

# DynamoDB table for contact form submissions
resource "aws_dynamodb_table" "contact_submissions" {
  name           = "joyofpm-contact-submissions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "submission_id"
  range_key      = "timestamp"

  attribute {
    name = "submission_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "EmailIndex"
    hash_key        = "email"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "joyofpm-contact-submissions"
    Environment = "production"
  }
}

# IAM role for Lambda function
resource "aws_iam_role" "contact_form_lambda" {
  name = "joyofpm-contact-form-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "joyofpm-contact-form-lambda-role"
    Environment = "production"
  }
}

# IAM policy for Lambda function
resource "aws_iam_role_policy" "contact_form_lambda_policy" {
  name = "joyofpm-contact-form-lambda-policy"
  role = aws_iam_role.contact_form_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.contact_submissions.arn,
          "${aws_dynamodb_table.contact_submissions.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Lambda function for contact form processing
resource "aws_lambda_function" "contact_form" {
  filename      = "contact_form_lambda.zip"
  function_name = "joyofpm-contact-form-handler"
  role          = aws_iam_role.contact_form_lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 30

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.contact_submissions.name
      RECIPIENT_EMAIL = "joyofprojectmanagement@gmail.com"
      CALENDLY_LINK = "https://calendly.com/chandra-r-dunn"
    }
  }

  tags = {
    Name        = "joyofpm-contact-form-handler"
    Environment = "production"
  }
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "contact_form" {
  name        = "joyofpm-contact-form-api"
  description = "API for JoyofPM contact form"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = "joyofpm-contact-form-api"
    Environment = "production"
  }
}

# API Gateway resource
resource "aws_api_gateway_resource" "contact" {
  rest_api_id = aws_api_gateway_rest_api.contact_form.id
  parent_id   = aws_api_gateway_rest_api.contact_form.root_resource_id
  path_part   = "contact"
}

# API Gateway POST method
resource "aws_api_gateway_method" "contact_post" {
  rest_api_id   = aws_api_gateway_rest_api.contact_form.id
  resource_id   = aws_api_gateway_resource.contact.id
  http_method   = "POST"
  authorization = "NONE"
}

# API Gateway OPTIONS method for CORS
resource "aws_api_gateway_method" "contact_options" {
  rest_api_id   = aws_api_gateway_rest_api.contact_form.id
  resource_id   = aws_api_gateway_resource.contact.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# API Gateway integration with Lambda
resource "aws_api_gateway_integration" "contact_post_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.contact_form.id
  resource_id             = aws_api_gateway_resource.contact.id
  http_method             = aws_api_gateway_method.contact_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.contact_form.invoke_arn
}

# API Gateway CORS integration
resource "aws_api_gateway_integration" "contact_options" {
  rest_api_id = aws_api_gateway_rest_api.contact_form.id
  resource_id = aws_api_gateway_resource.contact.id
  http_method = aws_api_gateway_method.contact_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# API Gateway method response for OPTIONS
resource "aws_api_gateway_method_response" "contact_options" {
  rest_api_id = aws_api_gateway_rest_api.contact_form.id
  resource_id = aws_api_gateway_resource.contact.id
  http_method = aws_api_gateway_method.contact_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

# API Gateway integration response for OPTIONS
resource "aws_api_gateway_integration_response" "contact_options" {
  rest_api_id = aws_api_gateway_rest_api.contact_form.id
  resource_id = aws_api_gateway_resource.contact.id
  http_method = aws_api_gateway_method.contact_options.http_method
  status_code = aws_api_gateway_method_response.contact_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'https://joyofpm.com'"
  }

  depends_on = [aws_api_gateway_integration.contact_options]
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "contact_form" {
  rest_api_id = aws_api_gateway_rest_api.contact_form.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.contact.id,
      aws_api_gateway_method.contact_post.id,
      aws_api_gateway_method.contact_options.id,
      aws_api_gateway_integration.contact_post_lambda.id,
      aws_api_gateway_integration.contact_options.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.contact_post_lambda,
    aws_api_gateway_integration.contact_options,
  ]
}

# API Gateway stage
resource "aws_api_gateway_stage" "contact_form" {
  deployment_id = aws_api_gateway_deployment.contact_form.id
  rest_api_id   = aws_api_gateway_rest_api.contact_form.id
  stage_name    = "prod"

  tags = {
    Name        = "joyofpm-contact-form-api-prod"
    Environment = "production"
  }
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.contact_form.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.contact_form.execution_arn}/*/*"
}

# Outputs
output "contact_form_api_endpoint" {
  value       = "${aws_api_gateway_stage.contact_form.invoke_url}/contact"
  description = "Contact form API endpoint"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.contact_submissions.name
  description = "DynamoDB table for contact submissions"
}
