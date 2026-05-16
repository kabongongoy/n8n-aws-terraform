# End-to-End Documentation: Building an AI Agent with Internet Search on AWS

## What Are We Building?

Imagine you want a smart assistant that can:
- Answer questions it already knows (like a textbook)
- Search the internet when it needs fresh information (like a researcher)
- Run 24/7 on your own server without paying for expensive API services

That is exactly what this guide builds. Think of it like setting up your own mini Google + ChatGPT on a server you control.

---

## The Big Picture (How Everything Fits Together)

```
Your Browser
     │
     │  HTTPS (secure connection)
     ▼
Caddy (the doorman)
     │
     ├──► n8n (the brain / workflow engine)
     │         │
     │         ├──► Groq API (the LLM - thinks and decides)
     │         │
     │         └──► SearXNG (the search engine - finds current info)
     │
     └──► Your Chatbot Page (the face / UI)
```

Everything runs inside Docker containers on a single AWS EC2 server.

---

## Part 1: The Server — AWS EC2 with Terraform

### What is AWS EC2?

AWS EC2 is like renting a computer in Amazon's data centre. Instead of buying a physical computer, you pay a small monthly fee and get a virtual computer running 24/7 in the cloud.

### What is Terraform?

Terraform is a tool that lets you describe your server setup in a text file and then automatically creates everything for you. Instead of clicking through AWS menus, you write instructions and Terraform does the work.

### What is a t4g.small?

It is the type of virtual computer we chose:
- 2 CPU cores
- 2 GB of memory (RAM)
- ARM64 chip (same technology as Apple Silicon — more efficient, cheaper)
- Costs approximately $14 AUD per month

---

### Step 1.1 — Install the Required Tools

Before anything, install these on your Windows computer:

1. **Terraform** — download from https://developer.hashicorp.com/terraform/install
2. **AWS CLI** — download from https://aws.amazon.com/cli/
3. **Configure AWS** — open a terminal and run:
   ```bash
   aws configure
   ```
   Enter your AWS Access Key, Secret Key, region (`ap-southeast-2`), and output format (`json`).

---

### Step 1.2 — Create the Terraform Files

Create a folder called `n8n-aws` and create these five files inside it.

#### File 1: `variables.tf` — The Settings Descriptions

This file defines what settings the setup needs. Think of it as a form with blank fields.

```hcl
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
  description = "Name of your EC2 Key Pair for SSH access"
  type        = string
}

variable "domain_name" {
  description = "Your domain for n8n, e.g. n8n.yourdomain.com"
  type        = string
}

variable "route53_zone_id" {
  description = "Route 53 Hosted Zone ID"
  type        = string
}

variable "n8n_basic_auth_user" {
  description = "Username for n8n login"
  type        = string
  default     = "admin"
}

variable "n8n_basic_auth_password" {
  description = "Password for n8n login"
  type        = string
  sensitive   = true
}

variable "your_home_ip" {
  description = "Your home IP address for SSH access (e.g. 1.2.3.4/32)"
  type        = string
}
```

#### File 2: `terraform.tfvars` — Your Actual Values

This file fills in the blanks from variables.tf with your real values.

```hcl
aws_region              = "ap-southeast-2"
instance_type           = "t4g.small"
key_name                = "your-keypair-name"
domain_name             = "n8n.yourdomain.com"
route53_zone_id         = "ZXXXXXXXXXXXXXXXXXXXX"
n8n_basic_auth_user     = "admin"
n8n_basic_auth_password = "your-strong-password"
your_home_ip            = "1.2.3.4/32"
```

> **Important:** Never commit this file to Git. It contains your password.

To find your values:
```bash
# Find your Route 53 Zone ID
aws route53 list-hosted-zones --query "HostedZones[*].[Name,Id]" --output table

# Find your home IP
curl https://checkip.amazonaws.com
```

#### File 3: `main.tf` — The Infrastructure Blueprint

This is the main file that tells Terraform what to build.

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

# Find the latest Ubuntu 24.04 ARM64 image
data "aws_ami" "ubuntu_arm64" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*"]
  }
  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

