const crypto = require('crypto');
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/.pnpm/sqlite3@5.1.7/node_modules/sqlite3/lib/sqlite3.js');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');

function nowStr() {
  return new Date().toISOString().replace('T',' ').replace('Z','').slice(0,23);
}

db.get("SELECT nodes, connections FROM workflow_entity WHERE name='local-ollama-agent'", (err, row) => {
  if (err || !row) { console.error('Not found'); db.close(); return; }

  const nodes = JSON.parse(row.nodes);
  const connections = JSON.parse(row.connections);

  const buildFirst = nodes.find(n => n.name === 'Build First Request');
  if (buildFirst) {
    buildFirst.parameters.jsCode = `
const body_data = $('Webhook').item.json.body;
const history   = body_data.history || [];

const historyMessages = history.flatMap(h => [
  { role: 'user',      content: h.user },
  { role: 'assistant', content: h.assistant }
]);

const today = new Date().toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
const userMessage = body_data.message;

const systemPrompt = 'You are a helpful assistant. Today is ' + today + '. ' +
  'You have a search tool called search_internet for current real-time information. ' +
  'You have a translate_text tool for translating between English, Yoruba, Igbo, Hausa, and Japanese. ' +
  'Use search_internet for current events, sports, news, prices, weather. ' +
  'Use translate_text when asked to translate anything. ' +
  'Use your own knowledge for timeless facts. ' +
  'IMPORTANT: Refuse any request involving pornography, illegal activities, drugs, weapons, hate speech.';

const body = JSON.stringify({
  model: 'gemma4-4b:latest',
  messages: [
    { role: 'system', content: systemPrompt },
    ...historyMessages,
    { role: 'user', content: userMessage }
  ],
  tools: [
    {
      type: 'function',
      function: {
        name: 'search_internet',
        description: 'Search the internet for current real-time information',
        parameters: {
          type: 'object',
          properties: { query: { type: 'string', description: 'The search query' } },
          required: ['query']
        }
      }
    },
    {
      type: 'function',
      function: {
        name: 'translate_text',
        description: 'Translate text between English, Yoruba, Igbo, Hausa, and Japanese',
        parameters: {
          type: 'object',
          properties: {
            text:          { type: 'string', description: 'The text to translate' },
            from_language: { type: 'string', description: 'Source language code: en, yo, ig, ha, ja' },
            to_language:   { type: 'string', description: 'Target language code: en, yo, ig, ha, ja' }
          },
          required: ['text', 'from_language', 'to_language']
        }
      }
    }
  ],
  tool_choice: 'auto'
});

return [{ json: { body, userMessage } }];
`;
    console.log('Updated: Build First Request with browser history + both tools');
  }

  const ver = crypto.randomUUID();
  const now = nowStr();
  const nodesJson = JSON.stringify(nodes);
  const connJson  = JSON.stringify(connections);

  db.run('UPDATE workflow_entity SET nodes=?, connections=?, versionId=?, updatedAt=? WHERE name=?',
    [nodesJson, connJson, ver, now, 'local-ollama-agent'], err => {
      if (err) { console.error(err.message); db.close(); return; }
      db.run(`INSERT OR REPLACE INTO workflow_history
        (versionId, workflowId, authors, createdAt, updatedAt, nodes, connections)
        SELECT ?, id, 'Henry Faleye', ?, ?, ?, ?
        FROM workflow_entity WHERE name='local-ollama-agent'`,
        [ver, now, now, nodesJson, connJson], err => {
          if (err) console.error(err.message);
          else console.log('Done');
          db.close();
        });
    });
});
