# Security Architecture: Public AI Agent on AWS

This document explains why security was introduced, what risks existed, every protection layer
that was implemented, and how they all work together to protect the public-facing AI agent at
`https://n8n.hoitcs.com.au/agent`.

---

## The Problem — Why Security Was Needed

When the AI agent was first linked from the HOITCS consulting website, it was publicly
accessible with no protection. Anyone — including automated bots — could send unlimited
requests to it. This created five real risks:

### Risk 1: API Cost Abuse
The agent uses the **Groq API** (a paid LLM service) to generate responses. Every request
consumes quota. A bot sending thousands of requests per hour could exhaust the free tier
or run up unexpected charges with no warning.

### Risk 2: Server Overload
The server running n8n is a **t4g.small EC2 instance** — only 2 CPU cores and 2 GB of RAM.
Sustained automated traffic could overwhelm it, causing the agent (and any other services on
the same server, including `soccer.hoitcs.com.au`) to crash or become unresponsive.

### Risk 3: Direct Webhook Abuse
The n8n AI agent listens on a webhook endpoint (`/webhook/agent`). A bot does not need to
visit the chatbot page to abuse it — it can POST directly to that URL. Once a bot discovers
the endpoint (through scraping, scanning, or simply guessing common paths), it can bypass
the frontend entirely and hammer the API directly.

### Risk 4: Prompt Injection
Malicious users can craft clever inputs designed to manipulate the AI agent into doing
things outside its intended scope — for example, trying to extract internal information,
generate harmful content, or trick it into bypassing its safety rules.

### Risk 5: Inappropriate Content
Without guardrails, users could submit requests for illegal, explicit, or harmful content.
The AI agent searches the internet as part of its workflow, meaning it could inadvertently
search for and return inappropriate material.

---

## The Solution — A Multi-Layer Security Architecture

Rather than relying on a single protection, a **defence-in-depth** approach was implemented.
Every layer catches what the previous layer might miss. Think of it as multiple locked doors
rather than one.

```
Internet (bots, users, attackers)
        │
        ▼
┌─────────────────────────────────┐
│         CLOUDFLARE EDGE         │  Layer 1 — Bot Fight Mode (global bot blocking)
│                                 │  Layer 2 — WAF Rate Limiting (10 req / 10 sec per IP)
│                                 │  Layer 3 — SSL Full (Strict) — end-to-end encryption
└────────────────┬────────────────┘
                 │ (only clean traffic reaches the server)
                 ▼
┌─────────────────────────────────┐
│          CADDY (server)         │  Layer 4 — Secret Token Check (403 without token)
│                                 │  Layer 5 — Real IP passthrough from Cloudflare
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│         FAIL2BAN (server)       │  Layer 6 — IP ban after 30 requests / 60 seconds
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│       N8N WORKFLOW (app)        │  Layer 7 — Keyword blocklist (before search)
│                                 │  Layer 8 — LLM safety rules (system prompt)
└─────────────────────────────────┘
```

---

## Layer 1 — Cloudflare Bot Fight Mode

### What it is
Cloudflare sits in front of the server and inspects all incoming traffic at the network edge
before it ever reaches Australia. Bot Fight Mode uses Cloudflare's global threat intelligence
(built from trillions of requests across millions of websites) to fingerprint and block known
malicious bots automatically.

### Why it was introduced
Without Cloudflare, all traffic — legitimate users and bots — hit the server directly. The
server had no way to distinguish between a human visitor and an automated scanner. By placing
Cloudflare in front, known bad actors are blocked globally before they consume any server
resources at all.

### What it blocks
- Known web scrapers and vulnerability scanners
- Credential stuffing bots
- DDoS attack traffic
- Bots from known malicious IP ranges worldwide

### Configuration
- **Location:** Cloudflare Dashboard → Security → Bots
- **Setting:** Bot Fight Mode → **ON**
- **Plan:** Free tier (no cost)

---

## Layer 2 — Cloudflare WAF Rate Limiting

### What it is
A Web Application Firewall (WAF) rule that limits how many requests a single IP address can
make to the webhook endpoint within a time window. Requests exceeding the limit are blocked
automatically.