# Create a dedicated network (VPC) for our server
resource "aws_vpc" "n8n" {
  cidr_block           = "10.10.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "n8n-vpc" }
}

# Create a public subnet inside the VPC
resource "aws_subnet" "n8n_public" {
  vpc_id                  = aws_vpc.n8n.id
  cidr_block              = "10.10.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags = { Name = "n8n-public-subnet" }
}

# Internet Gateway — the door between our server and the internet
resource "aws_internet_gateway" "n8n" {
  vpc_id = aws_vpc.n8n.id
  tags   = { Name = "n8n-igw" }
}

# Route table — tells traffic how to reach the internet
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

# Firewall rules — only allow specific traffic
resource "aws_security_group" "n8n" {
  name   = "n8n-sg"
  vpc_id = aws_vpc.n8n.id

  ingress {
    description = "SSH from home only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.your_home_ip]
  }

  ingress {
    description = "HTTP (for SSL certificate)"
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

  tags = { Name = "n8n-sg" }
}

# The actual EC2 server
resource "aws_instance" "n8n" {
  ami                     = data.aws_ami.ubuntu_arm64.id
  instance_type           = var.instance_type
  key_name                = var.key_name
  subnet_id               = aws_subnet.n8n_public.id
  vpc_security_group_ids  = [aws_security_group.n8n.id]
  disable_api_termination = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    delete_on_termination = true
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

# Static IP address (never changes even if server restarts)
resource "aws_eip" "n8n" {
  instance = aws_instance.n8n.id
  domain   = "vpc"
  tags     = { Name = "n8n-eip" }
}

# DNS record — points your domain to the server IP
resource "aws_route53_record" "n8n" {
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.n8n.public_ip]
}

# Alert if CPU usage is too high
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "n8n-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  dimensions          = { InstanceId = aws_instance.n8n.id }
}
```

#### File 4: `outputs.tf` — What to Show After Deployment

```hcl
output "elastic_ip" {
  value = aws_eip.n8n.public_ip
}

output "n8n_url" {
  value = "https://${var.domain_name}"
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_eip.n8n.public_ip}"
}
```

#### File 5: `user_data.sh` — Server Setup Script

This script runs automatically on first boot and installs everything.

```bash
#!/bin/bash
set -euo pipefail

DOMAIN="${domain_name}"
N8N_USER="${n8n_basic_auth_user}"
N8N_PASS="${n8n_basic_auth_password}"

# Update the operating system
apt-get update -y && apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg lsb-release ufw unzip htop

# Install Docker
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable docker && systemctl start docker

# Install Caddy (reverse proxy)
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -y && apt-get install -y caddy

# Create n8n data directory
mkdir -p /opt/n8n/data
chown -R 1000:1000 /opt/n8n/data

# Create n8n Docker Compose file
cat > /opt/n8n/docker-compose.yml <<EOF
services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=$N8N_USER
      - N8N_BASIC_AUTH_PASSWORD=$N8N_PASS
      - N8N_HOST=$DOMAIN
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://$DOMAIN/
      - GENERIC_TIMEZONE=Australia/Brisbane
      - N8N_LOG_LEVEL=info
      - N8N_TRUST_PROXY=true
    volumes:
      - /opt/n8n/data:/home/node/.n8n
    ports:
      - "5678:5678"
EOF

cd /opt/n8n && docker compose up -d

# Configure Caddy as reverse proxy with HTTPS
cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    handle_path /chatbot* {
        root * /var/www/chatbot
        file_server
    }

    handle_path /agent* {
        root * /var/www/agent
        file_server
    }

    handle {
        reverse_proxy localhost:5678 {
            header_down Access-Control-Allow-Origin *
            header_down Access-Control-Allow-Methods "POST, GET, OPTIONS"
            header_down Access-Control-Allow-Headers "Content-Type"
        }
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options nosniff
        Referrer-Policy no-referrer-when-downgrade
    }

    encode gzip
}
EOF

mkdir -p /var/www/chatbot /var/www/agent /var/log/caddy
systemctl enable caddy && systemctl restart caddy

# Firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Automatic security updates
apt-get install -y unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades
```

---

### Step 1.3 — Deploy with Terraform

Open a terminal in your `n8n-aws` folder and run:

```bash
# Download AWS provider
terraform init

