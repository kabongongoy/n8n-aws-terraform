import sqlite3, json, uuid, random, string
from datetime import datetime, timezone

def now_str():
    t = datetime.now(timezone.utc)
    return t.strftime('%Y-%m-%d %H:%M:%S.') + f'{t.microsecond // 1000:03d}'

def n8n_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

GROQ_API_KEY = 'your-groq-api-key-here'
SYSTEM_PROMPT = 'You are a helpful assistant. You have a search tool called search_internet for current web information. Use it for recent events or real-time data. Answer directly for general knowledge.'

db = sqlite3.connect('/opt/n8n/data/database.sqlite')
cur = db.cursor()

cur.execute('SELECT id FROM user LIMIT 1')
user_id = cur.fetchone()[0]
cur.execute('SELECT projectId FROM project_relation WHERE userId=? LIMIT 1', (user_id,))
project_id = cur.fetchone()[0]

wf_id   = n8n_id()
now     = now_str()
ver     = str(uuid.uuid4())
wh_id   = str(uuid.uuid4())
wh_path = 'agent'

# Code node JS to build first Groq call body
build_first_call_js = """
const userMessage = $('Webhook').item.json.body.message;
const body = JSON.stringify({
  model: 'llama-3.3-70b-versatile',
  messages: [
    { role: 'system', content: '""" + SYSTEM_PROMPT + """' },
    { role: 'user',   content: userMessage }
  ],
  tools: [{
    type: 'function',
    function: {
      name: 'search_internet',
      description: 'Search the internet for current information, news, or real-time data',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'The search query' }
        },
        required: ['query']
      }
    }
  }],
  tool_choice: 'auto'
});
return [{ json: { body, userMessage } }];
"""

# Code node JS to build second Groq call body (with search results)
build_second_call_js = """
const userMessage = $('Webhook').item.json.body.message;
const firstResponse = $('Call Groq with Tools').item.json;
const searchResults = $input.item.json.results.slice(0, 3).map(r => ({
  title: r.title,
  url: r.url,
  content: r.content
}));

const body = JSON.stringify({
  model: 'llama-3.3-70b-versatile',
  messages: [
    { role: 'system', content: '""" + SYSTEM_PROMPT + """' },
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

nodes = [
    {
        "id": n8n_id(), "name": "Webhook",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2.1, "position": [-1000, 0],
        "parameters": {
            "httpMethod": "POST", "path": wh_path,
            "responseMode": "responseNode", "options": {}
        },
        "webhookId": wh_id
    },
    {
        "id": n8n_id(), "name": "Build First Request",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2, "position": [-700, 0],
        "parameters": {
            "language": "javaScript",
            "jsCode": build_first_call_js
        }
    },
    {
        "id": n8n_id(), "name": "Call Groq with Tools",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2, "position": [-400, 0],
        "parameters": {
            "method": "POST",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": "Bearer " + GROQ_API_KEY},
                {"name": "Content-Type",  "value": "application/json"}
            ]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": "={{ $json.body }}",
            "options": {}
        }
    },
    {
        "id": n8n_id(), "name": "Needs Search?",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2, "position": [-100, 0],
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [{
                    "leftValue":  "={{ $json.choices[0].finish_reason }}",
                    "rightValue": "tool_calls",
                    "operator":   {"type": "string", "operation": "equals"}
                }],
                "combinator": "and"
            },
            "options": {}
        }
    },
    {
        "id": n8n_id(), "name": "Get Search Query",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2, "position": [200, -200],
        "parameters": {
            "language": "javaScript",
            "jsCode": """
