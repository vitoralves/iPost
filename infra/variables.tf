variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "image_uri" {
  type    = string
  default = ""
}

variable "scheduler_enabled" {
  type    = bool
  default = false
}

variable "ipost_mock_bedrock" {
  type    = string
  default = "true"
}

variable "supabase_url" {
  type      = string
  sensitive = true
}

variable "supabase_service_role_key" {
  type      = string
  sensitive = true
}

variable "supabase_outbox_bucket" {
  type    = string
  default = "outbox"
}

variable "supabase_private_bucket" {
  type    = string
  default = "private"
}

variable "bedrock_model_id" {
  type    = string
  default = "us.amazon.nova-pro-v1:0"
}

variable "bedrock_image_model_id" {
  type    = string
  default = "stability.sd3-5-large-v1:0"
}

variable "openai_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "openai_image_model_id" {
  type    = string
  default = "gpt-image-2"
}

variable "alert_email" {
  type    = string
  default = "vitordgav@gmail.com"
}

variable "resend_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "resend_from" {
  type    = string
  default = "iPost <onboarding@resend.dev>"
}