# Preview what will be created (nothing happens yet)
terraform plan

# Actually create everything (type 'yes' when asked)
terraform apply
```

Terraform will create 10 AWS resources and show you your server IP and URL when done. The server bootstrap script takes 3–5 minutes to finish on first boot.

---

## Part 2: Understanding Docker and Containers

### What is Docker?

Think of Docker like a shipping container. A shipping container holds everything a product needs — packaging, instructions, all components — and works the same way on any ship, truck, or warehouse.

A Docker container holds everything a software application needs — the code, the libraries, the settings — and runs the same way on any computer.

### What is Docker Compose?

Docker Compose is like a recipe that says "I need container A, container B, and container C, and here is how they connect to each other."

We use a `docker-compose.yml` file to define each container's settings.

### Why Use Docker for n8n?

Without Docker, installing n8n requires installing Node.js, npm, and many packages — and things can break when versions change. With Docker, you just say "give me the official n8n container" and it works immediately.

---

## Part 3: n8n — The Workflow Engine

### What is n8n?

n8n is like a visual programming tool where you connect blocks together to automate tasks. Each block (called a **node**) does one specific thing:
- Receive an HTTP request
- Call an API
- Run some code
- Send an email
- Write to a spreadsheet

You connect these blocks with arrows and n8n runs them in order.

### How n8n is Deployed

n8n runs in a Docker container defined in `/opt/n8n/docker-compose.yml`:

```yaml
services:
  n8n:
    image: n8nio/n8n:latest      # Use the official n8n image
    container_name: n8n
    restart: unless-stopped      # Restart automatically if it crashes
    environment:
      - N8N_HOST=n8n.yourdomain.com
      - N8N_PORT=5678             # n8n listens on port 5678
      - N8N_PROTOCOL=https
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=yourpassword
      - N8N_TRUST_PROXY=true      # Trust Caddy as the proxy in front
      - GENERIC_TIMEZONE=Australia/Brisbane
    volumes:
      - /opt/n8n/data:/home/node/.n8n   # Save data on the host (not inside container)
    ports:
      - "5678:5678"               # Expose port 5678
```

**Important:** The `volumes` line is critical. It saves all your workflows, credentials, and settings to `/opt/n8n/data` on the physical server — NOT inside the container. This means:
- You can update n8n (replace the container) without losing your data
- Your data survives server restarts
- You can back up `/opt/n8n/data` to be safe

### Managing n8n

```bash
# SSH into the server
ssh -i ~/.ssh/test-web.pem ubuntu@YOUR_SERVER_IP

# Check n8n is running
sudo docker ps

# View n8n logs
sudo docker logs -f n8n

# Restart n8n
cd /opt/n8n && sudo docker compose restart

# Update n8n to latest version
cd /opt/n8n
sudo docker compose pull
sudo docker compose up -d
```

---

## Part 4: Caddy — The Secure Doorman

### What is Caddy?

Caddy is a web server that sits in front of n8n. It does two important things:

1. **HTTPS (SSL)** — Automatically gets a free security certificate from Let's Encrypt so your site uses `https://` instead of `http://`. It renews this certificate automatically before it expires.

2. **Reverse Proxy** — When someone visits `https://n8n.yourdomain.com`, Caddy receives the request and forwards it to n8n running on port 5678. The browser never talks to n8n directly.

### The Traffic Flow

```
Browser → port 443 (HTTPS) → Caddy → port 5678 (HTTP) → n8n
```

### Caddy Configuration

Caddy reads its settings from `/etc/caddy/Caddyfile`:

```
n8n.yourdomain.com {

    # Serve the basic chatbot page at /chatbot
    handle_path /chatbot* {
        root * /var/www/chatbot
        file_server
    }

    # Serve the agent chatbot page at /agent
    handle_path /agent* {
        root * /var/www/agent
        file_server
    }

    # CORS headers — allow browser requests from any origin
    handle {
        reverse_proxy localhost:5678 {
            header_down Access-Control-Allow-Origin *
            header_down Access-Control-Allow-Methods "POST, GET, OPTIONS"
            header_down Access-Control-Allow-Headers "Content-Type"
        }
    }

    encode gzip
}
```

