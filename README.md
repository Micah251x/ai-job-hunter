# AI Job Hunter

Serverless pipeline that discovers software engineering job postings from public ATS job-board APIs, analyzes each one against a candidate profile with an LLM, and produces a ranked daily shortlist.

**Status:** early development.

## Stack

Python 3.13 · AWS Lambda · Amazon SQS · DynamoDB · Terraform · Pydantic

## Development

This repository uses trunk-based development. `main` is always deployable.
Work happens on short-lived branches (`feat/`, `fix/`, `chore/`) merged via pull request.
