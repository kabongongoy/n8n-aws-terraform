# Local AI Agent Documentation: n8n + Ollama + SearXNG on Windows

## What Are We Building?

A fully local AI agent that runs entirely on your Windows PC — no cloud, no monthly API costs, no internet dependency for the AI itself. It uses:

- **n8n** — the workflow engine (runs in Docker)
- **Ollama** — runs your local LLM (Gemma 4 4B, registered from GGUF file)
- **SearXNG** — a self-hosted search engine (runs in Docker)

The only time the internet is used is when SearXNG fetches search results — and that is just normal web browsing with no API key or cost.

---

## How It Compares to the Cloud Version

| | Cloud (AWS) | Local (Your PC) |
|---|---|---|
| n8n URL | https://n8n.hoitcs.com.au | http://localhost:5678 |
| LLM | Groq API (external) | Ollama (on your machine) |
| Search | SearXNG on EC2 | SearXNG in Docker |
| HTTPS | Yes (via Caddy) | No (not needed locally) |
| Cost | ~$18–20 AUD/month | $0 |
| Accessible from internet | Yes | No (localhost only) |
| Webhook from external services | Yes | No (localhost only) |

---

## Architecture

```
Your Browser
     │
     │  http://localhost:5678
     ▼
n8n (Docker container)
     │
     ├──► Ollama (native on host) → GLM 4.7 Flash (29B)
     │         http://host.docker.internal:11434
     │
     └──► SearXNG (Docker container)
               http://host.docker.internal:8080
                    │
               Google / Bing / DuckDuckGo
```

Everything stays on your machine. No data leaves your PC except the search queries sent to search engines.

---

## Prerequisites

Before starting, make sure you have these installed:

| Tool | Purpose | Check |
|---|---|---|
| Docker Desktop | Runs n8n and SearXNG in containers | `docker --version` |
| Ollama | Runs your local LLM | `ollama --version` |
| A browser | To open n8n and the chatbot | — |

---

## Part 1: Understanding the Key Difference — host.docker.internal

In the cloud setup, everything ran on one server, so services could reach each other via `localhost`. Locally, n8n runs inside a Docker container while Ollama runs natively on Windows. They are in different environments.

Docker provides a special hostname called `host.docker.internal` that lets containers reach the host machine:

```
From inside n8n container:
  host.docker.internal:11434  → Ollama on your Windows machine
  host.docker.internal:8080   → SearXNG container (via host network)
```

This is the only significant change from the cloud setup.

---

## Part 2: Setting Up n8n Locally

### Step 2.1 — Create the n8n Directory

Create a folder on your PC:
```
C:\Users\PC\n8n-local\
```

### Step 2.2 — Create docker-compose.yml

Create `C:\Users\PC\n8n-local\docker-compose.yml`:

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n-local
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://localhost:5678/
      - GENERIC_TIMEZONE=Australia/Brisbane
      - N8N_LOG_LEVEL=info
    volumes:
      - ./data:/home/node/.n8n
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Key differences from cloud:
- `N8N_PROTOCOL=http` — no HTTPS locally
- `WEBHOOK_URL=http://localhost:5678/` — local URL
- No `N8N_BASIC_AUTH_*` — no password needed locally (only you can access it)
- `extra_hosts` — ensures `host.docker.internal` resolves correctly on Linux/Mac

### Step 2.3 — Start n8n

Open PowerShell and run:

```powershell
cd C:\Users\PC\n8n-local
docker compose up -d
```

### Step 2.4 — Open n8n

Open your browser and go to **http://localhost:5678**. Complete the one-time setup (create an owner account).

### Step 2.5 — Verify n8n is Running

```powershell
docker ps --filter "name=n8n-local"
```

You should see `n8n-local` with status `Up`.

---

## Part 3: Setting Up SearXNG Locally

### Step 3.1 — Create the SearXNG Directory

```
C:\Users\PC\searxng-local\
```

### Step 3.2 — Create settings.yml

Create `C:\Users\PC\searxng-local\settings.yml`:

```yaml
use_default_settings: true

server:
  secret_key: 'local-searxng-secret-key'
  bind_address: '0.0.0.0'
  port: 8080
  limiter: false

search:
  safe_search: 2        # 0=off, 1=moderate, 2=strict
  default_lang: 'en'
  formats:
    - html
    - json              # Must be enabled for n8n to call it

outgoing:
  request_timeout: 10.0
```

### Step 3.3 — Create docker-compose.yml

Create `C:\Users\PC\searxng-local\docker-compose.yml`:

```yaml
services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng-local
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./settings.yml:/etc/searxng/settings.yml:ro
    environment:
      - SEARXNG_SECRET=local-searxng-secret-key
```

### Step 3.4 — Start SearXNG

```powershell
cd C:\Users\PC\searxng-local
docker compose up -d
```

### Step 3.5 — Test SearXNG

Open your browser and go to **http://localhost:8080** — you should see the SearXNG search interface.

Or test via PowerShell:
```powershell
Invoke-RestMethod "http://localhost:8080/search?q=hello&format=json" | Select-Object -ExpandProperty results | Select-Object -First 2
```

---

## Part 4: Ollama — Your Local LLM

### What is Ollama?

Ollama runs large language models locally on your Windows PC using llama.cpp under the hood. It exposes a REST API that n8n calls to generate responses.

### Models Available

```powershell
ollama list
```

For this setup we use:

| Model | Size | Tool Calling | Quality |
|---|---|---|---|
| `glm-4.7-flash:latest` | 19 GB | ✅ Yes | Excellent (29B params) |
| `llama3.2:latest` | 2.0 GB | ✅ Yes | Good (3B params, faster) |

### Ollama API Endpoints

Ollama exposes two APIs:

**OpenAI-compatible** (what we use — same format as Groq/OpenAI):
```
http://localhost:11434/v1/chat/completions
```

**Native Ollama API:**
```
http://localhost:11434/api/chat
```

We use the OpenAI-compatible endpoint because it uses the same JSON format as the cloud workflow, making the transition from Groq seamless.

### Key Difference from Groq

With Groq, tool call arguments come back as a **JSON string**:
```json
{"function": {"arguments": "{\"query\": \"latest news\"}"}}
```

With Ollama, they come back as an **object**:
```json
{"function": {"arguments": {"query": "latest news"}}}
```

The workflow handles this with a compatibility check:
```javascript
const args = typeof toolCall.function.arguments === 'string'
  ? JSON.parse(toolCall.function.arguments)
  : toolCall.function.arguments;
```

---

## Part 5: Creating the Agent Workflow

Because n8n stores workflows in a SQLite database inside the Docker container, we create them using a Node.js script that runs inside the container.

### Step 5.1 — Create the Workflow Script

Save this as `C:\Users\PC\n8n-local\create_workflow.js` and run it with:

```powershell
docker cp C:\Users\PC\n8n-local\create_workflow.js n8n-local:/tmp/create_workflow.js
docker exec n8n-local node /tmp/create_workflow.js
```

The script creates the complete workflow with all nodes and registers the webhook at `/webhook/agent-local`.

### Step 5.2 — Restart n8n

```powershell
docker restart n8n-local
```

### Step 5.3 — Publish the Workflow

1. Open **http://localhost:5678**
2. Find the **local-ollama-agent** workflow
3. Click **Publish**

### Step 5.4 — Add Workflow History (if Publish fails with "Version not found")

```powershell
docker cp C:\Users\PC\n8n-local\add_history.js n8n-local:/tmp/add_history.js
docker exec n8n-local node /tmp/add_history.js
```

Then try Publish again.

---

## Part 6: The Workflow — Node by Node

The workflow is identical in structure to the cloud version. The only changes are:

| | Cloud (Groq) | Local (Ollama) |
|---|---|---|
| LLM URL | `https://api.groq.com/openai/v1/chat/completions` | `http://host.docker.internal:11434/v1/chat/completions` |
| Auth header | `Authorization: Bearer API_KEY` | None needed |
| Model | `qwen/qwen3-32b` | `glm-4.7-flash:latest` |
| SearXNG URL | `http://172.18.0.1:8080/search` | `http://host.docker.internal:8080/search` |
| Arguments format | JSON string | Object (handled automatically) |