Caddy runs as a system service (not Docker) and starts automatically on boot.

```bash
# Check Caddy status
sudo systemctl status caddy

# Reload after config changes (no downtime)
sudo systemctl reload caddy

# View Caddy logs
sudo journalctl -u caddy -f
```

---

## Part 5: SearXNG — The Self-Hosted Search Engine

### What is SearXNG?

SearXNG is a free, open-source search engine you run on your own server. It sends search queries to Google, Bing, and DuckDuckGo simultaneously and combines the results. Your server gets the results — not you directly — so search engines cannot track individual users.

### Why Run Your Own Search Engine?

| Commercial Search APIs | SearXNG (Self-hosted) |
|---|---|
| Requires API key | No key needed |
| Monthly cost or quota | Completely free |
| Rate limits | No limits |
| Data sent to third party | Stays on your server |

### Deploying SearXNG with Docker

Create the directory and config file:

```bash
sudo mkdir -p /opt/searxng
sudo chown ubuntu:ubuntu /opt/searxng
```

Create `/opt/searxng/settings.yml`:

```yaml
use_default_settings: true

server:
  secret_key: 'your-random-secret-key'
  bind_address: '0.0.0.0'
  port: 8080
  limiter: false          # Disable rate limiting (we control who accesses it)

search:
  safe_search: 0
  default_lang: 'en'
  formats:
    - html
    - json               # Must enable JSON format for API access

outgoing:
  request_timeout: 10.0
```

Create `/opt/searxng/docker-compose.yml`:

```yaml
services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    restart: unless-stopped
    ports:
      - "8080:8080"       # Bind to all interfaces (needed for n8n to reach it)
    volumes:
      - /opt/searxng/settings.yml:/etc/searxng/settings.yml:ro
    environment:
      - SEARXNG_SECRET=your-random-secret-key
```

Start SearXNG:

```bash
cd /opt/searxng && sudo docker compose up -d
```

### Testing SearXNG

```bash
# Test from the server command line
curl 'http://localhost:8080/search?q=hello&format=json'

# You should see JSON with a "results" array
```

### How n8n Connects to SearXNG

Both n8n and SearXNG run in Docker containers. They cannot use `localhost` to find each other because `localhost` inside a Docker container means the container itself.

Instead, we use the **Docker host gateway IP** — the IP address of the host machine as seen from inside the Docker network:

```bash
# Find the gateway IP
sudo docker inspect n8n --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}'
# Returns: 172.18.0.1
```

So inside n8n, the SearXNG URL is:
```
http://172.18.0.1:8080/search
```

---

## Part 6: The Tool-Calling Agent Workflow

### What is Tool Calling?

Tool calling is a feature of modern AI models where the LLM does not just generate text — it can also request that an external function be called on its behalf.

Think of it like this:
- **Without tools:** You ask a question → LLM answers from memory
- **With tools:** You ask a question → LLM decides if it needs help → LLM calls a tool → Tool returns data → LLM uses data to answer

### The Complete Workflow Architecture

```
Webhook (receives user question)
        ↓
Build First Request (Code node)
  - Gets today's date
  - Gets user's question
  - Builds the Groq API request with tool definitions
        ↓
Call Groq with Tools (HTTP Request)
  - Sends request to Groq API
  - Groq decides: answer directly OR call search tool
        ↓
Needs Search? (IF node)
  - Checks if finish_reason = "tool_calls"
  ↓ YES                    ↓ NO
Get Search Query     Respond Directly
(Code node)          (returns answer)
  ↓
Search SearXNG
(HTTP Request to SearXNG)
  ↓
Build Second Request (Code node)
  - Combines: original question + Groq's tool call + search results
  - Builds a new Groq API request
  ↓
Send Results to Groq (HTTP Request)
  - Groq reads search results and formulates final answer
  ↓
Respond with Search Answer
(returns answer with searched:true flag)
```

---

### Node-by-Node Configuration

#### Node 1: Webhook

This is the entry point. It listens for POST requests.