### Why it was introduced
Even legitimate-looking traffic can be abusive if it comes too fast. A script (not a
fingerprinted bot) could still hammer the endpoint at hundreds of requests per minute. Rate
limiting catches this category of abuse regardless of whether the sender looks like a bot.

### What it blocks
- Automated scripts running in loops
- Stress-testing tools
- Any IP sending more than 10 requests in 10 seconds to `/webhook/`

### Configuration
- **Location:** Cloudflare Dashboard → Security → WAF → Rate Limiting Rules
- **Rule name:** Webhook rate limit
- **Match:** URI Path starts with `/webhook/`
- **Characteristic:** IP address
- **Threshold:** 10 requests per 10 seconds
- **Action:** Block
- **Plan:** Free tier

### Why `/webhook/` specifically
The AI agent endpoint (`/webhook/agent`) is the only path that incurs LLM API costs. Static
pages (`/agent`, `/chatbot`) and the n8n admin UI don't need rate limiting because they don't
trigger paid API calls.

---

## Layer 3 — SSL Full (Strict)

### What it is
Encryption configuration that ensures traffic is encrypted at every hop — from the user's
browser to Cloudflare, and from Cloudflare to the origin server.

### Why it matters
Cloudflare acts as a "man in the middle" by design (it decrypts traffic at the edge to
inspect and filter it, then re-encrypts it to forward to the server). Without Full (Strict)
mode, Cloudflare could forward traffic to the server over plain HTTP, exposing user messages
in transit.

### Configuration options explained
| Mode | Browser → Cloudflare | Cloudflare → Server | Risk |
|---|---|---|---|
| Off | Plain HTTP | Plain HTTP | All traffic exposed |
| Flexible | HTTPS | Plain HTTP | Messages exposed between CF and server |
| Full | HTTPS | HTTPS (any cert) | Accepts expired/self-signed certs |
| **Full (Strict)** | **HTTPS** | **HTTPS (valid cert)** | **Fully secure — used here** |

### Why Full (Strict) was safe to use
The server already had a valid **Let's Encrypt certificate** managed automatically by Caddy.
Full (Strict) verifies this certificate, ensuring end-to-end encryption with no gaps.

- **Location:** Cloudflare Dashboard → SSL/TLS → Overview
- **Setting:** Full (Strict)

---

## Layer 4 — Caddy Secret Token

### What it is
A shared secret (a 64-character random hex string) that must be present in the HTTP header
of every request to `/webhook/*`. Requests without the correct token receive an immediate
`403 Forbidden` response and never reach n8n.

### Why it was introduced
Cloudflare protects against known bots and rate limits IPs. However, a determined attacker
who discovers the webhook URL could:
- Use a residential proxy to rotate IPs (bypassing rate limits)
- Use a browser with a clean fingerprint (bypassing Bot Fight Mode)

The secret token adds a second independent barrier. Even if Cloudflare is bypassed, the
attacker still needs the token.

### How it works
The chatbot frontend (`/var/www/agent/index.html`) includes the token in every fetch request:
```javascript
headers: {
    'Content-Type': 'application/json',
    'X-Agent-Token': 'eb98d4ab2df2260a4ed033884686ddf876d2b36aa55e24b40a8f2865b7111be6'
}
```

Caddy checks for this header before proxying to n8n:
```caddyfile
handle /webhook/* {
    @no_token not header X-Agent-Token "eb98d4ab...token..."
    respond @no_token 403

    reverse_proxy localhost:5678 { ... }
}
```

### Important note on token security
The token is embedded in the frontend HTML and is therefore visible to anyone who views the
page source. It is not a true secret in the cryptographic sense — it is a **barrier raiser**.
Its purpose is to:
1. Block automated scanners that probe webhook paths without visiting the page first
2. Require a deliberate step (view-source + extract token) before abuse is possible
3. Work in combination with the other layers, not as a standalone protection

To rotate the token if it is ever compromised:
1. Generate a new token: `openssl rand -hex 32`
2. Update `/etc/caddy/Caddyfile` on the server
3. Update `/var/www/agent/index.html` on the server
4. Reload Caddy: `sudo systemctl reload caddy`

### CORS preflight handling
Browser-based requests trigger a CORS preflight (`OPTIONS` request) before the actual POST.
The Caddyfile handles this separately so preflight requests are never blocked by the token check:
```caddyfile
@options method OPTIONS
handle @options {
    header Access-Control-Allow-Headers "Content-Type, X-Agent-Token"
    respond 204
}
```

