data "aws_caller_identity" "current" {}

locals {
  worker_ready = var.image_uri != ""
  clock_on     = var.scheduler_enabled && local.worker_ready
}

resource "aws_ecr_repository" "worker" {
  name                 = "ipost-worker"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }
}

resource "aws_ecr_repository_policy" "worker_lambda" {
  repository = aws_ecr_repository.worker.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Sid    = "LambdaPull"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Condition = {
          ArnLike = {
            "aws:sourceArn" = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:ipost-worker"
          }
        }
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/ipost-worker"
  retention_in_days = 14
}

resource "aws_iam_role" "worker" {
  name = "ipost-worker-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "worker_logs" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "worker_bedrock" {
  name = "ipost-worker-bedrock"
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:*:inference-profile/us.amazon.nova-pro-v1:0",
          "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0",
          "arn:aws:bedrock:us-east-2::foundation-model/amazon.nova-pro-v1:0",
          "arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-pro-v1:0",
          "arn:aws:bedrock:us-west-2::foundation-model/stability.sd3-5-large-v1:0"
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "worker" {
  count         = local.worker_ready ? 1 : 0
  function_name = "ipost-worker"
  package_type  = "Image"
  image_uri     = var.image_uri
  role          = aws_iam_role.worker.arn
  timeout       = 900
  memory_size   = 2048
  architectures = ["x86_64"]

  ephemeral_storage {
    size = 2048
  }

  environment {
    variables = {
      SUPABASE_URL               = var.supabase_url
      SUPABASE_SERVICE_ROLE_KEY  = var.supabase_service_role_key
      SUPABASE_OUTBOX_BUCKET     = var.supabase_outbox_bucket
      SUPABASE_PRIVATE_BUCKET    = var.supabase_private_bucket
      BEDROCK_REGION             = var.aws_region
      BEDROCK_MODEL_ID           = var.bedrock_model_id
      BEDROCK_IMAGE_MODEL_ID     = var.bedrock_image_model_id
      OPENAI_API_KEY             = var.openai_api_key
      OPENAI_IMAGE_MODEL_ID      = var.openai_image_model_id
      IPOST_MOCK_BEDROCK         = var.ipost_mock_bedrock
      ALERT_EMAIL                = var.alert_email
      RESEND_API_KEY             = var.resend_api_key
      RESEND_FROM                = var.resend_from
    }
  }

  depends_on = [aws_cloudwatch_log_group.worker]
}

resource "aws_iam_role" "scheduler" {
  count = local.clock_on ? 1 : 0
  name  = "ipost-eventbridge-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  count = local.clock_on ? 1 : 0
  name  = "ipost-scheduler-invoke"
  role  = aws_iam_role.scheduler[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.worker[0].arn
      }
    ]
  })
}

resource "aws_scheduler_schedule" "story_generate" {
  count = local.clock_on ? 1 : 0
  name  = "ipost-story-generate"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 4 * * ? *)"
  schedule_expression_timezone = "America/Sao_Paulo"
  state                        = "ENABLED"

  target {
    arn      = aws_lambda_function.worker[0].arn
    role_arn = aws_iam_role.scheduler[0].arn
    input    = jsonencode({ action = "generate", type = "STORY" })
  }
}

resource "aws_scheduler_schedule" "story_publish" {
  count = local.clock_on ? 1 : 0
  name  = "ipost-story-publish"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 6 * * ? *)"
  schedule_expression_timezone = "America/Sao_Paulo"
  state                        = "ENABLED"

  target {
    arn      = aws_lambda_function.worker[0].arn
    role_arn = aws_iam_role.scheduler[0].arn
    input    = jsonencode({ action = "publish" })
  }
}

resource "aws_lambda_permission" "scheduler_generate" {
  count         = local.clock_on ? 1 : 0
  statement_id  = "AllowSchedulerGenerate"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker[0].function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.story_generate[0].arn
}

resource "aws_lambda_permission" "scheduler_publish" {
  count         = local.clock_on ? 1 : 0
  statement_id  = "AllowSchedulerPublish"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker[0].function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.story_publish[0].arn
}