```
Type:          Webhook
HTTP Method:   POST
Path:          agent
Response Mode: Response Node (waits for the workflow to finish before responding)
```

This creates the URL: `https://n8n.yourdomain.com/webhook/agent`

---

#### Node 2: Build First Request (Code Node)

This JavaScript code runs in n8n and prepares the message to send to Groq.

```javascript
// Get today's date in readable format (e.g. "Saturday, 16 May 2026")
const today = new Date().toLocaleDateString('en-AU', {
  weekday: 'long',
  year: 'numeric',
  month: 'long',
  day: 'numeric'
});

// Get the user's question from the webhook
const userMessage = $('Webhook').item.json.body.message;

// Build the system prompt — tell the LLM who it is and what date it is
const systemPrompt = `You are a helpful assistant. Today's date is ${today}.
You have a search tool called search_internet to find current, real-time information.
Always use it for: current events, sports fixtures, news, prices, weather.
Use your own knowledge for timeless facts.`;

// Build the complete API request body
const body = JSON.stringify({
  model: 'qwen/qwen3-32b',

  // The conversation so far
  messages: [
    { role: 'system', content: systemPrompt },
    { role: 'user',   content: userMessage }
  ],

  // Tell the LLM what tools it has available
  tools: [{
    type: 'function',
    function: {
      name: 'search_internet',
      description: 'Search the internet for current, real-time information',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'The search query'
          }
        },
        required: ['query']
      }
    }
  }],

  // Let the LLM decide when to use tools
  tool_choice: 'auto'
});

return [{ json: { body, userMessage } }];
```

**What is the system prompt?**
The system prompt is like giving the LLM a briefing before the conversation. We use it to:
- Tell it today's date (it does not know this from training)
- Tell it what tools are available
- Tell it when to use search vs answer directly

**What are tools?**
The `tools` array is a list of functions the LLM can request to be called. Each tool has:
- `name` — what to call it
- `description` — when to use it (the LLM reads this to decide)
- `parameters` — what information the LLM needs to provide when calling it

---

#### Node 3: Call Groq with Tools (HTTP Request)

This sends our prepared request to the Groq API.

```
Method:       POST
URL:          https://api.groq.com/openai/v1/chat/completions
Headers:
  Authorization: Bearer YOUR_GROQ_API_KEY
  Content-Type:  application/json
Body:         ={{ $json.body }}    ← uses the body built in the Code node
```

**What does Groq return?**

If the LLM decides to answer directly:
```json
{
  "choices": [{
    "finish_reason": "stop",
    "message": {
      "content": "2 + 2 = 4"
    }
  }]
}
```

If the LLM decides to search:
```json
{
  "choices": [{
    "finish_reason": "tool_calls",
    "message": {
      "tool_calls": [{
        "id": "call_abc123",
        "function": {
          "name": "search_internet",
          "arguments": "{\"query\": \"Arsenal Premier League fixture May 2026\"}"
        }
      }]
    }
  }]
}
```

---

#### Node 4: Needs Search? (IF Node)

This is the decision gate. It checks the `finish_reason` field from Groq.

```
Condition:  choices[0].finish_reason  equals  "tool_calls"

TRUE branch  → go to "Get Search Query" (search is needed)
FALSE branch → go to "Respond Directly" (answer directly)
```

---

#### Node 5: Get Search Query (Code Node)

When search is needed, this extracts the query the LLM wants to search for.

```javascript
// Get the tool call from Groq's response
const toolCall = $input.item.json.choices[0].message.tool_calls[0];

// The arguments are a JSON string — parse them
const args = JSON.parse(toolCall.function.arguments);

// Return the query and the tool call ID (needed later)
return [{ json: { query: args.query, toolCallId: toolCall.id } }];
```

---

#### Node 6: Search SearXNG (HTTP Request)

This calls our self-hosted SearXNG with the query the LLM generated.

```
Method:  GET
URL:     http://172.18.0.1:8080/search

Query Parameters:
  q        = ={{ $json.query }}    ← the search query from the LLM
  format   = json
  language = en
```

