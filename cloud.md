# n8n on AWS — Terraform Setup Guide

This guide provisions a cost-optimised AWS EC2 instance running n8n, secured with HTTPS, and accessible via a custom Route 53 domain. Everything is managed with Terraform.

---

## Architecture Overview

```
Internet
   │
   ▼
Route 53 (your-domain.com → EC2 Elastic IP)
   │
   ▼
EC2 t4g.small  (ARM64 / Graviton2 — cheapest viable option)
  ├── Docker + n8n container
  ├── Caddy (reverse proxy + automatic HTTPS via Let's Encrypt)
  ├── Security Group (ports 22, 80, 443)
  └── Elastic IP (static public IP)
```

**Why t4g.small?**
- ~$12–13/month On-Demand (Sydney `ap-southeast-2`)
- ARM64 Graviton2 — ~20% cheaper than equivalent x86 t3.small
- 2 vCPU / 2 GB RAM — sufficient for personal/learning n8n
- Use a **t4g.micro** (1 GB RAM) only if budget is the absolute priority; n8n can be tight on 1 GB

---

## Prerequisites

- AWS CLI configured (`aws configure`)
- Terraform ≥ 1.6 installed
- A domain name already registered (or transfer to Route 53)
- An existing Route 53 **Hosted Zone** for your domain

---

## File Structure

```
n8n-aws/
├── main.tf
├── variables.tf
├── outputs.tf
├── user_data.sh
└── terraform.tfvars        ← you fill this in
```

---

## `variables.tf`

```hcl
variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-southeast-2"   # Sydney — closest to Brisbane
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.small"        # Cheapest ARM64 with 2 GB RAM
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
```

---

## `terraform.tfvars`

```hcl
aws_region              = "ap-southeast-2"
instance_type           = "t4g.small"
key_name                = "my-keypair"                  # replace
domain_name             = "n8n.yourdomain.com"          # replace
route53_zone_id         = "Z0123456789ABCDEFGHIJ"       # replace
n8n_basic_auth_user     = "admin"
n8n_basic_auth_password = "change-me-to-something-strong"
your_home_ip            = "203.0.113.10/32"             # replace with your IP
```

---

## `user_data.sh`

This script runs once on first boot to install Docker, n8n, and Caddy.

```bash
#!/bin/bash
set -euo pipefail

# ── Variables injected by Terraform ──────────────────────────────────────────
DOMAIN="${domain_name}"
N8N_USER="${n8n_basic_auth_user}"
N8N_PASS="${n8n_basic_auth_password}"

# ── System update ─────────────────────────────────────────────────────────────
apt-get update -y
apt-get upgrade -y
apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  unzip \
  htop \
  ufw

# ── Docker ────────────────────────────────────────────────────────────────────
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker
systemctl start docker

# ── Caddy (reverse proxy + automatic HTTPS) ───────────────────────────────────
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -y
apt-get install -y caddy

# ── n8n data directory ────────────────────────────────────────────────────────
mkdir -p /opt/n8n/data
chown -R 1000:1000 /opt/n8n/data

# ── Docker Compose for n8n ────────────────────────────────────────────────────
cat > /opt/n8n/docker-compose.yml <<EOF
version: "3.8"

services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASS}
      - N8N_HOST=${DOMAIN}
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://${DOMAIN}/
      - GENERIC_TIMEZONE=Australia/Brisbane
      - N8N_LOG_LEVEL=info
      - N8N_METRICS=true
    volumes:
      - /opt/n8n/data:/home/node/.n8n
    ports:
      - "5678:5678"
EOF

cd /opt/n8n && docker compose up -d

# ── Caddyfile ─────────────────────────────────────────────────────────────────
cat > /etc/caddy/Caddyfile <<EOF
${DOMAIN} {
    reverse_proxy localhost:5678

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options nosniff
        X-Frame-Options SAMEORIGIN
        Referrer-Policy no-referrer-when-downgrade
    }

    encode gzip

    log {
        output file /var/log/caddy/n8n-access.log
        format json
    }
}
EOF

mkdir -p /var/log/caddy
systemctl enable caddy
systemctl restart caddy

# ── UFW firewall (belt-and-suspenders alongside Security Group) ───────────────
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Caddy ACME challenge)
ufw allow 443/tcp   # HTTPS
ufw --force enable

# ── Automatic security updates ────────────────────────────────────────────────
apt-get install -y unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades

echo "Bootstrap complete — n8n is starting at https://${DOMAIN}"
```

---

## `main.tf`

