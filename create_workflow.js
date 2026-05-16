const path = require('path');
const crypto = require('crypto');

// Find sqlite3 in n8n's node_modules
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/.pnpm/sqlite3@5.1.7/node_modules/sqlite3/lib/sqlite3.js');

const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');

function n8nId() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  return Array.from({length: 16}, () => chars[Math.floor(Math.random() * chars.length)]).join('');
}

function nowStr() {
  return new Date().toISOString().replace('T', ' ').replace('Z', '').slice(0, 23);
}

const OLLAMA_URL  = 'http://host.docker.internal:11434/v1/chat/completions';
const SEARXNG_URL = 'http://host.docker.internal:8080/search';
const MODEL       = 'llama3.2:latest';

const SP1 = "You are a helpful assistant. Today's date is ${today}. You have a search tool called search_internet for current, real-time information. Use it for current events, sports, news, prices, weather. Use your own knowledge for timeless facts. IMPORTANT: Refuse any request involving pornography, illegal activities, drugs, weapons, hate speech, or self-harm.";
const SP2 = "You are a helpful assistant. Today's date is ${today}. Use the search results to give an accurate answer. Never include inappropriate content from results.";

const firstCallJs = `
const today = new Date().toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
const userMessage = $('Webhook').item.json.body.message;
const systemPrompt = \`${SP1}\`.replace('\${today}', today);
const body = JSON.stringify({
  model: '${MODEL}',
  messages: [{ role: 'system', content: systemPrompt }, { role: 'user', content: userMessage }],
  tools: [{ type: 'function', function: { name: 'search_internet', description: 'Search the internet for current real-time information', parameters: { type: 'object', properties: { query: { type: 'string', description: 'The search query' } }, required: ['query'] } } }],
  tool_choice: 'auto'
});
return [{ json: { body, userMessage } }];
`.replace(/\$\{SP1\}/g, SP1).replace(/\$\{MODEL\}/g, MODEL);

const getQueryJs = `
const toolCall = $input.item.json.choices[0].message.tool_calls[0];
const args = JSON.parse(toolCall.function.arguments);
return [{ json: { query: args.query, toolCallId: toolCall.id } }];
`;

const filterJs = `
const blocklist = ['porn','pornography','xxx','nude','naked','sex video','explicit','onlyfans','escort','how to make drugs','buy drugs','how to kill','bomb making','dark web','csam'];
const query = $input.item.json.query.toLowerCase();
const blocked = blocklist.some(w => query.includes(w));
if (blocked) return [{ json: { blocked: true, query, refusal: "I'm sorry, I cannot search for that type of content." } }];
return [{ json: { blocked: false, query: $input.item.json.query, toolCallId: $input.item.json.toolCallId } }];
`;

const secondCallJs = `
const today = new Date().toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
const userMessage = $('Webhook').item.json.body.message;
const firstResponse = $('Call Ollama with Tools').item.json;
const searchResults = $input.item.json.results.slice(0, 5).map(r => ({ title: r.title, url: r.url, content: r.content }));
const systemPrompt = \`${SP2}\`.replace('\${today}', today);
const body = JSON.stringify({
  model: '${MODEL}',
  messages: [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userMessage },
    { role: 'assistant', tool_calls: firstResponse.choices[0].message.tool_calls },
    { role: 'tool', tool_call_id: firstResponse.choices[0].message.tool_calls[0].id, content: JSON.stringify(searchResults) }
  ]
});
return [{ json: { body } }];
`.replace(/\$\{SP2\}/g, SP2).replace(/\$\{MODEL\}/g, MODEL);

const refusalJs = `return [{ json: { choices: [{ message: { content: $input.item.json.refusal }, finish_reason: 'stop' }] } }];`;

const respondExpr = s => `={{ JSON.stringify({ output: $json.choices[0].message.content.replace(/<think>[\\s\\S]*?<\\/think>/g, "").trim(), searched: ${s} }) }}`;

const wfId  = n8nId();
const now   = nowStr();
const ver   = crypto.randomUUID();
const whId  = crypto.randomUUID();

