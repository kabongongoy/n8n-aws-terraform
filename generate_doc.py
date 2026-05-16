from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import re

doc = Document()

# ── Page margins ──────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin   = Cm(3)
    section.right_margin  = Cm(2.5)

# ── Colour palette ────────────────────────────────────────────────────────────
TEAL   = RGBColor(0x0f, 0x76, 0x6e)
DARK   = RGBColor(0x1e, 0x29, 0x3b)
GREY   = RGBColor(0x64, 0x74, 0x8b)
CODE_BG = RGBColor(0xf1, 0xf5, 0xf9)

# ── Helper: shade a paragraph ─────────────────────────────────────────────────
def shade_paragraph(para, rgb):
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), '{:02X}{:02X}{:02X}'.format(*rgb))
    pPr.append(shd)

# ── Helper: horizontal rule ───────────────────────────────────────────────────
def add_rule(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '0f766e')
    pBdr.append(bottom)
    pPr.append(pBdr)
    p.paragraph_format.space_after = Pt(6)

# ── Cover page ────────────────────────────────────────────────────────────────
cover = doc.add_paragraph()
cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = cover.add_run('\n\n')

title_p = doc.add_paragraph()
title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title_p.add_run('Building an AI Agent with Internet Search on AWS')
r.font.size = Pt(26)
r.font.bold = True
r.font.color.rgb = TEAL

sub_p = doc.add_paragraph()
sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = sub_p.add_run('End-to-End Step-by-Step Documentation')
r2.font.size = Pt(14)
r2.font.color.rgb = GREY

doc.add_paragraph('\n')

tagline = doc.add_paragraph()
tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
r3 = tagline.add_run(
    'From AWS EC2 deployment to Docker containers,\n'
    'n8n workflows, SearXNG self-hosted search,\n'
    'and building a fully autonomous AI agent with tool calling.'
)
r3.font.size = Pt(12)
r3.font.italic = True
r3.font.color.rgb = GREY

doc.add_page_break()

# ── Utility functions ─────────────────────────────────────────────────────────
def add_h1(text):
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after  = Pt(6)
    run = p.add_run(text)
    run.font.size  = Pt(20)
    run.font.bold  = True
    run.font.color.rgb = TEAL
    add_rule(doc)

def add_h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run(text)
    run.font.size  = Pt(15)
    run.font.bold  = True
    run.font.color.rgb = DARK

