# outputs.tf
output "s3_bucket_name" {
  value = aws_s3_bucket.workout_data.id
}

output "sns_topic_arn" {
  value = aws_sns_topic.workout_notifications.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.workout_processor.function_name
}