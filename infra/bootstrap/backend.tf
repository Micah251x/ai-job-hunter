terraform {
  backend "s3" {
    bucket       = "ai-job-hunter-tfstate-213527446132"
    key          = "bootstrap/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}