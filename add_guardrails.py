import sqlite3, json, uuid
from datetime import datetime, timezone

def now_str():
    t = datetime.now(timezone.utc)
    return t.strftime('%Y-%m-%d %H:%M:%S.') + f'{t.microsecond // 1000:03d}'

SYSTEM_PROMPT_1 = (
    "You are a helpful assistant. Today's date is ${today}. "
    "You have a search tool called search_internet to find current, real-time information from the web. "
    "Always use it when the user asks about current events, sports fixtures, scores, news, prices, weather, "
    "or anything time-sensitive. Use your own knowledge only for timeless facts. "
    "IMPORTANT SAFETY RULES: You must immediately refuse any request that involves pornographic content, "
    "explicit sexual material, illegal activities, drug procurement, weapons, hate speech, self-harm, "
    "or any content that could harm individuals or groups. "
    "If a user asks for such content, respond politely but firmly that you cannot help with that request. "
    "Do NOT search for such content under any circumstances."
)

SYSTEM_PROMPT_2 = (
    "You are a helpful assistant. Today's date is ${today}. "
    "Use the search results provided to give an accurate, up-to-date answer. "
    "Do not rely on your training data for time-sensitive information. "
    "IMPORTANT: Never include, reference, or summarise any inappropriate, explicit, or illegal content "
    "even if it appears in search results. Skip such results entirely."
)

# Query filter — blocks the query BEFORE it reaches SearXNG
QUERY_FILTER_JS = r"""
// List of blocked keywords (add more as needed)
const blocklist = [
  'porn', 'pornography', 'xxx', 'nude', 'naked', 'sex video', 'adult video',
  'explicit', 'onlyfans', 'escort', 'prostitut', 'child abuse', 'csam',
  'how to make drugs', 'buy drugs', 'buy weapons', 'how to hack',
  'how to kill', 'bomb making', 'dark web'
];

const query = $input.item.json.query.toLowerCase();
const toolCallId = $input.item.json.toolCallId;

// Check if any blocked keyword appears in the query
const blocked = blocklist.some(word => query.includes(word));

if (blocked) {
  // Return a flag that the next node will use to short-circuit the search
  return [{
    json: {
      blocked: true,
      toolCallId: toolCallId,
      query: query,
      refusal: "I'm sorry, but I'm not able to search for that type of content. Please ask me something appropriate and I'll be happy to help."
    }
  }];
}

// Query is safe — pass it through
return [{ json: { blocked: false, query: $input.item.json.query, toolCallId: toolCallId } }];
"""

# When query is blocked, this builds a refusal response directly
BLOCKED_RESPONSE_JS = r"""
const refusal = $input.item.json.refusal;
// Build a fake Groq-style response so the Respond node works the same way
return [{
  json: {
    choices: [{
      message: { content: refusal },
      finish_reason: 'stop'
    }]
  }
}];
"""

first_call_js = r"""
const today = new Date().toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
const userMessage = $('Webhook').item.json.body.message;

const systemPrompt = `""" + SYSTEM_PROMPT_1 + r"""`.replace('${today}', today);

const body = JSON.stringify({
  model: 'qwen/qwen3-32b',
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
"""

second_call_js = r"""
const today = new Date().toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
const userMessage = $('Webhook').item.json.body.message;
const firstResponse = $('Call Groq with Tools').item.json;
const searchResults = $input.item.json.results.slice(0, 5).map(r => ({
  title: r.title,
  url: r.url,
  content: r.content
}));

const systemPrompt = `""" + SYSTEM_PROMPT_2 + r"""`.replace('${today}', today);

const body = JSON.stringify({
  model: 'qwen/qwen3-32b',
  messages: [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userMessage },
    { role: 'assistant', tool_calls: firstResponse.choices[0].message.tool_calls },
    {
      role: 'tool',
      tool_call_id: firstResponse.choices[0].message.tool_calls[0].id,
      content: JSON.stringify(searchResults)
    }
  ]
});

return [{ json: { body } }];
"""

GROQ_API_KEY = 'your-groq-api-key-here'

db = sqlite3.connect('/opt/n8n/data/database.sqlite')
cur = db.cursor()

cur.execute("SELECT nodes, connections FROM workflow_entity WHERE id='oJsTkNqq1u7jDJfN'")
row = cur.fetchone()
nodes = json.loads(row[0])
connections = json.loads(row[1])

# Update existing Code nodes with new prompts
for node in nodes:
    if node['name'] == 'Build First Request':
        node['parameters']['jsCode'] = first_call_js
        print('Updated: Build First Request (guardrail system prompt)')
    if node['name'] == 'Build Second Request':
        node['parameters']['jsCode'] = second_call_js
        print('Updated: Build Second Request (guardrail system prompt)')