const nodes = [
  { id: n8nId(), name: 'Webhook', type: 'n8n-nodes-base.webhook', typeVersion: 2.1, position: [-1000, 0],
    parameters: { httpMethod: 'POST', path: 'agent-local', responseMode: 'responseNode', options: {} }, webhookId: whId },
  { id: n8nId(), name: 'Build First Request', type: 'n8n-nodes-base.code', typeVersion: 2, position: [-700, 0],
    parameters: { language: 'javaScript', jsCode: firstCallJs } },
  { id: n8nId(), name: 'Call Ollama with Tools', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, position: [-400, 0],
    parameters: { method: 'POST', url: OLLAMA_URL, sendHeaders: true,
      headerParameters: { parameters: [{ name: 'Content-Type', value: 'application/json' }] },
      sendBody: true, contentType: 'raw', rawContentType: 'application/json', body: '={{ $json.body }}', options: {} } },
  { id: n8nId(), name: 'Needs Search?', type: 'n8n-nodes-base.if', typeVersion: 2.2, position: [-100, 0],
    parameters: { conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
      conditions: [{ leftValue: '={{ $json.choices[0].finish_reason }}', rightValue: 'tool_calls',
        operator: { type: 'string', operation: 'equals' } }], combinator: 'and' }, options: {} } },
  { id: n8nId(), name: 'Get Search Query', type: 'n8n-nodes-base.code', typeVersion: 2, position: [200, -200],
    parameters: { language: 'javaScript', jsCode: getQueryJs } },
  { id: n8nId(), name: 'Filter Query', type: 'n8n-nodes-base.code', typeVersion: 2, position: [500, -200],
    parameters: { language: 'javaScript', jsCode: filterJs } },
  { id: n8nId(), name: 'Is Blocked?', type: 'n8n-nodes-base.if', typeVersion: 2.2, position: [800, -200],
    parameters: { conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
      conditions: [{ leftValue: '={{ $json.blocked }}', rightValue: true,
        operator: { type: 'boolean', operation: 'true' } }], combinator: 'and' }, options: {} } },
  { id: n8nId(), name: 'Build Refusal', type: 'n8n-nodes-base.code', typeVersion: 2, position: [1100, -350],
    parameters: { language: 'javaScript', jsCode: refusalJs } },
  { id: n8nId(), name: 'Search SearXNG', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, position: [1100, -50],
    parameters: { method: 'GET', url: SEARXNG_URL, sendQuery: true,
      queryParameters: { parameters: [{ name: 'q', value: '={{ $json.query }}' }, { name: 'format', value: 'json' }, { name: 'language', value: 'en' }] }, options: {} } },
  { id: n8nId(), name: 'Build Second Request', type: 'n8n-nodes-base.code', typeVersion: 2, position: [1400, -50],
    parameters: { language: 'javaScript', jsCode: secondCallJs } },
  { id: n8nId(), name: 'Send Results to Ollama', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, position: [1700, -50],
    parameters: { method: 'POST', url: OLLAMA_URL, sendHeaders: true,
      headerParameters: { parameters: [{ name: 'Content-Type', value: 'application/json' }] },
      sendBody: true, contentType: 'raw', rawContentType: 'application/json', body: '={{ $json.body }}', options: {} } },
  { id: n8nId(), name: 'Respond with Search Answer', type: 'n8n-nodes-base.respondToWebhook', typeVersion: 1.5, position: [2000, -50],
    parameters: { respondWith: 'json', responseBody: respondExpr('true'), options: {} } },
  { id: n8nId(), name: 'Respond Refused', type: 'n8n-nodes-base.respondToWebhook', typeVersion: 1.5, position: [1400, -350],
    parameters: { respondWith: 'json', responseBody: respondExpr('false'), options: {} } },
  { id: n8nId(), name: 'Respond Directly', type: 'n8n-nodes-base.respondToWebhook', typeVersion: 1.5, position: [200, 150],
    parameters: { respondWith: 'json', responseBody: respondExpr('false'), options: {} } },
];

const [WH,BF,CG,IF,GQ,FQ,IB,BR,SX,BS,SR,RSA,RR,RD] = nodes.map(n => n.name);

const connections = {
  [WH]:  { main: [[{ node: BF,  type: 'main', index: 0 }]] },
  [BF]:  { main: [[{ node: CG,  type: 'main', index: 0 }]] },
  [CG]:  { main: [[{ node: IF,  type: 'main', index: 0 }]] },
  [IF]:  { main: [[{ node: GQ,  type: 'main', index: 0 }], [{ node: RD, type: 'main', index: 0 }]] },
  [GQ]:  { main: [[{ node: FQ,  type: 'main', index: 0 }]] },
  [FQ]:  { main: [[{ node: IB,  type: 'main', index: 0 }]] },
  [IB]:  { main: [[{ node: BR,  type: 'main', index: 0 }], [{ node: SX, type: 'main', index: 0 }]] },
  [BR]:  { main: [[{ node: RR,  type: 'main', index: 0 }]] },
  [SX]:  { main: [[{ node: BS,  type: 'main', index: 0 }]] },
  [BS]:  { main: [[{ node: SR,  type: 'main', index: 0 }]] },
  [SR]:  { main: [[{ node: RSA, type: 'main', index: 0 }]] },
};

const nodesJson = JSON.stringify(nodes);
const connJson  = JSON.stringify(connections);

db.serialize(() => {
  db.run("DELETE FROM webhook_entity WHERE webhookPath='agent-local'");
  db.run("DELETE FROM workflow_entity WHERE name='local-ollama-agent'");

  db.get("SELECT id FROM user LIMIT 1", (err, user) => {
    if (err || !user) { console.error('No user found - please finish n8n setup first'); db.close(); return; }

    db.get("SELECT projectId FROM project_relation WHERE userId=? LIMIT 1", [user.id], (err, proj) => {
      db.run(`INSERT INTO workflow_entity (id, name, active, nodes, connections, settings, staticData, createdAt, updatedAt, versionId)
              VALUES (?,?,?,?,?,?,?,?,?,?)`,
        [wfId, 'local-ollama-agent', 1, nodesJson, connJson,
         JSON.stringify({executionOrder:'v1'}), '{}', now, now, ver]);

      if (proj) {
        db.run(`INSERT INTO shared_workflow (workflowId, projectId, role, createdAt, updatedAt) VALUES (?,?,?,?,?)`,
          [wfId, proj.projectId, 'workflow:owner', now, now]);
      }

      db.run(`INSERT INTO webhook_entity (workflowId, webhookPath, method, node, webhookId, pathLength) VALUES (?,?,?,?,?,?)`,
        [wfId, 'agent-local', 'POST', 'Webhook', whId, null]);

      db.run(`INSERT INTO workflow_history (versionId, workflowId, authors, createdAt, updatedAt, nodes, connections) VALUES (?,?,?,?,?,?,?)`,
        [ver, wfId, 'Henry Faleye', now, now, nodesJson, connJson],
        (err) => {
          if (err) console.error('History error:', err.message);
          console.log('Workflow created:', wfId);
          console.log('Webhook: POST http://localhost:5678/webhook/agent-local');
          db.close();
        });
    });
  });
});
