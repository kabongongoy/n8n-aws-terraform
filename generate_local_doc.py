from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

for section in doc.sections:
    section.top_margin = section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2.5)

TEAL = RGBColor(0x0f, 0x76, 0x6e)
DARK = RGBColor(0x1e, 0x29, 0x3b)
GREY = RGBColor(0x64, 0x74, 0x8b)

def shade_paragraph(para, rgb):
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), '{:02X}{:02X}{:02X}'.format(*rgb))
    pPr.append(shd)

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

def add_h1(text):
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after  = Pt(6)
    r = p.add_run(text)
    r.font.size = Pt(20); r.font.bold = True; r.font.color.rgb = TEAL
    add_rule(doc)

def add_h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14); p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.font.size = Pt(15); r.font.bold = True; r.font.color.rgb = DARK

def add_h3(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = TEAL

def add_body(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.size = Pt(11); r.font.color.rgb = DARK

def add_bullet(text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent = Cm(1 + level * 0.5)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    r.font.size = Pt(11); r.font.color.rgb = DARK

def add_code(text):
    for line in text.strip().split('\n'):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0); p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.5); p.paragraph_format.right_indent = Cm(0.5)
        shade_paragraph(p, (241, 245, 249))
        r = p.add_run(line if line else ' ')
        r.font.name = 'Courier New'; r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0x0f, 0x17, 0x2a)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def add_note(text, colour=(254, 252, 232), text_colour=RGBColor(0x92, 0x40, 0x0e)):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5); p.paragraph_format.space_after = Pt(6)
    shade_paragraph(p, colour)
    r = p.add_run('Note: ' + text)
    r.font.size = Pt(10); r.font.italic = True; r.font.color.rgb = text_colour

def add_table(headers, rows):
    table = doc.add_table(rows=len(rows)+1, cols=len(headers))
    table.style = 'Table Grid'
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        cell.paragraphs[0].runs[0].font.bold = True
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            table.rows[i+1].cells[j].text = val
    doc.add_paragraph()

# ── Cover ─────────────────────────────────────────────────────────────────────
doc.add_paragraph('\n\n')
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Local AI Agent Setup')
r.font.size = Pt(28); r.font.bold = True; r.font.color.rgb = TEAL

p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = p2.add_run('n8n + Ollama + SearXNG on Windows')
r2.font.size = Pt(16); r2.font.color.rgb = GREY

doc.add_paragraph('\n')
p3 = doc.add_paragraph(); p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
r3 = p3.add_run('A fully local, zero-cost AI agent with internet search.\nNo cloud. No API keys. No monthly fees.')
r3.font.size = Pt(12); r3.font.italic = True; r3.font.color.rgb = GREY

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('What Are We Building?')
add_body('A fully local AI agent that runs entirely on your Windows PC with zero ongoing cost. '
         'The only internet usage is when SearXNG fetches search results — normal web browsing, '
         'no API key required.')
add_bullet('n8n — workflow engine (Docker container)')
add_bullet('Ollama — runs GLM 4.7 Flash locally (29B parameters, 19GB)')
add_bullet('SearXNG — self-hosted search engine (Docker container)')

add_h2('Cloud vs Local Comparison')
add_table(
    ['Feature', 'Cloud (AWS)', 'Local (Windows PC)'],
    [
        ('n8n URL',          'https://n8n.hoitcs.com.au', 'http://localhost:5678'),
        ('LLM',              'Groq API (external)',        'Ollama (on your machine)'),
        ('Monthly cost',     '~$18–20 AUD',               '$0'),
        ('HTTPS',            'Yes (Caddy)',                'No (not needed)'),
        ('Internet access',  'Yes (public URL)',           'No (localhost only)'),
        ('External webhooks','Yes',                        'No'),
    ]
)