```hcl
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

# ── Default VPC ───────────────────────────────────────────────────────────────
data "aws_vpc" "default" {
  default = true
}

# ── Security Group ────────────────────────────────────────────────────────────
resource "aws_security_group" "n8n" {
  name        = "n8n-sg"
  description = "n8n server security group"
  vpc_id      = data.aws_vpc.default.id

  # SSH — restricted to your home IP only
  ingress {
    description = "SSH from home"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.your_home_ip]
  }

  # HTTP — needed for Let's Encrypt ACME HTTP-01 challenge
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS — n8n UI and webhooks
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
  vpc_security_group_ids = [aws_security_group.n8n.id]

  # Prevent accidental termination
  disable_api_termination = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20     # GB — enough for n8n + Docker images + workflow data
    delete_on_termination = true
    encrypted             = true
  }

  user_data = templatefile("${path.module}/user_data.sh", {
    domain_name             = var.domain_name
    n8n_basic_auth_user     = var.n8n_basic_auth_user
    n8n_basic_auth_password = var.n8n_basic_auth_password
  })

  metadata_options {
    http_tokens = "required"   # IMDSv2 — security best practice
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

# ── CloudWatch: Basic CPU Alarm (optional but useful) ────────────────────────
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
```

---

## `outputs.tf`

```hcl
output "instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.n8n.id
}

output "elastic_ip" {
  description = "Public Elastic IP address"
  value       = aws_eip.n8n.public_ip
}

output "n8n_url" {
  description = "n8n UI URL"
  value       = "https://${var.domain_name}"
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_eip.n8n.public_ip}"
}
```

---

## Deployment Steps

### 1. Find your Route 53 Hosted Zone ID

```bash
aws route53 list-hosted-zones --query 'HostedZones[*].[Name,Id]' --output table
```

### 2. Find your home public IP

```bash
curl -s https://checkip.amazonaws.com
```

### 3. Fill in `terraform.tfvars`

Edit the file with your real values (domain, zone ID, key pair name, home IP, password).

### 4. Deploy

```bash
cd n8n-aws
terraform init
terraform plan
terraform apply
```

Terraform will output your Elastic IP and n8n URL. DNS propagation typically takes 1–5 minutes.

### 5. Wait for bootstrap

The `user_data.sh` script takes ~3–5 minutes to complete on first boot. You can monitor progress via:

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<ELASTIC_IP>
sudo tail -f /var/log/cloud-init-output.log
```

### 6. Access n8n

Open `https://n8n.yourdomain.com` in your browser. Log in with the username and password you set in `terraform.tfvars`.

---

## Cost Estimate (Sydney — ap-southeast-2)

| Resource              | Monthly Cost (approx.) |
|-----------------------|------------------------|
| t4g.small On-Demand   | ~$14 AUD               |
| gp3 EBS 20 GB         | ~$2 AUD                |
| Elastic IP (attached) | Free                   |
| Route 53 hosted zone  | ~$0.75 AUD             |
| Data transfer (light) | ~$1–2 AUD              |
| **Total**             | **~$18–20 AUD/month**  |

> **Tip — save ~30% more:** Convert the instance to a **1-year No Upfront Reserved Instance** once you decide to keep it. The t4g.small reserved price drops to ~$9–10 AUD/month.

---

## Useful Management Commands

```bash
# SSH into the server
ssh -i ~/.ssh/your-key.pem ubuntu@<ELASTIC_IP>

# Check n8n container logs
sudo docker logs -f n8n

# Restart n8n
cd /opt/n8n && sudo docker compose restart

# Update n8n to latest version
cd /opt/n8n
sudo docker compose pull
sudo docker compose up -d

# Check Caddy (reverse proxy) status
sudo systemctl status caddy
sudo journalctl -u caddy -f

# Check disk usage
df -h
```

---

## Backup n8n Data

n8n workflows and credentials live in `/opt/n8n/data`. Back this up regularly:

```bash
# One-off backup to S3
aws s3 cp /opt/n8n/data s3://your-backup-bucket/n8n-backup-$(date +%Y%m%d)/ --recursive
```

For automated backups, add a cron job on the instance:

```bash
# Run: sudo crontab -e
0 2 * * * aws s3 sync /opt/n8n/data s3://your-backup-bucket/n8n/ --delete
```

---

## Teardown

```bash
terraform destroy
```

> Note: `disable_api_termination = true` protects the instance from accidental deletion via the console. Terraform will override this automatically during `destroy`.

---

## Security Checklist

- [x] SSH restricted to your home IP only
- [x] n8n behind HTTPS with automatic certificate renewal (Caddy + Let's Encrypt)
- [x] n8n basic auth enabled
- [x] IMDSv2 enforced (prevents SSRF attacks against instance metadata)
- [x] EBS volume encrypted at rest
- [x] UFW firewall on the OS level (defence in depth)
- [x] Unattended security upgrades enabled
- [ ] **You should do:** rotate your `n8n_basic_auth_password` after first login
- [ ] **You should do:** set up MFA on your AWS account if not already done