const toolCall = $input.item.json.choices[0].message.tool_calls[0];
const args = JSON.parse(toolCall.function.arguments);
return [{ json: { query: args.query, toolCallId: toolCall.id } }];
"""
        }
    },
    {
        "id": n8n_id(), "name": "Search SearXNG",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2, "position": [500, -200],
        "parameters": {
            "method": "GET",
            "url": "http://localhost:8080/search",
            "sendQuery": True,
            "queryParameters": {"parameters": [
                {"name": "q",        "value": "={{ $json.query }}"},
                {"name": "format",   "value": "json"},
                {"name": "language", "value": "en"}
            ]},
            "options": {}
        }
    },
    {
        "id": n8n_id(), "name": "Build Second Request",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2, "position": [800, -200],
        "parameters": {
            "language": "javaScript",
            "jsCode": build_second_call_js
        }
    },
    {
        "id": n8n_id(), "name": "Send Results to Groq",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2, "position": [1100, -200],
        "parameters": {
            "method": "POST",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": "Bearer " + GROQ_API_KEY},
                {"name": "Content-Type",  "value": "application/json"}
            ]},
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": "={{ $json.body }}",
            "options": {}
        }
    },
    {
        "id": n8n_id(), "name": "Respond with Search Answer",
        "type": "n8n-nodes-base.respondToWebhook",
        "typeVersion": 1.5, "position": [1400, -200],
        "parameters": {
            "respondWith": "json",
            "responseBody": "={{ JSON.stringify({ output: $json.choices[0].message.content, searched: true }) }}",
            "options": {}
        }
    },
    {
        "id": n8n_id(), "name": "Respond Directly",
        "type": "n8n-nodes-base.respondToWebhook",
        "typeVersion": 1.5, "position": [200, 150],
        "parameters": {
            "respondWith": "json",
            "responseBody": "={{ JSON.stringify({ output: $json.choices[0].message.content, searched: false }) }}",
            "options": {}
        }
    }
]

WH  = nodes[0]["name"]
BF  = nodes[1]["name"]
CG  = nodes[2]["name"]
IF  = nodes[3]["name"]
GQ  = nodes[4]["name"]
SX  = nodes[5]["name"]
BS  = nodes[6]["name"]
SR  = nodes[7]["name"]
RSA = nodes[8]["name"]
RD  = nodes[9]["name"]

connections = {
    WH:  {"main": [[{"node": BF,  "type": "main", "index": 0}]]},
    BF:  {"main": [[{"node": CG,  "type": "main", "index": 0}]]},
    CG:  {"main": [[{"node": IF,  "type": "main", "index": 0}]]},
    IF:  {"main": [
            [{"node": GQ,  "type": "main", "index": 0}],
            [{"node": RD,  "type": "main", "index": 0}]
          ]},
    GQ:  {"main": [[{"node": SX,  "type": "main", "index": 0}]]},
    SX:  {"main": [[{"node": BS,  "type": "main", "index": 0}]]},
    BS:  {"main": [[{"node": SR,  "type": "main", "index": 0}]]},
    SR:  {"main": [[{"node": RSA, "type": "main", "index": 0}]]}
}

nodes_json = json.dumps(nodes)
conn_json  = json.dumps(connections)

cur.execute("DELETE FROM webhook_entity WHERE webhookPath='agent'")
cur.execute("DELETE FROM shared_workflow WHERE workflowId IN (SELECT id FROM workflow_entity WHERE name='tool-calling-demo')")
cur.execute("DELETE FROM workflow_history WHERE workflowId IN (SELECT id FROM workflow_entity WHERE name='tool-calling-demo')")
cur.execute("DELETE FROM workflow_entity WHERE name='tool-calling-demo'")

cur.execute('''INSERT INTO workflow_entity
    (id, name, active, nodes, connections, settings, staticData, createdAt, updatedAt, versionId)
    VALUES (?,?,?,?,?,?,?,?,?,?)''',
    (wf_id, 'tool-calling-demo', 1,
     nodes_json, conn_json,
     json.dumps({"executionOrder": "v1"}),
     '{}', now, now, ver))

cur.execute('''INSERT INTO shared_workflow (workflowId, projectId, role, createdAt, updatedAt)
    VALUES (?,?,?,?,?)''', (wf_id, project_id, 'workflow:owner', now, now))

cur.execute('''INSERT INTO webhook_entity
    (workflowId, webhookPath, method, node, webhookId, pathLength)
    VALUES (?,?,?,?,?,?)''', (wf_id, wh_path, 'POST', 'Webhook', wh_id, None))

cur.execute('''INSERT INTO workflow_history
    (versionId, workflowId, authors, createdAt, updatedAt, nodes, connections, name, autosaved)
    VALUES (?,?,?,?,?,?,?,?,?)''',
    (ver, wf_id, 'Henry Faleye', now, now, nodes_json, conn_json, 'tool-calling-demo', 0))

db.commit()
db.close()
print('Created workflow ID:', wf_id)
print('Webhook: POST /webhook/agent')