add_h2('Architecture')
add_code(
    'Your Browser\n'
    '     │  http://localhost:5678\n'
    '     ▼\n'
    'n8n (Docker container)\n'
    '     │\n'
    '     ├──► Ollama (native Windows) → GLM 4.7 Flash\n'
    '     │         http://host.docker.internal:11434\n'
    '     │\n'
    '     └──► SearXNG (Docker container)\n'
    '               http://host.docker.internal:8080\n'
    '                    │\n'
    '               Google / Bing / DuckDuckGo'
)

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 1: The Key Concept — host.docker.internal')
add_body('In the cloud, everything ran on one server so services used localhost. '
         'Locally, n8n runs inside Docker while Ollama runs natively on Windows — '
         'different environments. Docker provides a special hostname to bridge them:')
add_code(
    '# From inside n8n container:\n'
    'host.docker.internal:11434  →  Ollama on your Windows machine\n'
    'host.docker.internal:8080   →  SearXNG container (via host network)'
)
add_note('This is the only significant networking change from the cloud version.')

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 2: Setting Up n8n Locally')

add_h2('Step 2.1 — Create n8n Directory and docker-compose.yml')
add_body('Create C:\\Users\\PC\\n8n-local\\docker-compose.yml:')
add_code(
    'services:\n'
    '  n8n:\n'
    '    image: n8nio/n8n:latest\n'
    '    container_name: n8n-local\n'
    '    restart: unless-stopped\n'
    '    ports:\n'
    '      - "5678:5678"\n'
    '    environment:\n'
    '      - N8N_HOST=localhost\n'
    '      - N8N_PORT=5678\n'
    '      - N8N_PROTOCOL=http          # No HTTPS locally\n'
    '      - WEBHOOK_URL=http://localhost:5678/\n'
    '      - GENERIC_TIMEZONE=Australia/Brisbane\n'
    '      - N8N_LOG_LEVEL=info\n'
    '    volumes:\n'
    '      - ./data:/home/node/.n8n    # Data stored on host\n'
    '    extra_hosts:\n'
    '      - "host.docker.internal:host-gateway"'
)

add_h2('Step 2.2 — Start n8n')
add_code(
    'cd C:\\Users\\PC\\n8n-local\n'
    'docker compose up -d'
)
add_body('Open http://localhost:5678 in your browser and complete the one-time setup.')

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 3: Setting Up SearXNG Locally')

add_h2('Step 3.1 — Create SearXNG Directory and Files')
add_body('Create C:\\Users\\PC\\searxng-local\\settings.yml:')
add_code(
    'use_default_settings: true\n'
    'server:\n'
    '  secret_key: "local-searxng-secret-key"\n'
    '  bind_address: "0.0.0.0"\n'
    '  port: 8080\n'
    '  limiter: false\n'
    'search:\n'
    '  safe_search: 2\n'
    '  default_lang: "en"\n'
    '  formats:\n'
    '    - html\n'
    '    - json          # Required for n8n API calls\n'
    'outgoing:\n'
    '  request_timeout: 10.0'
)
add_body('Create C:\\Users\\PC\\searxng-local\\docker-compose.yml:')
add_code(
    'services:\n'
    '  searxng:\n'
    '    image: searxng/searxng:latest\n'
    '    container_name: searxng-local\n'
    '    restart: unless-stopped\n'
    '    ports:\n'
    '      - "8080:8080"\n'
    '    volumes:\n'
    '      - ./settings.yml:/etc/searxng/settings.yml:ro\n'
    '    environment:\n'
    '      - SEARXNG_SECRET=local-searxng-secret-key'
)

add_h2('Step 3.2 — Start SearXNG')
add_code(
    'cd C:\\Users\\PC\\searxng-local\n'
    'docker compose up -d'
)
add_body('Test it: Open http://localhost:8080 in your browser.')

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 4: Ollama — Your Local LLM')

add_h2('Available Models')
add_table(
    ['Model', 'Size', 'Tool Calling', 'First Response', 'Quality'],
    [
        ('gemma4-4b:latest', '19 GB', 'Yes', '30–60 sec', 'Excellent (29B)'),
        ('llama3.2:latest',      '2 GB',  'Yes', '5–10 sec',  'Good (3B, faster)'),
    ]
)

