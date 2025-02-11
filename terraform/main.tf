# main.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
  
  backend "s3" {
    bucket = "terraform-state-workout-tracker"
    key    = "workout-tracker/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 bucket for workout data
resource "aws_s3_bucket" "workout_data" {
  bucket = "${var.project_name}-${var.environment}-data"
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "workout_data_versioning" {
  bucket = aws_s3_bucket.workout_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# SNS Topic for notifications
resource "aws_sns_topic" "workout_notifications" {
  name = "${var.project_name}-${var.environment}-notifications"
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-${var.environment}-lambda-role"

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
}

# IAM policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-${var.environment}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "sns:Publish",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          aws_s3_bucket.workout_data.arn,
          "${aws_s3_bucket.workout_data.arn}/*",
          aws_sns_topic.workout_notifications.arn
        ]
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "workout_processor" {
  filename         = var.lambda_zip_path
  function_name    = "${var.project_name}-${var.environment}-processor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "enhanced_workout_processor.handler"
  runtime         = "python3.8"
  timeout         = 300
  memory_size     = 256

  environment {
    variables = {
      ENVIRONMENT = var.environment
      SNS_TOPIC_ARN = aws_sns_topic.workout_notifications.arn
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 event trigger for Lambda
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.workout_data.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.workout_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }
}

# Lambda permission for S3
resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.workout_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.workout_data.arn
}
