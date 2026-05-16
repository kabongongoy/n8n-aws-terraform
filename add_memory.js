const crypto = require('crypto');
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/.pnpm/sqlite3@5.1.7/node_modules/sqlite3/lib/sqlite3.js');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');

function n8nId() {
  const c = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  return Array.from({length:16}, () => c[Math.floor(Math.random()*c.length)]).join('');
}
function nowStr() {
  return new Date().toISOString().replace('T',' ').replace('Z','').slice(0,23);
}

db.get("SELECT nodes, connections FROM workflow_entity WHERE name='local-ollama-agent'", (err, row) => {
  if (err || !row) { console.error('Workflow not found'); db.close(); return; }

  const nodes = JSON.parse(row.nodes);
  const connections = JSON.parse(row.connections);

  // ── 1. Update Build First Request to read memory ─────────────────────────
  const buildFirst = nodes.find(n => n.name === 'Build First Request');
  if (buildFirst) {
    const old = buildFirst.parameters.jsCode;

    // Inject memory reading at the top and include history in messages
    buildFirst.parameters.jsCode = `
// Read last 5 conversation pairs from persistent memory
const history = $workflow.staticData.conversationHistory || [];
const historyMessages = history.flatMap(h => [
  { role: 'user',      content: h.user },
  { role: 'assistant', content: h.assistant }
]);

const today = new Date().toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
const userMessage = $('Webhook').item.json.body.message;

const systemPrompt = \`You are a helpful assistant. Today's date is \${today}.
You have a search tool called search_internet for current, real-time information.
You have a translate_text tool for translating between English, Yoruba, Igbo, Hausa, and Japanese.
Use search_internet for current events, sports, news, prices, weather.
Use translate_text when asked to translate anything.
Use your own knowledge for timeless facts.
IMPORTANT: Refuse any request involving pornography, illegal activities, drugs, weapons, hate speech, or self-harm.\`;

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
        description: 'Search the internet for current, real-time information',
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
    console.log('Updated: Build First Request (now reads memory + includes history)');
  }

  // ── 2. Add Save Memory nodes before each respond node ────────────────────
  const saveMemoryJs = `
const userMessage   = $('Webhook').item.json.body.message;
const assistantReply = $input.item.json.choices[0].message.content
  .replace(/<think>[\\s\\S]*?<\\/think>/g, '').trim();

// Load existing history, add new exchange, keep last 5 pairs
const history = $workflow.staticData.conversationHistory || [];
history.push({ user: userMessage, assistant: assistantReply });
$workflow.staticData.conversationHistory = history.slice(-5);

// Pass through the original data unchanged
return [$input.item];
`;

  // Find positions of the three main Ollama response nodes
  const respondDirect   = nodes.find(n => n.name === 'Respond Directly');
  const respondSearch   = nodes.find(n => n.name === 'Respond with Search Answer');
  const respondTranslate = nodes.find(n => n.name === 'Respond with Translation');

  const saveDirect    = { id: n8nId(), name: 'Save Memory (Direct)',    type: 'n8n-nodes-base.code', typeVersion: 2, position: [respondDirect    ? respondDirect.position[0]    - 250 : 0, respondDirect    ? respondDirect.position[1]    : 0], parameters: { language: 'javaScript', jsCode: saveMemoryJs } };
  const saveSearch    = { id: n8nId(), name: 'Save Memory (Search)',    type: 'n8n-nodes-base.code', typeVersion: 2, position: [respondSearch    ? respondSearch.position[0]    - 250 : 0, respondSearch    ? respondSearch.position[1]    : 0], parameters: { language: 'javaScript', jsCode: saveMemoryJs } };
  const saveTranslate = { id: n8nId(), name: 'Save Memory (Translate)', type: 'n8n-nodes-base.code', typeVersion: 2, position: [respondTranslate ? respondTranslate.position[0] - 250 : 0, respondTranslate ? respondTranslate.position[1] : 0], parameters: { language: 'javaScript', jsCode: saveMemoryJs } };

  nodes.push(saveDirect, saveSearch, saveTranslate);

  // ── 3. Rewire: insert Save Memory nodes before each Respond node ─────────
  // Find what currently connects TO each respond node and redirect through Save Memory

  // Direct: "Needs Search?" FALSE branch → Save Memory (Direct) → Respond Directly
  connections['Needs Search?'].main[1] = [{ node: 'Save Memory (Direct)', type: 'main', index: 0 }];
  connections['Save Memory (Direct)'] = { main: [[{ node: 'Respond Directly', type: 'main', index: 0 }]] };

  // Search: "Send Results to Ollama" → Save Memory (Search) → Respond with Search Answer
  connections['Send Results to Ollama'] = { main: [[{ node: 'Save Memory (Search)', type: 'main', index: 0 }]] };
  connections['Save Memory (Search)']  = { main: [[{ node: 'Respond with Search Answer', type: 'main', index: 0 }]] };

  // Translation: "Send Translation to Ollama" → Save Memory (Translate) → Respond with Translation
  connections['Send Translation to Ollama'] = { main: [[{ node: 'Save Memory (Translate)', type: 'main', index: 0 }]] };
  connections['Save Memory (Translate)']    = { main: [[{ node: 'Respond with Translation', type: 'main', index: 0 }]] };

  console.log('Added: 3 Save Memory nodes (Direct / Search / Translate)');

  // ── 4. Save ───────────────────────────────────────────────────────────────
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
          else console.log('\n✅ Memory added — last 5 conversations will be remembered');
          db.close();
        });
    });
});