add_h2('Key Difference: Tool Call Arguments Format')
add_body('Groq returns tool call arguments as a JSON string. '
         'Ollama returns them as a JavaScript object. '
         'The workflow handles both automatically:')
add_code(
    '// Handles both Groq (string) and Ollama (object) formats\n'
    'const args = typeof toolCall.function.arguments === "string"\n'
    '  ? JSON.parse(toolCall.function.arguments)\n'
    '  : toolCall.function.arguments;\n'
    '\n'
    'const query = String(args.query);'
)

add_h2('Ollama API Endpoints')
add_code(
    '# OpenAI-compatible (what we use — same format as Groq)\n'
    'http://localhost:11434/v1/chat/completions\n'
    '\n'
    '# From inside n8n Docker container:\n'
    'http://host.docker.internal:11434/v1/chat/completions'
)
add_note('No Authorization header is needed — Ollama has no API key requirement.')

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 5: Creating the Workflow')

add_h2('How Workflow Creation Works Locally')
add_body('Because n8n on Windows stores data inside the Docker container '
         '(WSL2 filesystem), we cannot modify the database directly from Windows. '
         'Instead, we copy a Node.js script into the container and run it there:')
add_code(
    '# Copy script into container\n'
    'docker cp C:\\Users\\PC\\n8n-local\\create_workflow.js n8n-local:/tmp/create_workflow.js\n'
    '\n'
    '# Run it inside the container\n'
    'docker exec n8n-local node /tmp/create_workflow.js\n'
    '\n'
    '# Restart n8n to pick up the new workflow\n'
    'docker restart n8n-local'
)
add_body('Then open http://localhost:5678, find the local-ollama-agent workflow, and click Publish.')
add_note('If Publish fails with "Version not found", run add_history.js the same way, then try again.')

add_h2('What Changes vs the Cloud Workflow')
add_table(
    ['Setting', 'Cloud (Groq)', 'Local (Ollama)'],
    [
        ('LLM URL',      'https://api.groq.com/openai/v1/chat/completions', 'http://host.docker.internal:11434/v1/chat/completions'),
        ('Auth header',  'Authorization: Bearer API_KEY',                    'None needed'),
        ('Model',        'qwen/qwen3-32b',                                   'gemma4-4b:latest'),
        ('SearXNG URL',  'http://172.18.0.1:8080/search',                   'http://host.docker.internal:8080/search'),
        ('Arguments',    'JSON string',                                       'Object (handled automatically)'),
    ]
)

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 6: Content Guardrails')
add_body('Three layers of protection — identical to the cloud version:')
add_bullet('Layer 1 — SearXNG safe_search: 2 (strict) — filters at search engine level')
add_bullet('Layer 2 — LLM system prompt — instructs GLM to refuse inappropriate requests')
add_bullet('Layer 3 — Filter Query Code node — keyword blocklist before SearXNG')
add_note('The system prompt guardrail is the first line of defence. '
         'Most inappropriate requests are refused before the search tool is even called.')

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 7: The Local Chatbot Page')
add_body('A single HTML file at C:\\Users\\PC\\n8n-local\\agent-local.html. '
         'Double-click it in File Explorer to open — no web server required.')
add_code('const WEBHOOK_URL = "http://localhost:5678/webhook/agent-local";')
add_body('Features:')
add_bullet('"⚡ LOCAL" badge in the header — identifies this as the local version')
add_bullet('"🔍 Searched the internet" badge — confirms SearXNG was used')
add_bullet('"💡 Answered from knowledge" badge — confirms GLM answered directly')
add_bullet('"🚫 Request blocked" badge — confirms a guardrail was triggered')

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 8: Managing the Local Setup')

add_h2('Start Everything')
add_code(
    '# Start n8n\n'
    'cd C:\\Users\\PC\\n8n-local;     docker compose up -d\n'
    '\n'
    '# Start SearXNG\n'
    'cd C:\\Users\\PC\\searxng-local; docker compose up -d\n'
    '\n'
    '# Ollama starts automatically with Windows'
)