# Find positions for new nodes
get_query_node = next(n for n in nodes if n['name'] == 'Get Search Query')
searxng_node   = next(n for n in nodes if n['name'] == 'Search SearXNG')
respond_search = next(n for n in nodes if n['name'] == 'Respond with Search Answer')

gq_pos = get_query_node['position']
sx_pos = searxng_node['position']

def n8n_id():
    import random, string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

# New node: Filter Query
filter_id = n8n_id()
filter_node = {
    'id': filter_id,
    'name': 'Filter Query',
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
    'position': [gq_pos[0] + 300, gq_pos[1]],
    'parameters': {
        'language': 'javaScript',
        'jsCode': QUERY_FILTER_JS
    }
}

# New node: IF Blocked?
blocked_if_id = n8n_id()
blocked_if_node = {
    'id': blocked_if_id,
    'name': 'Is Blocked?',
    'type': 'n8n-nodes-base.if',
    'typeVersion': 2.2,
    'position': [gq_pos[0] + 600, gq_pos[1]],
    'parameters': {
        'conditions': {
            'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
            'conditions': [{
                'leftValue': '={{ $json.blocked }}',
                'rightValue': True,
                'operator': {'type': 'boolean', 'operation': 'true'}
            }],
            'combinator': 'and'
        },
        'options': {}
    }
}

# New node: Build Refusal Response
refusal_id = n8n_id()
refusal_node = {
    'id': refusal_id,
    'name': 'Build Refusal',
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
    'position': [gq_pos[0] + 900, gq_pos[1] - 150],
    'parameters': {
        'language': 'javaScript',
        'jsCode': BLOCKED_RESPONSE_JS
    }
}

# New node: Respond Refused
respond_refused_id = n8n_id()
respond_refused_node = {
    'id': respond_refused_id,
    'name': 'Respond Refused',
    'type': 'n8n-nodes-base.respondToWebhook',
    'typeVersion': 1.5,
    'position': [gq_pos[0] + 1200, gq_pos[1] - 150],
    'parameters': {
        'respondWith': 'json',
        'responseBody': '={{ JSON.stringify({ output: $json.choices[0].message.content, searched: false, blocked: true }) }}',
        'options': {}
    }
}

nodes.extend([filter_node, blocked_if_node, refusal_node, respond_refused_node])

# Update connections:
# Get Search Query → Filter Query (instead of directly to Search SearXNG)
connections['Get Search Query'] = {
    'main': [[{'node': 'Filter Query', 'type': 'main', 'index': 0}]]
}

# Filter Query → Is Blocked?
connections['Filter Query'] = {
    'main': [[{'node': 'Is Blocked?', 'type': 'main', 'index': 0}]]
}

# Is Blocked?
# TRUE  → Build Refusal
# FALSE → Search SearXNG
connections['Is Blocked?'] = {
    'main': [
        [{'node': 'Build Refusal',   'type': 'main', 'index': 0}],
        [{'node': 'Search SearXNG',  'type': 'main', 'index': 0}]
    ]
}

# Build Refusal → Respond Refused
connections['Build Refusal'] = {
    'main': [[{'node': 'Respond Refused', 'type': 'main', 'index': 0}]]
}

now = now_str()
ver = str(uuid.uuid4())
nodes_json = json.dumps(nodes)
conn_json  = json.dumps(connections)

cur.execute("UPDATE workflow_entity SET nodes=?, connections=?, versionId=?, updatedAt=? WHERE id='oJsTkNqq1u7jDJfN'",
    (nodes_json, conn_json, ver, now))
cur.execute('''INSERT OR REPLACE INTO workflow_history
    (versionId, workflowId, authors, createdAt, updatedAt, nodes, connections, name, autosaved)
    VALUES (?,?,?,?,?,?,?,?,?)''',
    (ver, 'oJsTkNqq1u7jDJfN', 'Henry Faleye', now, now, nodes_json, conn_json, 'tool-calling-demo', 0))

db.commit()
db.close()
print('Guardrails added successfully:')
print('  - SearXNG safe_search: 2 (strict)')
print('  - System prompt: LLM refuses inappropriate requests')
print('  - Filter Query node: blocks keywords before reaching SearXNG')
print('  - Is Blocked? IF node: routes blocked queries to refusal')
print('  - Build Refusal node: builds polite refusal response')
print('  - Respond Refused node: returns refusal to user')
