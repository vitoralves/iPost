output "ecr_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

output "lambda_function_name" {
  value = try(aws_lambda_function.worker[0].function_name, "")
}

output "story_generate_schedule" {
  value = try(aws_scheduler_schedule.story_generate[0].name, "")
}

output "story_publish_schedule" {
  value = try(aws_scheduler_schedule.story_publish[0].name, "")
}

output "reel_generate_schedule" {
  value = try(aws_scheduler_schedule.reel_generate[0].name, "")
}

output "reel_publish_schedule" {
  value = try(aws_scheduler_schedule.reel_publish[0].name, "")
}

output "insights_sync_schedule" {
  value = try(aws_scheduler_schedule.insights_sync[0].name, "")
}
