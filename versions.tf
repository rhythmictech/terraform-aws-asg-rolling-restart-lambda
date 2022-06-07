terraform {
  required_version = ">= 0.13.4"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 3.8"
    }

    external = {
      source  = "hashicorp/external"
      version = ">= 1.2"
    }

    local = {
      source  = "hashicorp/local"
      version = ">= 1.2"
    }

    null = {
      source  = "hashicorp/null"
      version = ">= 1.0"
    }

    random = {
      source  = "hashicorp/random"
      version = ">= 1.0"
    }
  }
}