add_h2('Stop Everything')
add_code(
    'cd C:\\Users\\PC\\n8n-local;     docker compose down\n'
    'cd C:\\Users\\PC\\searxng-local; docker compose down'
)

add_h2('Check Status')
add_code('docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"')

add_h2('Switch Models')
add_body('Update the model name in the Build First Request and Build Second Request '
         'Code nodes in n8n, then Publish the workflow:')
add_code(
    '// Fast but less capable (2GB)\n'
    "model: 'llama3.2:latest'\n"
    '\n'
    '// Slower but much more capable (19GB)\n'
    "model: 'gemma4-4b:latest'"
)

add_h2('Pull a New Model')
add_code(
    'ollama pull llama3.1:8b\n'
    'ollama pull qwen2.5:7b'
)

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 9: Performance')
add_table(
    ['Model', 'Size', 'First Response', 'Subsequent', 'RAM Used'],
    [
        ('llama3.2:latest (3B)',       '2 GB',  '5–10 sec',  '2–5 sec',   '~3 GB'),
        ('gemma4-4b:latest (4B)',      '5 GB',  '15–30 sec', '5–60 sec',  '~5 GB'),
        ('gemma4-4b:latest (4B)',  '5 GB',  '15–30 sec', '5–15 sec',  '~5 GB'),
    ]
)

add_h2('Cold Start vs Warm Responses')
add_body(
    'Ollama unloads models from memory after 5 minutes of inactivity. '
    'The next request triggers a cold start — loading weights from disk into RAM. '
    'Once warm, all subsequent responses are much faster.'
)
add_body('For search questions, the workflow makes two Ollama calls:')
add_code(
    'Direct answer:  1x Ollama call                        → 5–15 sec (warm)\n'
    'Search answer:  1x Ollama + SearXNG + 1x Ollama  → 30–60 sec (warm)'
)

add_h2('Keep the Model Permanently Loaded')
add_body('To avoid cold start delays, set OLLAMA_KEEP_ALIVE to never unload:')
add_code(
    '# PowerShell — set permanently for your user\n'
    "[System.Environment]::SetEnvironmentVariable('OLLAMA_KEEP_ALIVE', '-1', 'User')\n"
    '# Restart Ollama from the system tray for this to take effect'
)

add_h2('Chatbot Timeout Handling')
add_body(
    'The local chatbot page (agent-local.html) has a 4-minute fetch timeout. '
    'After 15 seconds of waiting it shows "⏳ Searching the web... '
    'this may take 1–2 minutes on CPU" so you know it is still working.'
)

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 10: Adding Models — Download vs Copy')

add_h2('Option A — Download via Ollama CLI')
add_code(
    'ollama pull gemma4-4b:latest\n'
    'ollama pull qwen2.5:7b\n'
    'ollama pull llama3.1:8b'
)

add_h2('Option B — Copy a GGUF File from Another Computer')
add_body(
    'If you already have a model file (.gguf) on another machine, '
    'copy it directly without re-downloading. No internet required.'
)
add_body('Step 1 — Copy the GGUF file to your PC, e.g.:')
add_code(r'C:\Users\PC\.ollama\models\gemma-4-E4B-it-Q4_K_M.gguf')

add_body('Step 2 — Create a Modelfile pointing to the file:')
add_code(r'FROM C:\Users\PC\.ollama\models\gemma-4-E4B-it-Q4_K_M.gguf')

add_body('Step 3 — Register it with Ollama:')
add_code(r'ollama create gemma4-4b -f "C:\Users\PC\.ollama\Modelfile-gemma4"')

add_body('Step 4 — Verify it appears and test tool calling:')
add_code(
    'ollama list   # should show gemma4-4b:latest\n'
    '\n'
    '# Test tool calling via OpenAI-compatible API:\n'
    'Invoke-RestMethod http://localhost:11434/v1/chat/completions -Method POST ...\n'
    '# finish_reason should be "tool_calls" for a news/current events question'
)
add_note(
    'Always test tool calling before wiring a new model into the n8n workflow. '
    'Not all GGUF models support function calling — verify with the test above first.'
)

