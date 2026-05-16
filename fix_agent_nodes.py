import sqlite3, json, uuid
from datetime import datetime, timezone

def now_str():
    t = datetime.now(timezone.utc)
    return t.strftime('%Y-%m-%d %H:%M:%S.') + f'{t.microsecond // 1000:03d}'

SYSTEM_PROMPT_1 = (
    "You are a helpful assistant. Today's date is ${today}. "
    "You have a search tool called search_internet to find current, real-time information from the web. "
    "Always use it when the user asks about current events, sports fixtures, scores, news, prices, weather, "
    "or anything time-sensitive. Use your own knowledge only for timeless facts."
)

SYSTEM_PROMPT_2 = (
    "You are a helpful assistant. Today's date is ${today}. "
    "Use the search results provided to give an accurate, up-to-date answer. "
    "Do not rely on your training data for time-sensitive information."
)

first_call_js = r"""
const today = new Date().toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
const userMessage = $('Webhook').item.json.body.message;

const systemPrompt = `""" + SYSTEM_PROMPT_1.replace('`', r'\`') + r"""`.replace('${today}', today);

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

const systemPrompt = `""" + SYSTEM_PROMPT_2.replace('`', r'\`') + r"""`.replace('${today}', today);

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

db = sqlite3.connect('/opt/n8n/data/database.sqlite')
cur = db.cursor()

cur.execute("SELECT nodes, connections FROM workflow_entity WHERE id='oJsTkNqq1u7jDJfN'")
row = cur.fetchone()
nodes = json.loads(row[0])
conn  = row[1]

for node in nodes:
    if node['name'] == 'Build First Request':
        node['parameters']['jsCode'] = first_call_js
        print('Updated: Build First Request')
    if node['name'] == 'Build Second Request':
        node['parameters']['jsCode'] = second_call_js
        print('Updated: Build Second Request')

now = now_str()
ver = str(uuid.uuid4())
nodes_json = json.dumps(nodes)

cur.execute("UPDATE workflow_entity SET nodes=?, versionId=?, updatedAt=? WHERE id='oJsTkNqq1u7jDJfN'",
    (nodes_json, ver, now))
cur.execute('''INSERT OR REPLACE INTO workflow_history
    (versionId, workflowId, authors, createdAt, updatedAt, nodes, connections, name, autosaved)
    VALUES (?,?,?,?,?,?,?,?,?)''',
    (ver, 'oJsTkNqq1u7jDJfN', 'Henry Faleye', now, now, nodes_json, conn, 'tool-calling-demo', 0))

db.commit()
db.close()
print('Done')
