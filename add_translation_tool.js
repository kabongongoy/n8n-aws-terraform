/**
 * Adds a translate_text tool to the local-ollama-agent workflow.
 * Run inside the n8n container:
 *   docker cp add_translation_tool.js n8n-local:/tmp/add_translation_tool.js
 *   docker exec n8n-local node /tmp/add_translation_tool.js
 */
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

// ── Extract query from translation tool call arguments ────────────────────────
const getTranslationQueryJs = `
const toolCall = $input.item.json.choices[0].message.tool_calls[0];
const args = typeof toolCall.function.arguments === 'string'
  ? JSON.parse(toolCall.function.arguments)
  : toolCall.function.arguments;

// If it's a search call pass it through; if translation extract params
if (toolCall.function.name === 'translate_text') {
  return [{ json: {
    tool: 'translate_text',
    text: String(args.text || ''),
    from: String(args.from_language || 'en'),
    to:   String(args.to_language   || 'yo'),
    toolCallId: toolCall.id
  }}];
}

// Fallback: treat as search query
const query = args.query !== undefined ? String(args.query) : '';
return [{ json: { tool: 'search_internet', query, toolCallId: toolCall.id } }];
`;

// ── Route based on which tool was called ─────────────────────────────────────
const routeToolJs = `
const tool = $input.item.json.tool;
return [{ json: { ...$input.item.json, route: tool === 'translate_text' ? 1 : 0 } }];
`;

// ── Call MyMemory translation API ─────────────────────────────────────────────
// This is an HTTP Request node — no code needed, just config

// ── Build second Groq/Ollama call with translation result ─────────────────────
const buildTranslationResponseJs = `
const userMessage  = $('Webhook').item.json.body.message;
const firstResponse = $('Call Ollama with Tools').item.json;
const translationResult = $input.item.json;

const translated = translationResult.responseData
  ? translationResult.responseData.translatedText
  : 'Translation unavailable';

const LANG_NAMES = { en:'English', yo:'Yoruba', ig:'Igbo', ha:'Hausa', ja:'Japanese' };

const today = new Date().toLocaleDateString('en-AU', { weekday:'long', year:'numeric', month:'long', day:'numeric' });

const body = JSON.stringify({
  model: 'gemma4-4b:latest',
  messages: [
    { role: 'system', content: 'You are a helpful assistant. Today is ' + today + '. Answer clearly and concisely.' },
    { role: 'user', content: userMessage },
    { role: 'assistant', tool_calls: firstResponse.choices[0].message.tool_calls },
    {
      role: 'tool',
      tool_call_id: firstResponse.choices[0].message.tool_calls[0].id,
      content: 'Translation result: ' + translated
    }
  ]
});

return [{ json: { body } }];
`;