add_h2('Switching Models in the Workflow')
add_body('Use the switch script inside the container, then Publish in n8n:')
add_code(
    'docker cp C:\\Users\\PC\\n8n-local\\switch_model.js n8n-local:/tmp/switch_model.js\n'
    'docker exec n8n-local node /tmp/switch_model.js'
)

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 11: How the Decision Works')

add_h2('Example 1: Simple Question')
add_code(
    'User: "what is 2 + 2?"\n'
    '        ↓\n'
    'GLM thinks: "Basic maths — I know this. No search needed."\n'
    'GLM returns: finish_reason = "stop"\n'
    '        ↓\n'
    'IF node → FALSE → Respond Directly\n'
    'Response: { output: "4", searched: false }\n'
    'Chatbot: 💡 Answered from knowledge'
)

add_h2('Example 2: Current Events')
add_code(
    'User: "latest news in Australia?"\n'
    '        ↓\n'
    'GLM thinks: "This needs current info. I will search."\n'
    'GLM returns: finish_reason = "tool_calls"\n'
    '  query: "latest Australia news May 2026"\n'
    '        ↓\n'
    'Filter Query: not blocked ✅\n'
    '        ↓\n'
    'SearXNG → Google/Bing/DuckDuckGo → 30 results\n'
    '        ↓\n'
    'GLM reads results → writes summary\n'
    'Response: { output: "Here are today\'s stories...", searched: true }\n'
    'Chatbot: 🔍 Searched the internet'
)

# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 14: ngrok — HTTPS Tunnel for External Access')
add_body('Some services like Telegram bots require an HTTPS URL to send data to n8n. '
         'ngrok creates a secure tunnel from the internet to your local machine.')

add_h2('Why ngrok is Needed')
add_code('Telegram servers  →  needs HTTPS  →  ngrok  →  localhost:5678  →  n8n')

add_h2('Your Permanent Static Domain')
add_body('ngrok provides one free static domain that never changes between restarts:')
add_code('https://prevailingly-bivariate-larhonda.ngrok-free.dev')
add_body('Start ngrok with this domain:')
add_code('ngrok http --domain=prevailingly-bivariate-larhonda.ngrok-free.dev 5678')

add_h2('Permanent URLs')
add_table(
    ['Purpose', 'URL'],
    [
        ('n8n editor (local)',   'http://localhost:5678'),
        ('n8n editor (public)', 'https://prevailingly-bivariate-larhonda.ngrok-free.dev'),
        ('Agent webhook',       'https://prevailingly-bivariate-larhonda.ngrok-free.dev/webhook/agent-local'),
    ]
)

add_h2('n8n docker-compose.yml with ngrok')
add_code(
    'environment:\n'
    '  - N8N_HOST=prevailingly-bivariate-larhonda.ngrok-free.dev\n'
    '  - N8N_PROTOCOL=https\n'
    '  - WEBHOOK_URL=https://prevailingly-bivariate-larhonda.ngrok-free.dev/\n'
    '  - N8N_TRUST_PROXY=true'
)

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 15: Automatic Startup Script')
add_body('A PowerShell script at C:\\Users\\PC\\n8n-local\\start-n8n.ps1 starts '
         'everything automatically on Windows login.')
add_body('What it does:')
add_bullet('Starts Docker containers (n8n + SearXNG)')
add_bullet('Kills any existing ngrok process')
add_bullet('Starts ngrok with the permanent static domain')
add_bullet('Verifies the tunnel is active and prints all URLs')

add_h2('Run Manually')
add_code('C:\\Users\\PC\\n8n-local\\start-n8n.ps1')

add_h2('Automatic Startup')
add_body('A shortcut in the Windows Startup folder runs it silently on every login:')
add_code(r'C:\Users\PC\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\HOITCS n8n Startup.lnk')

