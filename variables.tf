variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-southeast-2"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.small"
}

variable "key_name" {
  description = "Name of an existing EC2 Key Pair for SSH access"
  type        = string
}

variable "domain_name" {
  description = "Full domain for n8n, e.g. n8n.example.com"
  type        = string
}

variable "route53_zone_id" {
  description = "Route 53 Hosted Zone ID for your domain"
  type        = string
}

variable "n8n_basic_auth_user" {
  description = "Username for n8n basic auth"
  type        = string
  default     = "admin"
}

variable "n8n_basic_auth_password" {
  description = "Password for n8n basic auth"
  type        = string
  sensitive   = true
}

variable "your_home_ip" {
  description = "Your home public IP (CIDR) for SSH access, e.g. 1.2.3.4/32"
  type        = string
}