db.get("SELECT nodes, connections FROM workflow_entity WHERE name='local-ollama-agent'", (err, row) => {
  if (err || !row) { console.error('Workflow not found'); db.close(); return; }

  const nodes = JSON.parse(row.nodes);
  const connections = JSON.parse(row.connections);

  // ── Step 1: Update Build First Request to include translate_text tool ──────
  const buildFirstNode = nodes.find(n => n.name === 'Build First Request');
  if (buildFirstNode) {
    buildFirstNode.parameters.jsCode = buildFirstNode.parameters.jsCode.replace(
      "tools: [{\n    type: 'function',\n    function: {\n      name: 'search_internet',",
      `tools: [
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
  /*** KEEP ORIGINAL search_internet below — replaced above ***/
  _PLACEHOLDER: [{\n    type: 'function',\n    function: {\n      name: 'PLACEHOLDER',`
    );
    console.log('Updated: Build First Request (added translate_text tool)');
  }

  // ── Step 2: Add new nodes ──────────────────────────────────────────────────
  const translateNodeId  = n8nId();
  const translateResId   = n8nId();
  const translateReplyId = n8nId();
  const translateRespId  = n8nId();

  // Get position of Get Search Query node to place new nodes nearby
  const getQueryNode = nodes.find(n => n.name === 'Get Search Query');
  const pos = getQueryNode ? getQueryNode.position : [200, -200];

  const newNodes = [
    // Translate HTTP Request
    {
      id: translateNodeId, name: 'Call Translation API',
      type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
      position: [pos[0] + 300, pos[1] + 300],
      parameters: {
        method: 'GET',
        url: 'https://api.mymemory.translated.net/get',
        sendQuery: true,
        queryParameters: { parameters: [
          { name: 'q',        value: '={{ $json.text }}' },
          { name: 'langpair', value: '={{ $json.from + "|" + $json.to }}' }
        ]},
        options: {}
      }
    },
    // Build second call with translation result
    {
      id: translateResId, name: 'Build Translation Response',
      type: 'n8n-nodes-base.code', typeVersion: 2,
      position: [pos[0] + 600, pos[1] + 300],
      parameters: { language: 'javaScript', jsCode: buildTranslationResponseJs }
    },
    // Send to Ollama with translation result
    {
      id: translateReplyId, name: 'Send Translation to Ollama',
      type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
      position: [pos[0] + 900, pos[1] + 300],
      parameters: {
        method: 'POST',
        url: 'http://host.docker.internal:11434/v1/chat/completions',
        sendHeaders: true,
        headerParameters: { parameters: [{ name: 'Content-Type', value: 'application/json' }] },
        sendBody: true, contentType: 'raw', rawContentType: 'application/json',
        body: '={{ $json.body }}', options: {}
      }
    },
    // Respond with translation answer
    {
      id: translateRespId, name: 'Respond with Translation',
      type: 'n8n-nodes-base.respondToWebhook', typeVersion: 1.5,
      position: [pos[0] + 1200, pos[1] + 300],
      parameters: {
        respondWith: 'json',
        responseBody: '={{ JSON.stringify({ output: $json.choices[0].message.content.replace(/<think>[\\s\\S]*?<\\/think>/g, "").trim(), searched: false, translated: true }) }}',
        options: {}
      }
    }
  ];

  nodes.push(...newNodes);

  // ── Step 3: Update Get Search Query to also handle translate calls ──────────
  const gqNode = nodes.find(n => n.name === 'Get Search Query');
  if (gqNode) {
    gqNode.parameters.jsCode = `
const toolCall = $input.item.json.choices[0].message.tool_calls[0];
const args = typeof toolCall.function.arguments === 'string'
  ? JSON.parse(toolCall.function.arguments)
  : toolCall.function.arguments;

if (toolCall.function.name === 'translate_text') {
  return [{ json: {
    tool: 'translate_text',
    text: String(args.text || ''),
    from: String(args.from_language || 'en'),
    to:   String(args.to_language   || 'yo'),
    toolCallId: toolCall.id
  }}];
}

// Default: search query
const query = args.query !== undefined ? String(args.query) : '';
return [{ json: { tool: 'search_internet', query, toolCallId: toolCall.id } }];
`;
    console.log('Updated: Get Search Query (handles both tools)');
  }

  // ── Step 4: Update Filter Query to route to translate or search ─────────────
  const filterNode = nodes.find(n => n.name === 'Filter Query');
  if (filterNode) {
    filterNode.parameters.jsCode = `
// If it's a translation request, pass it through directly
if ($input.item.json.tool === 'translate_text') {
  return [{ json: { ...$input.item.json, blocked: false } }];
}

// Otherwise apply search blocklist
const blocklist = ['porn','pornography','xxx','nude','naked','sex video','explicit',
  'onlyfans','escort','how to make drugs','buy drugs','how to kill','bomb making','dark web','csam'];
const q = $input.item.json.query;
const query = (q !== undefined && q !== null) ? String(q).toLowerCase() : '';
const blocked = blocklist.some(w => query.includes(w));
if (blocked) return [{ json: { blocked: true, query, tool: 'search_internet',
  refusal: "I am sorry, I cannot search for that type of content." } }];
return [{ json: { blocked: false, query: String($input.item.json.query), toolCallId: $input.item.json.toolCallId, tool: 'search_internet' } }];
`;
    console.log('Updated: Filter Query (routes translate vs search)');
  }

  // ── Step 5: Add IF node for translation routing ─────────────────────────────
  const routeIfId = n8nId();
  const isBlockedNode = nodes.find(n => n.name === 'Is Blocked?');
  const ibPos = isBlockedNode ? isBlockedNode.position : [800, -200];

  const routeIfNode = {
    id: routeIfId, name: 'Is Translation?',
    type: 'n8n-nodes-base.if', typeVersion: 2.2,
    position: [ibPos[0] - 300, ibPos[1] + 150],
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
        conditions: [{
          leftValue: '={{ $json.tool }}', rightValue: 'translate_text',
          operator: { type: 'string', operation: 'equals' }
        }],
        combinator: 'and'
      },
      options: {}
    }
  };
  nodes.push(routeIfNode);

  // ── Step 6: Rewire connections ──────────────────────────────────────────────
  // Get Search Query → Is Translation? (instead of Filter Query)
  connections['Get Search Query'] = {
    main: [[{ node: 'Is Translation?', type: 'main', index: 0 }]]
  };

  // Is Translation?
  // TRUE (1) → Call Translation API
  // FALSE (0) → Filter Query (original search path)
  connections['Is Translation?'] = {
    main: [
      [{ node: 'Call Translation API', type: 'main', index: 0 }],
      [{ node: 'Filter Query',         type: 'main', index: 0 }]
    ]
  };

  // Call Translation API → Build Translation Response
  connections['Call Translation API'] = {
    main: [[{ node: 'Build Translation Response', type: 'main', index: 0 }]]
  };

  // Build Translation Response → Send Translation to Ollama
  connections['Build Translation Response'] = {
    main: [[{ node: 'Send Translation to Ollama', type: 'main', index: 0 }]]
  };

  // Send Translation to Ollama → Respond with Translation
  connections['Send Translation to Ollama'] = {
    main: [[{ node: 'Respond with Translation', type: 'main', index: 0 }]]
  };

  console.log('Connections rewired');

  // ── Save ────────────────────────────────────────────────────────────────────
  const ver = crypto.randomUUID();
  const now = nowStr();
  const nodesJson = JSON.stringify(nodes);
  const connJson  = JSON.stringify(connections);

  db.run(
    'UPDATE workflow_entity SET nodes=?, connections=?, versionId=?, updatedAt=? WHERE name=?',
    [nodesJson, connJson, ver, now, 'local-ollama-agent'],
    err => {
      if (err) { console.error('Save error:', err.message); db.close(); return; }

      db.run(
        `INSERT OR REPLACE INTO workflow_history
         (versionId, workflowId, authors, createdAt, updatedAt, nodes, connections)
         SELECT ?, id, 'Henry Faleye', ?, ?, ?, ?
         FROM workflow_entity WHERE name='local-ollama-agent'`,
        [ver, now, now, nodesJson, connJson],
        err => {
          if (err) console.error('History error:', err.message);
          else console.log('\n✅ Done — translate_text tool added to local-ollama-agent');
          db.close();
        }
      );
    }
  );
});