add_h2('After Every Restart — One Manual Step')
add_body('Toggle the Telegram workflow off then on in n8n to re-register the webhook URL with Telegram.')
add_note('Telegram stores the webhook URL on their servers. Even though the URL never changes '
         '(static domain), n8n must re-register it after each restart.')

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 16: Telegram Bot Workflow')
add_h2('Bot Details')
add_table(
    ['Setting', 'Value'],
    [
        ('Bot name',      'hoitcs n8n chatbot'),
        ('Bot username',  '@hoitcs_n8n_bot'),
        ('n8n workflow',  'telegraph'),
        ('Trigger mode',  'Polling (Pull in events from Telegram)'),
        ('Model',         'gemma4-4b:latest via Ollama'),
    ]
)

add_h2('Workflow Architecture')
add_code(
    'Telegram Trigger (polling)\n'
    '        ↓\n'
    'Build Ollama Request — injects date + search tool\n'
    '        ↓\n'
    'Call Ollama\n'
    '        ↓\n'
    'Needs Search? (IF finish_reason = "tool_calls")\n'
    '  ↓ YES                         ↓ NO\n'
    'Get Search Query           Extract Reply\n'
    '        ↓                        ↓\n'
    'Run Web Search          Send Telegram Reply\n'
    '        ↓\n'
    'Build Second Request\n'
    '        ↓\n'
    'Call Ollama with Results\n'
    '        ↓\n'
    'Extract Reply → Send Telegram Reply'
)

add_h2('System Prompt')
add_code(
    'You are a helpful assistant that answers questions with humour and wit.\n'
    'But make it accurate, use emojis and colourful language.\n'
    'Today is {today}.\n'
    'Use search_internet for current events, news, sport, weather.\n'
    'Use your own knowledge for timeless facts.'
)

add_h2('Important: Telegram Message Formatting')
add_body('The Send Telegram Reply node must NOT use Markdown parse mode. '
         'The LLM response contains emoji and symbols that break Telegram\'s Markdown parser.')
add_code(
    'additionalFields: {}   # NO parse_mode — send as plain text'
)
add_note('If you see "Bad Request: can\'t parse entities" errors, check that '
         'parse_mode is not set in the Send Telegram Reply node parameters.')

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Part 17: Web Search Tool (Reusable Sub-Workflow)')
add_body('A reusable n8n sub-workflow that any workflow can call to search the internet. '
         'Built once, usable everywhere.')

add_h2('How to Use It in Any Workflow')
add_bullet('Add an "Execute Workflow" node')
add_bullet('Select "Web Search Tool" as the target')
add_bullet('Pass input: { "query": "your search term" }')
add_bullet('Returns: { query, results: [{title, url, content}], count }')

add_h2('Internal Structure')
add_code(
    'Input (executeWorkflowTrigger v1)\n'
    '        ↓\n'
    'Validate Query\n'
    '  - Rejects empty queries\n'
    '  - Content blocklist (pornography, illegal content)\n'
    '        ↓\n'
    'Search SearXNG\n'
    '  GET http://host.docker.internal:8080/search\n'
    '        ↓\n'
    'Format Results\n'
    '  Returns top 5: title, url, content'
)

add_note('The trigger node must use typeVersion 1 (not 1.1). '
         'Version 1.1 requires input schema definition before publishing; '
         'version 1 accepts any data without a predefined schema.')

# ═══════════════════════════════════════════════════════════════════════════════
add_h1('Summary: Zero Cost, Fully Local')
add_table(
    ['Component', 'Technology', 'Cost'],
    [
        ('Workflow engine',  'n8n in Docker',            '$0'),
        ('LLM inference',    'Ollama + GLM 4.7 Flash',   '$0'),
        ('Web search',       'SearXNG in Docker',         '$0'),
        ('Search results',   'Google/Bing/DDG (via SearXNG)', '$0'),
        ('Total',            '',                          '$0'),
    ]
)
add_body('The only costs are electricity and your existing internet connection. '
         'No API keys, no subscriptions, no cloud bills.')

output = r'c:\Users\PC\OneDrive\Documents\claude\n8n\AI_Agent_Local_Documentation_v4.docx'
doc.save(output)
print('Saved:', output)