def add_h3(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after  = Pt(3)
    run = p.add_run(text)
    run.font.size  = Pt(12)
    run.font.bold  = True
    run.font.color.rgb = TEAL

def add_body(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.color.rgb = DARK

def add_bullet(text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent  = Cm(1 + level * 0.5)
    p.paragraph_format.space_after  = Pt(3)
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.color.rgb = DARK

def add_code(text):
    lines = text.strip().split('\n')
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
        p.paragraph_format.left_indent  = Cm(0.5)
        p.paragraph_format.right_indent = Cm(0.5)
        shade_paragraph(p, (241, 245, 249))
        run = p.add_run(line if line else ' ')
        run.font.name  = 'Courier New'
        run.font.size  = Pt(9)
        run.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def add_note(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Cm(0.5)
    p.paragraph_format.space_after  = Pt(6)
    shade_paragraph(p, (254, 252, 232))
    run = p.add_run('Note: ' + text)
    run.font.size   = Pt(10)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x92, 0x40, 0x0e)

# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

add_h1('What Are We Building?')
add_body(
    'We are building a smart AI assistant that runs entirely on your own server. '
    'It can answer questions from its own knowledge (like a textbook) and search '
    'the internet automatically when it needs fresh information (like a researcher). '
    'It runs 24 hours a day, 7 days a week, without paying for expensive third-party search APIs.'
)

add_h2('The Big Picture')
add_body('Everything runs inside Docker containers on a single AWS EC2 server:')
add_code(
    'Your Browser\n'
    '     │  HTTPS (secure connection)\n'
    '     ▼\n'
    'Caddy (the doorman — handles HTTPS)\n'
    '     │\n'
    '     ├──► n8n (the brain — runs your workflows)\n'
    '     │         │\n'
    '     │         ├──► Groq API (the LLM — thinks and decides)\n'
    '     │         └──► SearXNG (self-hosted search engine)\n'
    '     │\n'
    '     └──► Your Chatbot Pages (/chatbot and /agent)'
)

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Part 1: The Server — AWS EC2 with Terraform')

add_h2('What is AWS EC2?')
add_body(
    'AWS EC2 is like renting a computer in Amazon\'s data centre. Instead of buying '
    'a physical computer, you pay a small monthly fee and get a virtual computer '
    'running 24/7 in the cloud.'
)

add_h2('What is Terraform?')
add_body(
    'Terraform is a tool that lets you describe your server setup in a text file '
    'and automatically creates everything for you. Instead of clicking through AWS '
    'menus, you write instructions and Terraform does the work.'
)

add_h2('What Server Did We Choose?')
add_body('We chose a t4g.small instance because it is cost-effective and powerful enough:')
add_bullet('2 CPU cores')
add_bullet('2 GB of RAM')
add_bullet('ARM64 chip (same technology as Apple Silicon — 20% cheaper than x86)')
add_bullet('Approximately $14 AUD per month')

add_h2('Step 1.1 — Install the Required Tools')
add_body('Install these on your Windows computer before starting:')
add_bullet('Terraform — download from https://developer.hashicorp.com/terraform/install')
add_bullet('AWS CLI — download from https://aws.amazon.com/cli/')
add_body('Then configure your AWS credentials:')
add_code('aws configure\n# Enter: Access Key, Secret Key, Region (ap-southeast-2), Output (json)')

add_h2('Step 1.2 — Create the Terraform Files')
add_body('Create a folder called n8n-aws and create these five files inside it.')

add_h3('File 1: variables.tf — The Settings Descriptions')
add_body(
    'This file defines what settings the setup needs. Think of it as a form with '
    'blank fields — you fill in the actual values in terraform.tfvars.'
)
add_code(
    'variable "aws_region" {\n'
    '  description = "AWS region to deploy into"\n'
    '  type        = string\n'
    '  default     = "ap-southeast-2"\n'
    '}\n'
    '\n'
    'variable "instance_type" {\n'
    '  description = "EC2 instance type"\n'
    '  type        = string\n'
    '  default     = "t4g.small"\n'
    '}\n'
    '\n'
    'variable "key_name" {\n'
    '  description = "Name of your EC2 Key Pair for SSH access"\n'
    '  type        = string\n'
    '}\n'
    '\n'
    'variable "domain_name" {\n'
    '  description = "Your domain for n8n, e.g. n8n.yourdomain.com"\n'
    '  type        = string\n'
    '}\n'
    '\n'
    'variable "route53_zone_id" {\n'
    '  description = "Route 53 Hosted Zone ID"\n'
    '  type        = string\n'
    '}\n'
    '\n'
    'variable "n8n_basic_auth_user" {\n'
    '  default     = "admin"\n'
    '  type        = string\n'
    '}\n'
    '\n'
    'variable "n8n_basic_auth_password" {\n'
    '  type        = string\n'
    '  sensitive   = true\n'
    '}\n'
    '\n'
    'variable "your_home_ip" {\n'
    '  description = "Your home IP address (e.g. 1.2.3.4/32)"\n'
    '  type        = string\n'
    '}'
)

add_h3('File 2: terraform.tfvars — Your Actual Values')
add_body('Fill in this file with your real values:')
add_code(
    'aws_region              = "ap-southeast-2"\n'
    'instance_type           = "t4g.small"\n'
    'key_name                = "your-keypair-name"\n'
    'domain_name             = "n8n.yourdomain.com"\n'
    'route53_zone_id         = "ZXXXXXXXXXXXXXXXXXXXX"\n'
    'n8n_basic_auth_user     = "admin"\n'
    'n8n_basic_auth_password = "your-strong-password"\n'
    'your_home_ip            = "1.2.3.4/32"'
)
add_note('Never commit this file to Git — it contains your password. It is already in .gitignore.')
add_body('Find your values with these commands:')
add_code(
    '# Find your Route 53 Zone ID\n'
    'aws route53 list-hosted-zones --query "HostedZones[*].[Name,Id]" --output table\n'
    '\n'
    '# Find your home IP\n'
    'curl https://checkip.amazonaws.com'
)

add_h3('File 3: main.tf — The Infrastructure Blueprint')
add_body(
    'This is the main Terraform file. It creates the VPC (private network), '
    'subnet, internet gateway, security group (firewall), EC2 instance, '
    'elastic IP, Route 53 DNS record, and CloudWatch alarm.'
)
add_body('Key resources explained:')
add_bullet('aws_vpc — creates a private network for your server (10.10.0.0/16)')
add_bullet('aws_subnet — a public subnet inside the VPC where the server lives')
add_bullet('aws_internet_gateway — the door connecting your network to the internet')
add_bullet('aws_security_group — firewall rules (only allows SSH from your IP, HTTP, HTTPS)')
add_bullet('aws_instance — the actual EC2 virtual machine')
add_bullet('aws_eip — a static IP address that never changes')
add_bullet('aws_route53_record — points your domain name to the static IP')

add_h3('File 4: user_data.sh — The Bootstrap Script')
add_body(
    'This shell script runs automatically the very first time the server boots. '
    'It installs and configures everything:'
)
add_bullet('Updates the operating system')
add_bullet('Installs Docker and Docker Compose')
add_bullet('Installs Caddy (the reverse proxy)')
add_bullet('Creates the n8n data directory (/opt/n8n/data)')
add_bullet('Creates the Docker Compose file for n8n')
add_bullet('Starts n8n as a Docker container')
add_bullet('Configures Caddy with HTTPS and routing rules')
add_bullet('Enables the UFW firewall')
add_bullet('Enables automatic security updates')

add_h2('Step 1.3 — Deploy')
add_code(
    '# Download the AWS provider plugin\n'
    'terraform init\n'
    '\n'
    '# Preview what will be created (nothing happens yet)\n'
    'terraform plan\n'
    '\n'
    '# Create everything (type yes when asked)\n'
    'terraform apply'
)
add_body(
    'Terraform creates 10 AWS resources and outputs your server IP, n8n URL, '
    'and SSH command. The bootstrap script takes 3–5 minutes to finish on first boot.'
)

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Part 2: Docker and Containers')

add_h2('What is Docker?')
add_body(
    'Think of Docker like a shipping container. A shipping container holds '
    'everything a product needs and works the same way on any ship, truck, or '
    'warehouse. A Docker container holds everything a software application needs '
    'and runs the same way on any computer.'
)

add_h2('What is Docker Compose?')
add_body(
    'Docker Compose is like a recipe. You write a docker-compose.yml file that '
    'says "I need container A with these settings, and container B with these '
    'settings, and they connect like this." One command starts everything.'
)

add_h2('Why Use Docker?')
add_body(
    'Without Docker you would need to manually install Node.js, npm, and many '
    'packages — and things can break when versions change. With Docker you say '
    '"give me the official n8n container" and it works immediately.'
)

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Part 3: n8n — The Workflow Engine')

add_h2('What is n8n?')
add_body(
    'n8n is a visual workflow automation tool. You connect blocks (called nodes) '
    'together to automate tasks. Each node does one specific thing: receive an '
    'HTTP request, call an API, run code, send an email, write to a spreadsheet, etc.'
)

add_h2('How n8n is Deployed')
add_body('n8n runs in Docker, defined in /opt/n8n/docker-compose.yml:')
add_code(
    'services:\n'
    '  n8n:\n'
    '    image: n8nio/n8n:latest\n'
    '    container_name: n8n\n'
    '    restart: unless-stopped      # Restart if it crashes\n'
    '    environment:\n'
    '      - N8N_HOST=n8n.yourdomain.com\n'
    '      - N8N_PORT=5678\n'
    '      - N8N_PROTOCOL=https\n'
    '      - N8N_BASIC_AUTH_ACTIVE=true\n'
    '      - N8N_BASIC_AUTH_USER=admin\n'
    '      - N8N_BASIC_AUTH_PASSWORD=yourpassword\n'
    '      - N8N_TRUST_PROXY=true\n'
    '      - GENERIC_TIMEZONE=Australia/Brisbane\n'
    '    volumes:\n'
    '      - /opt/n8n/data:/home/node/.n8n   # Data saved on host\n'
    '    ports:\n'
    '      - "5678:5678"'
)
add_note(
    'The volumes line saves all workflows and credentials to /opt/n8n/data on '
    'the physical server — not inside the container. This means you can update '
    'n8n without losing your data.'
)

add_h2('Managing n8n')
add_code(
    '# SSH into the server\n'
    'ssh -i ~/.ssh/test-web.pem ubuntu@YOUR_SERVER_IP\n'
    '\n'
    '# Check n8n is running\n'
    'sudo docker ps\n'
    '\n'
    '# View logs\n'
    'sudo docker logs -f n8n\n'
    '\n'
    '# Restart n8n\n'
    'cd /opt/n8n && sudo docker compose restart\n'
    '\n'
    '# Update to latest version\n'
    'cd /opt/n8n && sudo docker compose pull && sudo docker compose up -d'
)

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Part 4: Caddy — The Secure Doorman')

add_h2('What is Caddy?')
add_body(
    'Caddy is a web server that sits in front of n8n and does two things:'
)
add_bullet(
    'HTTPS (SSL) — Automatically gets a free security certificate from '
    'Let\'s Encrypt so your site uses https:// instead of http://. '
    'It renews the certificate automatically before it expires.'
)
add_bullet(
    'Reverse Proxy — When someone visits your domain, Caddy forwards '
    'the request to n8n running on port 5678. The browser never talks '
    'to n8n directly.'
)

add_h2('Traffic Flow')
add_code('Browser → port 443 (HTTPS) → Caddy → port 5678 (HTTP) → n8n')

add_h2('Caddy Configuration (/etc/caddy/Caddyfile)')
add_code(
    'n8n.yourdomain.com {\n'
    '\n'
    '    # Serve the basic chatbot page at /chatbot\n'
    '    handle_path /chatbot* {\n'
    '        root * /var/www/chatbot\n'
    '        file_server\n'
    '    }\n'
    '\n'
    '    # Serve the agent chatbot page at /agent\n'
    '    handle_path /agent* {\n'
    '        root * /var/www/agent\n'
    '        file_server\n'
    '    }\n'
    '\n'
    '    # Handle CORS preflight requests\n'
    '    @options method OPTIONS\n'
    '    handle @options {\n'
    '        header Access-Control-Allow-Origin *\n'
    '        respond 204\n'
    '    }\n'
    '\n'
    '    # Forward everything else to n8n\n'
    '    handle {\n'
    '        reverse_proxy localhost:5678 {\n'
    '            header_down Access-Control-Allow-Origin *\n'
    '        }\n'
    '    }\n'
    '\n'
    '    encode gzip\n'
    '}'
)
add_code(
    '# Check Caddy status\n'
    'sudo systemctl status caddy\n'
    '\n'
    '# Reload after config changes (no downtime)\n'
    'sudo systemctl reload caddy'
)

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Part 5: SearXNG — The Self-Hosted Search Engine')

add_h2('What is SearXNG?')
add_body(
    'SearXNG is a free, open-source search engine you run on your own server. '
    'It sends search queries to Google, Bing, and DuckDuckGo simultaneously '
    'and combines the results. No API key required. No cost. No rate limits.'
)

add_h2('Why Run Your Own Search Engine?')
add_body('Comparison:')
table = doc.add_table(rows=4, cols=2)
table.style = 'Table Grid'
headers = ['Commercial Search APIs', 'SearXNG (Self-hosted)']
rows_data = [
    ('Requires API key', 'No key needed'),
    ('Monthly cost or quota limits', 'Completely free, no limits'),
    ('Data sent to third party', 'Stays on your server'),
]
for i, h in enumerate(headers):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].font.bold = True
for i, (a, b) in enumerate(rows_data):
    table.rows[i+1].cells[0].text = a
    table.rows[i+1].cells[1].text = b
doc.add_paragraph()

add_h2('Deploying SearXNG with Docker')
add_body('Step 1: Create the directory and configuration file:')
add_code(
    'sudo mkdir -p /opt/searxng\n'
    'sudo chown ubuntu:ubuntu /opt/searxng'
)
add_body('Step 2: Create /opt/searxng/settings.yml:')
add_code(
    'use_default_settings: true\n'
    'server:\n'
    '  secret_key: "your-random-secret-key"\n'
    '  bind_address: "0.0.0.0"\n'
    '  port: 8080\n'
    '  limiter: false\n'
    'search:\n'
    '  safe_search: 0\n'
    '  default_lang: "en"\n'
    '  formats:\n'
    '    - html\n'
    '    - json          # Must enable JSON for API access\n'
    'outgoing:\n'
    '  request_timeout: 10.0'
)
add_body('Step 3: Create /opt/searxng/docker-compose.yml:')
add_code(
    'services:\n'
    '  searxng:\n'
    '    image: searxng/searxng:latest\n'
    '    container_name: searxng\n'
    '    restart: unless-stopped\n'
    '    ports:\n'
    '      - "8080:8080"   # Bind to all interfaces\n'
    '    volumes:\n'
    '      - /opt/searxng/settings.yml:/etc/searxng/settings.yml:ro\n'
    '    environment:\n'
    '      - SEARXNG_SECRET=your-random-secret-key'
)
add_body('Step 4: Start SearXNG:')
add_code('cd /opt/searxng && sudo docker compose up -d')
add_body('Step 5: Test it works:')
add_code("curl 'http://localhost:8080/search?q=hello&format=json'")

add_h2('How n8n Connects to SearXNG')
add_body(
    'Both containers run in Docker. They cannot use "localhost" to find each other '
    'because localhost inside a Docker container refers to the container itself, '
    'not the host machine.'
)
add_body('We use the Docker host gateway IP instead:')
add_code(
    '# Find the gateway IP\n'
    'sudo docker inspect n8n --format "{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}"\n'
    '# Returns: 172.18.0.1'
)
add_body('So inside n8n, the SearXNG URL is:')
add_code('http://172.18.0.1:8080/search')

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Part 6: The Tool-Calling Agent Workflow')

add_h2('What is Tool Calling?')
add_body(
    'Tool calling is a feature of modern AI models where the LLM does not just '
    'generate text — it can request that an external function be called on its behalf.'
)
add_body('The difference:')
add_bullet('Without tools: You ask → LLM answers from memory')
add_bullet('With tools: You ask → LLM decides if it needs help → LLM calls a tool → Tool returns data → LLM uses data to answer')

add_h2('Complete Workflow Architecture')
add_code(
    'Webhook (receives user question)\n'
    '        ↓\n'
    'Build First Request (Code node)\n'
    '  - Gets today\'s date\n'
    '  - Builds Groq API request with tool definitions\n'
    '        ↓\n'
    'Call Groq with Tools (HTTP Request)\n'
    '  - Groq decides: answer directly OR call search tool\n'
    '        ↓\n'
    'Needs Search? (IF node)\n'
    '  - Checks finish_reason = "tool_calls"\n'
    '  ↓ YES                        ↓ NO\n'
    'Get Search Query          Respond Directly\n'
    '(Code node)               (return answer)\n'
    '  ↓\n'
    'Search SearXNG\n'
    '(HTTP Request)\n'
    '  ↓\n'
    'Build Second Request (Code node)\n'
    '  - Combines question + tool call + results\n'
    '  ↓\n'
    'Send Results to Groq (HTTP Request)\n'
    '  ↓\n'
    'Respond with Search Answer'
)

add_h2('Node-by-Node Configuration')

add_h3('Node 1: Webhook')
add_body('The entry point. Listens for POST requests from the chatbot page.')
add_code(
    'Type:          Webhook\n'
    'HTTP Method:   POST\n'
    'Path:          agent\n'
    'Response Mode: Response Node\n'
    '\n'
    'Creates the URL: https://n8n.yourdomain.com/webhook/agent'
)

add_h3('Node 2: Build First Request (Code Node)')
add_body(
    'JavaScript code that prepares the message to send to Groq. '
    'It injects today\'s date into the system prompt and includes the tool definition.'
)
add_code(
    'const today = new Date().toLocaleDateString("en-AU", {\n'
    '  weekday: "long", year: "numeric", month: "long", day: "numeric"\n'
    '});\n'
    '\n'
    'const userMessage = $(\'Webhook\').item.json.body.message;\n'
    '\n'
    'const systemPrompt = `You are a helpful assistant. Today\'s date is ${today}.\n'
    'Use search_internet for current events, sports, news, prices, weather.\n'
    'Use your own knowledge for timeless facts.`;\n'
    '\n'
    'const body = JSON.stringify({\n'
    '  model: "qwen/qwen3-32b",\n'
    '  messages: [\n'
    '    { role: "system", content: systemPrompt },\n'
    '    { role: "user",   content: userMessage }\n'
    '  ],\n'
    '  tools: [{\n'
    '    type: "function",\n'
    '    function: {\n'
    '      name: "search_internet",\n'
    '      description: "Search the internet for current, real-time information",\n'
    '      parameters: {\n'
    '        type: "object",\n'
    '        properties: { query: { type: "string" } },\n'
    '        required: ["query"]\n'
    '      }\n'
    '    }\n'
    '  }],\n'
    '  tool_choice: "auto"\n'
    '});\n'
    '\n'
    'return [{ json: { body, userMessage } }];'
)
add_note(
    'We inject today\'s date because the LLM\'s training data has a cutoff date '
    'and it genuinely does not know the current date unless we tell it.'
)

add_h3('Node 3: Call Groq with Tools (HTTP Request)')
add_body('Sends our prepared request to the Groq API.')
add_code(
    'Method:  POST\n'
    'URL:     https://api.groq.com/openai/v1/chat/completions\n'
    'Headers:\n'
    '  Authorization: Bearer YOUR_GROQ_API_KEY\n'
    '  Content-Type:  application/json\n'
    'Body:    ={{ $json.body }}'
)
add_body('Groq returns one of two response formats:')
add_body('If the LLM answers directly (finish_reason = "stop"):')
add_code(
    '{\n'
    '  "choices": [{\n'
    '    "finish_reason": "stop",\n'
    '    "message": { "content": "2 + 2 = 4" }\n'
    '  }]\n'
    '}'
)
add_body('If the LLM wants to search (finish_reason = "tool_calls"):')
add_code(
    '{\n'
    '  "choices": [{\n'
    '    "finish_reason": "tool_calls",\n'
    '    "message": {\n'
    '      "tool_calls": [{\n'
    '        "id": "call_abc123",\n'
    '        "function": {\n'
    '          "name": "search_internet",\n'
    '          "arguments": "{\\"query\\": \\"Arsenal fixture May 2026\\"}"\n'
    '        }\n'
    '      }]\n'
    '    }\n'
    '  }]\n'
    '}'
)

add_h3('Node 4: Needs Search? (IF Node)')
add_body('The decision gate that splits the workflow into two paths.')
add_code(
    'Condition:  choices[0].finish_reason  equals  "tool_calls"\n'
    '\n'
    'TRUE  → go to Get Search Query (search needed)\n'
    'FALSE → go to Respond Directly (answer directly)'
)

add_h3('Node 5: Get Search Query (Code Node)')
add_body('Extracts the search query that the LLM generated.')
add_code(
    'const toolCall = $input.item.json.choices[0].message.tool_calls[0];\n'
    'const args = JSON.parse(toolCall.function.arguments);\n'
    'return [{ json: { query: args.query, toolCallId: toolCall.id } }];'
)

add_h3('Node 6: Search SearXNG (HTTP Request)')
add_body('Calls our self-hosted SearXNG with the query the LLM generated.')
add_code(
    'Method:  GET\n'
    'URL:     http://172.18.0.1:8080/search\n'
    'Params:\n'
    '  q        = ={{ $json.query }}\n'
    '  format   = json\n'
    '  language = en'
)

add_h3('Node 7: Build Second Request (Code Node)')
add_body(
    'Builds the second Groq request that includes the original question, '
    'the tool call, and the search results.'
)
add_code(
    'const userMessage   = $(\'Webhook\').item.json.body.message;\n'
    'const firstResponse = $(\'Call Groq with Tools\').item.json;\n'
    'const searchResults = $input.item.json.results.slice(0, 5).map(r => ({\n'
    '  title: r.title, url: r.url, content: r.content\n'
    '}));\n'
    '\n'
    'const body = JSON.stringify({\n'
    '  model: "qwen/qwen3-32b",\n'
    '  messages: [\n'
    '    { role: "system",    content: systemPrompt },\n'
    '    { role: "user",      content: userMessage },\n'
    '    { role: "assistant", tool_calls: firstResponse.choices[0].message.tool_calls },\n'
    '    {\n'
    '      role: "tool",\n'
    '      tool_call_id: firstResponse.choices[0].message.tool_calls[0].id,\n'
    '      content: JSON.stringify(searchResults)\n'
    '    }\n'
    '  ]\n'
    '});\n'
    '\n'
    'return [{ json: { body } }];'
)
add_note(
    'We send the full conversation history so Groq knows what happened: '
    'the user asked, the LLM requested a search, the search returned results, '
    'now formulate the final answer.'
)

add_h3('Nodes 8 and 9: Respond to Webhook')
add_body('Two respond nodes — one for each path. Both strip the <think> reasoning tags.')
add_code(
    '# Respond Directly (no search)\n'
    'respondWith: json\n'
    'responseBody: ={{ JSON.stringify({\n'
    '  output: $json.choices[0].message.content\n'
    '          .replace(/<think>[\\s\\S]*?<\\/think>/g, "").trim(),\n'
    '  searched: false\n'
    '}) }}\n'
    '\n'
    '# Respond with Search Answer\n'
    'responseBody: same but searched: true'
)
add_note(
    'The <think> tags contain the model\'s internal reasoning process. '
    'We strip them so users only see the final answer.'
)

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Part 7: Content Guardrails')
add_body(
    'Three layers of protection are in place to prevent inappropriate, explicit, '
    'or illicit content from being searched or returned to users.'
)

add_h2('Layer 1 — SearXNG Strict Safe Search')
add_body(
    'SearXNG passes a safe search flag to Google, Bing, and DuckDuckGo so they '
    'filter explicit results before sending them back. Set in /opt/searxng/settings.yml:'
)
add_code(
    'search:\n'
    '  safe_search: 2    # 0 = off,  1 = moderate,  2 = strict'
)
add_body('Restart SearXNG after changing this setting:')
add_code('cd /opt/searxng && sudo docker compose restart')

add_h2('Layer 2 — LLM System Prompt Guardrail')
add_body(
    'The system prompt instructs the LLM to refuse inappropriate requests '
    'before they ever reach the search stage:'
)
add_code(
    'IMPORTANT SAFETY RULES: You must immediately refuse any request that\n'
    'involves pornographic content, explicit sexual material, illegal\n'
    'activities, drug procurement, weapons, hate speech, or self-harm.\n'
    'Do NOT search for such content under any circumstances.'
)
add_note(
    'This is the first line of defence. If the user asks for inappropriate '
    'content, the LLM refuses without ever calling the search tool.'
)

add_h2('Layer 3 — Query Filter Code Node')
add_body(
    'Even if the LLM somehow generates a problematic query, a dedicated '
    '"Filter Query" Code node checks it against a blocklist before it '
    'reaches SearXNG:'
)
add_code(
    'const blocklist = [\n'
    '  "porn", "pornography", "xxx", "nude", "naked", "sex video",\n'
    '  "explicit", "onlyfans", "escort", "how to make drugs", "buy drugs",\n'
    '  "how to kill", "bomb making", "dark web", "csam"\n'
    '];\n'
    '\n'
    'const blocked = blocklist.some(word => query.includes(word));\n'
    '\n'
    'if (blocked) {\n'
    '  return [{ json: {\n'
    '    blocked: true,\n'
    '    refusal: "I\'m sorry, I cannot search for that type of content."\n'
    '  }}];\n'
    '}\n'
    'return [{ json: { blocked: false, query: query } }];'
)

add_h2('Updated Workflow with Guardrails')
add_code(
    'Get Search Query\n'
    '      ↓\n'
    'Filter Query  ← checks blocklist\n'
    '      ↓\n'
    'Is Blocked?\n'
    '  ↓ YES              ↓ NO\n'
    'Build Refusal    Search SearXNG (safe_search = 2)\n'
    '  ↓                  ↓\n'
    'Respond Refused  Build Second Request → Groq → Respond'
)

add_h2('How to Add More Blocked Keywords')
add_body(
    'Open the "Filter Query" node in n8n and add words to the blocklist array. '
    'Save and Publish the workflow — no server restart needed.'
)
add_note(
    'All three layers work together. Layer 2 (LLM prompt) catches most cases. '
    'Layer 3 (blocklist) is a safety net if the LLM misses something. '
    'Layer 1 (SearXNG) filters results at the search engine level.'
)

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Part 8: How the Decision Process Works')

add_h2('Example 1: A Simple Maths Question')
add_code(
    '1. User types: "what is 2 + 2?"\n'
    '2. n8n sends to Groq with tool definition\n'
    '3. Groq thinks: "Basic maths — no search needed"\n'
    '4. Groq returns: finish_reason = "stop"\n'
    '5. IF node → FALSE branch → Respond Directly\n'
    '6. Response: { "output": "2 + 2 = 4", "searched": false }\n'
    '7. Chatbot shows: purple "Answered from knowledge" badge'
)

add_h2('Example 2: A Current Events Question')
add_code(
    '1. User types: "what is the latest news in Australia?"\n'
    '2. n8n sends to Groq with today\'s date + tool definition\n'
    '3. Groq thinks: "This needs current info — I should search"\n'
    '4. Groq returns: finish_reason = "tool_calls"\n'
    '   query: "latest Australia news May 2026"\n'
    '5. IF node → TRUE branch → SearXNG is called\n'
    '6. SearXNG searches Google, Bing, DuckDuckGo\n'
    '7. Results sent back to Groq\n'
    '8. Groq writes a summary using real results\n'
    '9. Response: { "output": "Here are today\'s stories...", "searched": true }\n'
    '10. Chatbot shows: green "Searched the internet" badge'
)

add_h2('What the LLM Uses to Decide')
add_body('The model reads two things to decide whether to search:')
add_bullet(
    'The tool description — we wrote "Search the internet for current, '
    'real-time information". The words real-time signal it is for fresh data only.'
)
add_bullet(
    'The system prompt — we wrote "Use it for recent events, sports, news, '
    'prices, weather. Use your own knowledge for timeless facts."'
)

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Part 8: Management and Costs')

add_h2('Useful Commands')
add_code(
    '# Check all running containers\n'
    'sudo docker ps\n'
    '\n'
    '# View n8n logs\n'
    'sudo docker logs -f n8n\n'
    '\n'
    '# View SearXNG logs\n'
    'sudo docker logs -f searxng\n'
    '\n'
    '# Restart n8n\n'
    'cd /opt/n8n && sudo docker compose restart\n'
    '\n'
    '# Restart SearXNG\n'
    'cd /opt/searxng && sudo docker compose restart\n'
    '\n'
    '# Check disk usage\n'
    'df -h\n'
    '\n'
    '# Check memory usage\n'
    'free -h'
)

add_h2('Monthly Cost Summary')
table2 = doc.add_table(rows=6, cols=2)
table2.style = 'Table Grid'
cost_data = [
    ('Resource', 'Monthly Cost'),
    ('EC2 t4g.small', '~$14 AUD'),
    ('EBS 20GB storage', '~$2 AUD'),
    ('Route 53 DNS', '~$0.75 AUD'),
    ('SearXNG + Groq (free tier)', '$0'),
    ('Total', '~$18–20 AUD/month'),
]
for i, (a, b) in enumerate(cost_data):
    table2.rows[i].cells[0].text = a
    table2.rows[i].cells[1].text = b
    if i == 0 or i == 5:
        for cell in table2.rows[i].cells:
            cell.paragraphs[0].runs[0].font.bold = True
doc.add_paragraph()

add_h2('Security Checklist')
add_bullet('SSH access restricted to your home IP only')
add_bullet('HTTPS enforced with auto-renewing certificate via Caddy + Let\'s Encrypt')
add_bullet('n8n protected with username and password')
add_bullet('EBS volume encrypted at rest')
add_bullet('IMDSv2 enforced on the EC2 instance')
add_bullet('UFW firewall — only ports 22, 80, 443 open')
add_bullet('SearXNG not exposed to the internet — only accessible internally')
add_bullet('Automatic OS security updates enabled')

# ───────────────────────────────────────────────────────────────────────────────
add_h1('Summary: What You Have Built')
add_code(
    'Internet → Route 53 DNS → Elastic IP → EC2 t4g.small\n'
    '                                              │\n'
    '                              ┌───────────────┤\n'
    '                              │               │\n'
    '                           Caddy          Security\n'
    '                        (HTTPS proxy)     Group\n'
    '                              │\n'
    '                 ┌────────────┼────────────┐\n'
    '                 │            │            │\n'
    '            /chatbot      n8n :5678    /agent\n'
    '           (basic LLM)   (workflows)  (tool agent)\n'
    '                              │\n'
    '                 ┌────────────┘\n'
    '                 │\n'
    '            SearXNG :8080\n'
    '          (self-hosted search)\n'
    '                 │\n'
    '          Google/Bing/DuckDuckGo'
)

add_h2('What Makes This Different from Using ChatGPT')
add_bullet('You own all the data and infrastructure')
add_bullet('No per-message costs for web search — SearXNG is free and unlimited')
add_bullet('Fully customisable — you control every part of the pipeline')
add_bullet('Educational — you can see exactly how tool calling works inside n8n')
add_bullet('Reusable — any n8n workflow can call SearXNG without any additional setup')

# ── Save ──────────────────────────────────────────────────────────────────────
output_path = r'c:\Users\PC\OneDrive\Documents\claude\n8n\AI_Agent_Documentation_v2.docx'
doc.save(output_path)
print('Saved:', output_path)
