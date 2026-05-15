terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Latest Ubuntu 24.04 LTS ARM64 AMI ────────────────────────────────────────
data "aws_ami" "ubuntu_arm64" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

# ── Dedicated VPC ────────────────────────────────────────────────────────────
resource "aws_vpc" "n8n" {
  cidr_block           = "10.10.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "n8n-vpc" }
}

resource "aws_subnet" "n8n_public" {
  vpc_id                  = aws_vpc.n8n.id
  cidr_block              = "10.10.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = { Name = "n8n-public-subnet" }
}

resource "aws_internet_gateway" "n8n" {
  vpc_id = aws_vpc.n8n.id

  tags = { Name = "n8n-igw" }
}

resource "aws_route_table" "n8n_public" {
  vpc_id = aws_vpc.n8n.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.n8n.id
  }

  tags = { Name = "n8n-public-rt" }
}

resource "aws_route_table_association" "n8n_public" {
  subnet_id      = aws_subnet.n8n_public.id
  route_table_id = aws_route_table.n8n_public.id
}

# ── Security Group ────────────────────────────────────────────────────────────
resource "aws_security_group" "n8n" {
  name        = "n8n-sg"
  description = "n8n server security group"
  vpc_id      = aws_vpc.n8n.id

  ingress {
    description = "SSH from home"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.your_home_ip]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "n8n-sg"
  }
}

# ── EC2 Instance ──────────────────────────────────────────────────────────────
resource "aws_instance" "n8n" {
  ami                    = data.aws_ami.ubuntu_arm64.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.n8n_public.id
  vpc_security_group_ids = [aws_security_group.n8n.id]

  disable_api_termination = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    delete_on_termination = true
    encrypted             = true
  }

  user_data = templatefile("${path.module}/user_data.sh", {
    domain_name             = var.domain_name
    n8n_basic_auth_user     = var.n8n_basic_auth_user
    n8n_basic_auth_password = var.n8n_basic_auth_password
  })

  metadata_options {
    http_tokens = "required"
  }

  tags = {
    Name        = "n8n-server"
    Environment = "learning"
  }
}

# ── Elastic IP ────────────────────────────────────────────────────────────────
resource "aws_eip" "n8n" {
  instance = aws_instance.n8n.id
  domain   = "vpc"

  tags = {
    Name = "n8n-eip"
  }
}

# ── Route 53 DNS Record ───────────────────────────────────────────────────────
resource "aws_route53_record" "n8n" {
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.n8n.public_ip]
}

# ── CloudWatch CPU Alarm ──────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "n8n-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "n8n CPU above 80% for 10 minutes"

  dimensions = {
    InstanceId = aws_instance.n8n.id
  }
}