### Complete Workflow Structure

```
Webhook (POST /webhook/agent-local)
        ↓
Build First Request (Code node)
  - Gets today's date
  - Gets user message from webhook
  - Builds request body for Ollama
        ↓
Call Ollama with Tools (HTTP Request)
  - POST to http://host.docker.internal:11434/v1/chat/completions
  - No auth header needed
  - Includes tool definition for search_internet
        ↓
Needs Search? (IF node)
  - Checks finish_reason = "tool_calls"
  ↓ YES                          ↓ NO
Get Search Query            Respond Directly
  ↓                         (searched: false)
Filter Query ← blocklist check
  ↓
Is Blocked?
  ↓ YES              ↓ NO
Build Refusal    Search SearXNG
  ↓              (host.docker.internal:8080)
Respond Refused       ↓
               Build Second Request
                      ↓
               Send Results to Ollama
                      ↓
               Respond with Search Answer
               (searched: true)
```

### Node: Build First Request

This Code node prepares the request to Ollama. It injects today's date, the user's message, and the tool definition:

```javascript
const today = new Date().toLocaleDateString('en-AU', {
  weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
});
const userMessage = $('Webhook').item.json.body.message;

const systemPrompt = `You are a helpful assistant. Today's date is ${today}.
You have a search tool called search_internet for current, real-time information.
Use it for current events, sports, news, prices, weather.
Use your own knowledge for timeless facts.
IMPORTANT: Refuse any request involving pornography, illegal activities, drugs, weapons, hate speech.`;

const body = JSON.stringify({
  model: 'glm-4.7-flash:latest',
  messages: [
    { role: 'system', content: systemPrompt },
    { role: 'user',   content: userMessage }
  ],
  tools: [{
    type: 'function',
    function: {
      name: 'search_internet',
      description: 'Search the internet for current, real-time information',
      parameters: {
        type: 'object',
        properties: { query: { type: 'string', description: 'The search query' } },
        required: ['query']
      }
    }
  }],
  tool_choice: 'auto'
});

return [{ json: { body, userMessage } }];
```

### Node: Get Search Query

Extracts the search query from Ollama's tool call response. Handles both JSON string and object formats:

```javascript
const toolCall = $input.item.json.choices[0].message.tool_calls[0];

// Ollama returns arguments as object; Groq returns as JSON string
const args = typeof toolCall.function.arguments === 'string'
  ? JSON.parse(toolCall.function.arguments)
  : toolCall.function.arguments;

const query = args.query !== undefined ? String(args.query) : '';
return [{ json: { query, toolCallId: toolCall.id } }];
```

### Node: Filter Query

Blocks inappropriate search queries before they reach SearXNG:

```javascript
const blocklist = [
  'porn', 'pornography', 'xxx', 'nude', 'naked', 'sex video', 'explicit',
  'onlyfans', 'escort', 'how to make drugs', 'buy drugs',
  'how to kill', 'bomb making', 'dark web', 'csam'
];

const q = $input.item.json.query;
const query = (q !== undefined && q !== null) ? String(q).toLowerCase() : '';
const blocked = blocklist.some(w => query.includes(w));

if (blocked) return [{ json: {
  blocked: true, query,
  refusal: "I'm sorry, I cannot search for that type of content."
}}];

return [{ json: { blocked: false, query: String($input.item.json.query) } }];
```

### Node: Search SearXNG

Calls the local SearXNG instance. From inside n8n's Docker container, SearXNG is reachable via `host.docker.internal`:

```
Method:  GET
URL:     http://host.docker.internal:8080/search
Params:
  q        = ={{ $json.query }}
  format   = json
  language = en
```

---

## Part 7: Content Guardrails (Three Layers)

### Layer 1 — SearXNG Safe Search (Level 2 — Strict)

In `settings.yml`:
```yaml
search:
  safe_search: 2
```

This tells Google, Bing, and DuckDuckGo to filter explicit results before returning them.

### Layer 2 — LLM System Prompt

The system prompt explicitly instructs GLM to refuse inappropriate requests before calling the search tool:

```
IMPORTANT: Refuse any request involving pornographic content, explicit sexual material,
illegal activities, drug procurement, weapons, hate speech, or self-harm.
Do NOT search for such content under any circumstances.
```

### Layer 3 — Query Keyword Filter

The `Filter Query` node checks the generated search query against a blocklist. If a match is found, the search is skipped and a polite refusal is returned directly.

---

## Part 8: The Local Chatbot Page

The chatbot page is a single HTML file saved at:
```
C:\Users\PC\n8n-local\agent-local.html
```

Open it by double-clicking in File Explorer. No web server required.

Key settings in the HTML:
```javascript
const WEBHOOK_URL = 'http://localhost:5678/webhook/agent-local';
```

Features:
- **"⚡ LOCAL"** badge in the header — clearly identifies this as the local version
- **"🔍 Searched the internet"** badge (green) — confirms search was used
- **"💡 Answered from knowledge"** badge (purple) — confirms local knowledge was used
- **"🚫 Request blocked"** badge (red) — confirms guardrail triggered

---

## Part 9: Managing the Local Setup

### Start Everything

```powershell
# Start n8n
cd C:\Users\PC\n8n-local
docker compose up -d

# Start SearXNG
cd C:\Users\PC\searxng-local
docker compose up -d

# Ollama starts automatically with Windows — check with:
ollama list
```

### Stop Everything

```powershell
cd C:\Users\PC\n8n-local;    docker compose down
cd C:\Users\PC\searxng-local; docker compose down
```

### Check Status

```powershell
docker ps --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
```

### View Logs

```powershell
docker logs -f n8n-local
docker logs -f searxng-local
```

### Update n8n to Latest Version

```powershell
cd C:\Users\PC\n8n-local
docker compose pull
docker compose up -d
```

### Switch Models

To switch between models, update the model name in the **Build First Request** and **Build Second Request** Code nodes in n8n, then Publish the workflow.

```javascript
// Fast but less capable
model: 'llama3.2:latest'

// Slower to load but much more capable
model: 'glm-4.7-flash:latest'
```

### Pull a New Model

```powershell
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
```

---

## Part 10: Performance Expectations

| Model | Size | First Response | Subsequent Responses | RAM Used |
|---|---|---|---|---|
| `llama3.2:latest` (3B) | 2 GB | ~5–10 sec | ~2–5 sec | ~3 GB |
| `gemma4-4b:latest` (4B) | 5 GB | ~15–30 sec | ~5–15 sec (direct) / 30–60 sec (search) | ~5 GB |
| `glm-4.7-flash:latest` (29B) | 19 GB | ~30–60 sec | ~10–20 sec | ~12–15 GB |

### Why the First Response is Slow

Ollama unloads models from memory after 5 minutes of inactivity. The next request reloads model weights from disk into RAM — that is the slow part. Once warm, all subsequent responses are much faster.

### Keep the Model Loaded Permanently

To avoid cold start delays, prevent Ollama from ever unloading the model:

```powershell
# Set keep-alive to forever (-1 = never unload)
[System.Environment]::SetEnvironmentVariable('OLLAMA_KEEP_ALIVE', '-1', 'User')
# Restart Ollama from the system tray for this to take effect
```

Or keep a terminal open with the model running:

```powershell
ollama run gemma4-4b:latest
# Leave this terminal open — type /bye to stop
```

### Search vs Direct Answer Speed

For the agent workflow, search questions require two Ollama calls plus a SearXNG request:

```
Direct answer:  1x Ollama call            → 5–15 sec (warm)
Search answer:  1x Ollama + SearXNG + 1x Ollama → 30–60 sec (warm)
```

The chatbot page shows **"⏳ Searching the web... this may take 1–2 minutes on CPU"** after 15 seconds so you know it is working and have not timed out.

---

## Part 11: How the Decision Works End to End

### Example 1: Simple Question

```
User: "what is 2 + 2?"
        ↓
Ollama reads question + tool definition
Ollama thinks: "Basic maths — I know this. No search needed."
Ollama returns: finish_reason = "stop"
        ↓
IF node → FALSE branch → Respond Directly
        ↓
Response: { "output": "2 + 2 = 4", "searched": false }
Chatbot shows: 💡 Answered from knowledge
```