SearXNG returns results like:
```json
{
  "results": [
    {
      "title": "Arsenal vs Burnley - Premier League",
      "url": "https://www.arsenal.com/fixtures",
      "content": "Arsenal face Burnley on Monday 18 May 2026..."
    },
    ...
  ]
}
```

---

#### Node 7: Build Second Request (Code Node)

Now we have search results. We need to send them back to Groq so it can formulate a final answer.

```javascript
const today = new Date().toLocaleDateString('en-AU', {
  weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
});

// Get original data
const userMessage  = $('Webhook').item.json.body.message;
const firstResponse = $('Call Groq with Tools').item.json;

// Get top 5 search results (trim to avoid sending too much text)
const searchResults = $input.item.json.results.slice(0, 5).map(r => ({
  title:   r.title,
  url:     r.url,
  content: r.content
}));

// Build the full conversation history including the tool call and results
const body = JSON.stringify({
  model: 'qwen/qwen3-32b',
  messages: [
    {
      role: 'system',
      content: `You are a helpful assistant. Today's date is ${today}.
      Use the search results to give an accurate, up-to-date answer.`
    },
    // Original user question
    { role: 'user', content: userMessage },

    // What the LLM said (that it wants to call a tool)
    {
      role: 'assistant',
      tool_calls: firstResponse.choices[0].message.tool_calls
    },

    // The search results (the "tool's response")
    {
      role: 'tool',
      tool_call_id: firstResponse.choices[0].message.tool_calls[0].id,
      content: JSON.stringify(searchResults)
    }
  ]
});

return [{ json: { body } }];
```

**Why send the conversation history?**
Groq needs the full context to know what happened:
1. The user asked a question
2. The LLM said "I want to search for X"
3. The search returned results Y
4. Now formulate the final answer

---

#### Node 8: Send Results to Groq (HTTP Request)

Same as Node 3 — sends the second request to Groq with the search results included.

```
Method:  POST
URL:     https://api.groq.com/openai/v1/chat/completions
Headers: same as before
Body:    ={{ $json.body }}
```

Groq reads the search results and returns a final, informed answer.

---

#### Nodes 9 and 10: Respond to Webhook

Two separate Respond nodes — one for each branch:

**Respond Directly** (no search branch):
```
Respond With: JSON
Response Body: ={{ JSON.stringify({
  output: $json.choices[0].message.content.replace(/<think>[\s\S]*?<\/think>/g, "").trim(),
  searched: false
}) }}
```

**Respond with Search Answer** (search branch):
```
Respond With: JSON
Response Body: ={{ JSON.stringify({
  output: $json.choices[0].message.content.replace(/<think>[\s\S]*?<\/think>/g, "").trim(),
  searched: true
}) }}
```

**Why strip `<think>` tags?**
The `qwen/qwen3-32b` model shows its reasoning process inside `<think>...</think>` tags. We use a regex to remove these before sending the response so users only see the final answer.

**Why include `searched: true/false`?**
This tells the frontend (chatbot page) whether to show a "Searched the internet" or "Answered from knowledge" badge.

---

## Part 7: The Chatbot Frontend

### What is the Frontend?

The frontend is a simple HTML page that provides a chat interface. It is a single HTML file served by Caddy as a static file.

### Key JavaScript Logic

```javascript
const WEBHOOK_URL = 'https://n8n.yourdomain.com/webhook/agent';

async function sendMessage() {
  const text = input.value.trim();

  // Send the user's message to the n8n webhook
  const res = await fetch(WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  });

  const rawText = await res.text();
  let data = JSON.parse(rawText);

  // Extract just the answer text
  const reply   = data.output.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
  const searched = data.searched;  // true or false

  // Display the answer (with a badge showing if web was searched)
  appendMessage(reply, 'bot', searched);
}
```

### Deploying the Frontend

```bash
# Upload the HTML file to the server
scp -i ~/.ssh/test-web.pem agent.html ubuntu@YOUR_SERVER_IP:/var/www/agent/index.html
```

Caddy serves it at `https://n8n.yourdomain.com/agent`.

---

## Part 8: How the Decision Process Works End to End

Here is the complete journey of a single question:

### Example 1: "what is 2 + 2?"