---

## Layer 5 — Real IP Passthrough (Cloudflare → Caddy)

### What it is
When Cloudflare proxies traffic, the server sees **Cloudflare's IP address**, not the real
visitor's IP. This would cause fail2ban (Layer 6) to ban Cloudflare's IPs instead of the
actual abuser — blocking all legitimate traffic in the process.

To fix this, Caddy is configured to trust Cloudflare's IP ranges and read the real client IP
from the `CF-Connecting-IP` HTTP header that Cloudflare adds to every forwarded request.

### Configuration in Caddyfile
```caddyfile
reverse_proxy localhost:5678 {
    trusted_proxies 173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22
                    141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20
                    197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13
                    104.24.0.0/14 172.64.0.0/13 131.0.72.0/22
    header_up X-Real-IP {http.request.header.CF-Connecting-IP}
}
```

This tells Caddy:
- Trust requests that arrive from these Cloudflare IP ranges
- Forward the real visitor IP (from `CF-Connecting-IP`) as `X-Real-IP` to n8n

---

## Layer 6 — fail2ban Rate Limiting

### What it is
fail2ban is a server-side daemon that monitors Caddy's access logs in real time. If a single
IP address makes more than 30 requests to the webhook endpoint within 60 seconds, fail2ban
automatically adds a firewall rule (via iptables) to ban that IP for 15 minutes.

### Why it was introduced
Cloudflare's rate limiting operates at the edge. fail2ban operates at the OS level on the
server itself. This provides a second rate-limiting layer that:
- Catches traffic that may not pass through Cloudflare (e.g., direct IP access)
- Provides a server-side record of abuse attempts
- Bans at the firewall level — banned IPs don't even reach Caddy

### Configuration files

**Filter** (`/etc/fail2ban/filter.d/caddy-webhook.conf`):
```ini
[Definition]
failregex = .*"remote_ip":"<HOST>".*"uri":"/webhook
ignoreregex =
datepattern = "ts":{EPOCH}
```

**Jail** (`/etc/fail2ban/jail.d/caddy-webhook.conf`):
```ini
[caddy-webhook]
enabled  = true
port     = http,https
filter   = caddy-webhook
logpath  = /var/log/caddy/n8n-access.log
maxretry = 30
findtime = 60
bantime  = 900
action   = iptables-multiport[name=caddy-webhook, port="http,https", protocol=tcp]
```

### Checking fail2ban status
```bash
# See all active jails
sudo fail2ban-client status

# See webhook jail specifically (banned IPs, total attempts)
sudo fail2ban-client status caddy-webhook

# Manually unban an IP
sudo fail2ban-client set caddy-webhook unbanip 1.2.3.4
```

---

## Layer 7 — Keyword Blocklist (n8n Workflow)

### What it is
A JavaScript code node inside the n8n workflow that inspects the search query extracted by
the LLM before it is sent to SearXNG (the search engine). If the query contains any blocked
keyword, it is rejected immediately — SearXNG is never called.

### Why it was introduced
The LLM decides what to search for based on the user's message. A malicious user could craft
a message that causes the LLM to search for inappropriate content. The blocklist intercepts
the search query at the workflow level — after the LLM has processed the request but before
the search executes.

### Blocked categories
```javascript
const blocklist = [
    'porn', 'pornography', 'xxx', 'nude', 'naked', 'sex video', 'adult video',
    'explicit', 'onlyfans', 'escort', 'prostitut', 'child abuse', 'csam',
    'how to make drugs', 'buy drugs', 'buy weapons', 'how to hack',
    'how to kill', 'bomb making', 'dark web'
];
```

### How it works
```
User message → LLM (Groq) → extracts search query
                                        │
                               ┌────────▼────────┐
                               │  Filter Query   │
                               │  (blocklist     │
                               │   check)        │
                               └──┬──────────┬───┘
                         blocked  │          │  safe
                                  ▼          ▼
                            Polite        SearXNG
                            refusal       search
```

When a query is blocked, the user receives a polite refusal message. The event is logged but
no search is performed and no additional LLM cost is incurred.

---

## Layer 8 — LLM Safety Rules (System Prompt)

