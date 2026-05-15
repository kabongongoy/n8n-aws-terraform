# n8n on AWS — Terraform Setup

Provisions a cost-optimised AWS EC2 instance running [n8n](https://n8n.io), secured with HTTPS via Caddy, and accessible through a custom Route 53 domain.

## Architecture

```
Internet
   │
   ▼
Route 53 (n8n.yourdomain.com → Elastic IP)
   │
   ▼
EC2 t4g.small  (ARM64 / Graviton2)
  ├── Docker + n8n container
  ├── Caddy (reverse proxy + automatic HTTPS via Let's Encrypt)
  ├── Dedicated VPC + public subnet
  ├── Security Group (ports 22, 80, 443)
  └── Elastic IP (static public IP)
```

## What Gets Created

| Resource | Details |
|---|---|
| EC2 instance | t4g.small ARM64 (Ubuntu 24.04 LTS) |
| VPC | Dedicated 10.10.0.0/16 with public subnet |
| Elastic IP | Static public IP attached to the instance |
| Route 53 record | A record pointing your domain to the Elastic IP |
| EBS volume | 20 GB gp3, encrypted at rest |
| CloudWatch alarm | CPU alert when above 80% for 10 minutes |

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.6
- [AWS CLI](https://aws.amazon.com/cli/) configured (`aws configure`)
- A Route 53 hosted zone for your domain
- An existing EC2 key pair

## Usage

**1. Clone the repo**

```bash
git clone https://github.com/kabongongoy/n8n-aws-terraform.git
cd n8n-aws-terraform
```

**2. Create your variables file**

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
aws_region              = "ap-southeast-2"
instance_type           = "t4g.small"
key_name                = "your-keypair-name"
domain_name             = "n8n.yourdomain.com"
route53_zone_id         = "ZXXXXXXXXXXXXXXXXXXXX"
n8n_basic_auth_user     = "admin"
n8n_basic_auth_password = "your-strong-password"
your_home_ip            = "1.2.3.4/32"   # curl checkip.amazonaws.com
```

Find your Route 53 zone ID:
```bash
aws route53 list-hosted-zones --query "HostedZones[*].[Name,Id]" --output table
```

**3. Deploy**

```bash
terraform init
terraform plan
terraform apply
```

Terraform will output your Elastic IP and n8n URL. The instance bootstrap script takes ~3–5 minutes to complete on first boot.

**4. Access n8n**

Open `https://n8n.yourdomain.com` and log in with the credentials you set in `terraform.tfvars`.

## Cost Estimate (Sydney — ap-southeast-2)

| Resource | Monthly Cost |
|---|---|
| t4g.small On-Demand | ~$14 AUD |
| gp3 EBS 20 GB | ~$2 AUD |
| Elastic IP (attached) | Free |
| Route 53 hosted zone | ~$0.75 AUD |
| Data transfer (light) | ~$1–2 AUD |
| **Total** | **~$18–20 AUD/month** |

> **Tip:** Convert to a 1-year No Upfront Reserved Instance to drop the EC2 cost to ~$9–10 AUD/month.

## Useful Commands

```bash
# SSH into the server
ssh -i ~/.ssh/your-key.pem ubuntu@<ELASTIC_IP>

# Check n8n logs
sudo docker logs -f n8n

# Restart n8n
cd /opt/n8n && sudo docker compose restart

# Update n8n to latest
cd /opt/n8n && sudo docker compose pull && sudo docker compose up -d

# Check Caddy status
sudo systemctl status caddy
```

## Teardown

```bash
terraform destroy
```

## Security

- SSH restricted to your home IP only
- HTTPS with automatic certificate renewal (Caddy + Let's Encrypt)
- n8n basic auth enabled
- IMDSv2 enforced (prevents SSRF against instance metadata)
- EBS volume encrypted at rest
- UFW firewall enabled on the OS level
- Unattended security upgrades enabled