### Example 2: Current Events Question

```
User: "what is the latest news in Australia?"
        ↓
Ollama reads question + today's date + tool definition
Ollama thinks: "This needs current info. I will search."
Ollama returns: finish_reason = "tool_calls"
  query: "latest Australia news May 2026"
        ↓
Filter Query: "latest australia news..." → not blocked ✅
        ↓
SearXNG searches Google/Bing/DuckDuckGo
Returns 30 results with titles and content
        ↓
Build Second Request sends results to Ollama
Ollama reads results and writes summary
        ↓
Response: { "output": "Here are today's stories...", "searched": true }
Chatbot shows: 🔍 Searched the internet
```

### Example 3: Blocked Request

```
User: "show me porn videos"
        ↓
Ollama reads question + safety rules in system prompt
Ollama thinks: "This violates safety rules. I must refuse."
Ollama returns: finish_reason = "stop", content = "I'm sorry..."
        ↓
IF node → FALSE branch → Respond Directly
        ↓
Response: { "output": "I'm sorry...", "searched": false }
```

---

## Part 12: Adding Models — Download vs Copy

### Option A — Download via Ollama CLI

```powershell
ollama pull gemma4-4b:latest
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
```

### Option B — Copy a GGUF File from Another Computer

If you already have a model file (`.gguf`) on another machine, you can copy it directly without re-downloading. No internet required.

**Step 1 — Copy the GGUF file to your PC:**

Place it anywhere, for example:
```
C:\Users\PC\.ollama\models\gemma-4-E4B-it-Q4_K_M.gguf
```

**Step 2 — Create a Modelfile pointing to it:**

Create a text file (e.g. `C:\Users\PC\.ollama\Modelfile-gemma4`) containing:
```
FROM C:\Users\PC\.ollama\models\gemma-4-E4B-it-Q4_K_M.gguf
```

**Step 3 — Register it with Ollama:**

```powershell
ollama create gemma4-4b -f "C:\Users\PC\.ollama\Modelfile-gemma4"
```

**Step 4 — Verify it appears:**

```powershell
ollama list
# Should show: gemma4-4b:latest
```

**Step 5 — Test tool calling before using in the workflow:**

```powershell
$body = '{
  "model": "gemma4-4b:latest",
  "messages": [{"role":"user","content":"What is the latest news in Australia?"}],
  "tools": [{"type":"function","function":{"name":"search_internet","description":"Search web","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}}],
  "tool_choice": "auto",
  "stream": false
}'
$r = Invoke-RestMethod "http://localhost:11434/v1/chat/completions" -Method POST -ContentType "application/json" -Body $body
Write-Host "finish_reason:" $r.choices[0].finish_reason
# Should say: tool_calls (meaning the model correctly decided to search)
```

### Switching Models in the Workflow

Use the `switch_model.js` script (copy it into the container and run it), then Publish the workflow in n8n:

```powershell
docker cp C:\Users\PC\n8n-local\switch_model.js n8n-local:/tmp/switch_model.js
docker exec n8n-local node /tmp/switch_model.js
```

Or manually edit the **Build First Request** and **Build Second Request** Code nodes in n8n and change the model name, then Publish.

---

## Part 13: Cost Summary

| Component | Cost |
|---|---|
| n8n (Docker) | $0 |
| SearXNG (Docker) | $0 |
| Ollama + Gemma 4 model | $0 |
| Web search results (via SearXNG) | $0 |
| **Total** | **$0** |

The only costs are electricity and your existing internet connection.

---

## Summary: What You Have Built Locally

```
Windows PC
├── Docker Desktop
│     ├── n8n-local        → http://localhost:5678
│     └── searxng-local    → http://localhost:8080
│
└── Ollama (native Windows app)
      └── glm-4.7-flash    → http://localhost:11434
            (29B params, Q4 quantized, ~19GB)
```

**What makes this different from the cloud version:**
- Zero ongoing cost
- Data never leaves your machine (except search queries)
- Works without internet (except for search results)
- No Caddy, no HTTPS, no domain name needed
- Webhook only accessible from your PC (no external triggers)
- First response is slower (model loading time)