### What it is
Instructions embedded in the system prompt sent to the Groq LLM with every request. These
instructions define the agent's behaviour and enforce content boundaries at the AI level.

### Why it was introduced
The keyword blocklist (Layer 7) only catches queries that match known keywords. The system
prompt provides a broader, more intelligent safety layer — the LLM itself is instructed to
refuse harmful requests, even ones that don't match the blocklist.

### System prompt (first call — query generation)
```
You are a helpful assistant. Today's date is ${today}.
You have a search tool called search_internet to find current, real-time information.
Always use it when the user asks about current events, sports, news, prices, weather,
or anything time-sensitive.

IMPORTANT SAFETY RULES: You must immediately refuse any request that involves
pornographic content, explicit sexual material, illegal activities, drug procurement,
weapons, hate speech, self-harm, or any content that could harm individuals or groups.
If a user asks for such content, respond politely but firmly that you cannot help.
Do NOT search for such content under any circumstances.
```

### System prompt (second call — answer generation)
```
You are a helpful assistant. Today's date is ${today}.
Use the search results provided to give an accurate, up-to-date answer.
Do not rely on your training data for time-sensitive information.

IMPORTANT: Never include, reference, or summarise any inappropriate, explicit,
or illegal content even if it appears in search results. Skip such results entirely.
```

---

## Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER / BROWSER                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE EDGE (Global)                         │
│                                                                     │
│  [Layer 1] Bot Fight Mode — blocks known bots by fingerprint        │
│  [Layer 2] WAF Rate Limit — blocks >10 req/10s per IP to /webhook/ │
│  [Layer 3] SSL Full Strict — enforces end-to-end encryption        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS (clean traffic only)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              EC2 t4g.small — ap-southeast-2 (Sydney)                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   CADDY (reverse proxy)                      │  │
│  │                                                              │  │
│  │  [Layer 4] Token check — 403 if X-Agent-Token missing       │  │
│  │  [Layer 5] CF-Connecting-IP → X-Real-IP passthrough         │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────┴──────────────────────────────────┐  │
│  │                  FAIL2BAN (daemon)                           │  │
│  │  [Layer 6] Monitors Caddy logs — bans IP after 30 req/60s   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │                    N8N WORKFLOW                               │  │
│  │                                                              │  │
│  │  User message → Groq LLM → search query                     │  │
│  │                                │                            │  │
│  │              [Layer 7] Keyword blocklist                     │  │
│  │              [Layer 8] LLM safety system prompt             │  │
│  │                                │                            │  │
│  │                           SearXNG → answer → user           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Security Maintenance Checklist

| Task | Frequency | How |
|---|---|---|
| Check fail2ban banned IPs | Weekly | `sudo fail2ban-client status caddy-webhook` |
| Review Cloudflare analytics for anomalies | Weekly | Cloudflare Dashboard → Analytics |
| Check Groq API usage against limits | Monthly | console.groq.com → Usage |
| Rotate the secret token | If compromised | Update Caddyfile + agent HTML, reload Caddy |
| Update n8n to latest version | Monthly | `cd /opt/n8n && sudo docker compose pull && sudo docker compose up -d` |
| Check server disk usage | Monthly | `df -h` via SSH |
| Review blocked keyword list | Quarterly | Update n8n workflow → Filter Query node |

---

## Token Rotation Procedure

If the secret token is ever exposed or you suspect abuse, rotate it immediately:

```bash
# 1. SSH into the server
ssh -i test-web.pem ubuntu@13.237.175.232

# 2. Generate a new token
NEW_TOKEN=$(openssl rand -hex 32)
echo "New token: $NEW_TOKEN"

# 3. Update Caddyfile
sudo sed -i "s/eb98d4ab2df2260a4ed033884686ddf876d2b36aa55e24b40a8f2865b7111be6/$NEW_TOKEN/g" /etc/caddy/Caddyfile

# 4. Update agent HTML
sudo sed -i "s/eb98d4ab2df2260a4ed033884686ddf876d2b36aa55e24b40a8f2865b7111be6/$NEW_TOKEN/g" /var/www/agent/index.html

# 5. Reload Caddy
sudo systemctl reload caddy
```

---

*Document created: May 2026*
*Author: HOITCS — Hands On IT Consulting Services*