```
1. User types question in browser
2. Browser POST → https://n8n.yourdomain.com/webhook/agent
3. n8n Webhook node receives { "message": "what is 2 + 2?" }
4. Code node builds Groq request with tool definition
5. HTTP Request sends to Groq API
6. Groq thinks: "This is basic maths. No search needed."
7. Groq returns: finish_reason = "stop", content = "2 + 2 = 4"
8. IF node: finish_reason is NOT "tool_calls" → FALSE branch
9. Respond Directly node sends: { "output": "2 + 2 = 4", "searched": false }
10. Browser receives response, shows "Answered from knowledge" badge
```

### Example 2: "what is the latest news in Australia?"

```
1. User types question in browser
2. Browser POST → https://n8n.yourdomain.com/webhook/agent
3. n8n Webhook node receives the question
4. Code node builds Groq request with tool definition + today's date
5. HTTP Request sends to Groq API
6. Groq thinks: "This needs current information. I should search."
7. Groq returns: finish_reason = "tool_calls"
   tool_calls: [{ function: { name: "search_internet", arguments: '{"query":"latest Australia news May 2026"}' } }]
8. IF node: finish_reason IS "tool_calls" → TRUE branch
9. Code node extracts query: "latest Australia news May 2026"
10. HTTP Request calls SearXNG: http://172.18.0.1:8080/search?q=latest+Australia+news+May+2026&format=json
11. SearXNG searches Google, Bing, DuckDuckGo simultaneously
12. SearXNG returns list of news articles with titles and content
13. Code node builds second Groq request with the search results
14. HTTP Request sends results to Groq
15. Groq reads results and writes a summary answer
16. Respond with Search Answer sends: { "output": "Here are today's top stories...", "searched": true }
17. Browser receives response, shows "Searched the internet" badge
```

---

## Part 9: Managing Everything

### Useful Commands

```bash
# SSH into your server
ssh -i ~/.ssh/test-web.pem ubuntu@YOUR_SERVER_IP

# Check all running containers
sudo docker ps

# Check n8n logs
sudo docker logs -f n8n

# Check SearXNG logs
sudo docker logs -f searxng

# Restart n8n
cd /opt/n8n && sudo docker compose restart

# Restart SearXNG
cd /opt/searxng && sudo docker compose restart

# Check disk usage
df -h

# Check memory usage
free -h
```

### Cost Summary

| Resource | Monthly Cost |
|---|---|
| EC2 t4g.small | ~$14 AUD |
| EBS 20GB storage | ~$2 AUD |
| Route 53 DNS | ~$0.75 AUD |
| Data transfer | ~$1–2 AUD |
| Groq API (free tier) | $0 |
| SearXNG | $0 |
| **Total** | **~$18–20 AUD/month** |

### Security Checklist

- SSH access restricted to your home IP only
- HTTPS enforced with auto-renewing certificate (Caddy + Let's Encrypt)
- n8n protected with username and password
- EBS volume encrypted at rest
- IMDSv2 enforced (prevents SSRF attacks)
- UFW firewall enabled (only ports 22, 80, 443 open)
- SearXNG not exposed to the internet (only accessible internally)
- Automatic OS security updates enabled

---

## Summary: What You Have Built

```
Internet → Route 53 DNS → Elastic IP → EC2 t4g.small
                                              │
                              ┌───────────────┤
                              │               │
                           Caddy          Security
                        (HTTPS proxy)     Group
                              │
                 ┌────────────┼────────────┐
                 │            │            │
            /chatbot      n8n :5678    /agent
           (basic LLM)   (workflows)  (tool agent)
                              │
                 ┌────────────┘
                 │
            SearXNG :8080
          (self-hosted search)
                 │
          Google/Bing/DDG
```

**What the agent can do:**
- Answer general knowledge questions from its training data
- Search the internet in real time for current information
- Decide automatically which approach each question needs
- Show you whether it searched or answered from knowledge

**What makes this different from just using ChatGPT:**
- You own all the data and infrastructure
- No per-message costs for web search
- Unlimited search queries
- Fully customisable — you control every part of the pipeline
- Educational — you can see exactly how tool calling works inside n8n
