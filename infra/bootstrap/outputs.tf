output "state_bucket_name" {
  description = "Name of the s3 bucket holding Terraform state"
  value       = aws_s3_bucket.tfstate.bucket
}