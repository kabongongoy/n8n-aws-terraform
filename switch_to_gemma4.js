const crypto = require('crypto');
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/.pnpm/sqlite3@5.1.7/node_modules/sqlite3/lib/sqlite3.js');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');

const NEW_MODEL = 'gemma4-4b:latest';

db.get("SELECT nodes FROM workflow_entity WHERE name='local-ollama-agent'", (err, row) => {
  if (err || !row) { console.error('Workflow not found'); db.close(); return; }

  const nodes = JSON.parse(row.nodes);
  let updated = 0;

  nodes.forEach(n => {
    if (n.parameters && n.parameters.jsCode) {
      // Replace any existing model name
      const oldCode = n.parameters.jsCode;
      const newCode = oldCode
        .replace(/glm-4\.7-flash:latest/g, NEW_MODEL)
        .replace(/llama3\.2:latest/g, NEW_MODEL)
        .replace(/qwen2\.5:7b/g, NEW_MODEL)
        .replace(/qwen\/qwen3-32b/g, NEW_MODEL);
      if (newCode !== oldCode) {
        n.parameters.jsCode = newCode;
        console.log('Updated model in:', n.name);
        updated++;
      }
    }
  });

  if (updated === 0) { console.log('No model references found to update'); db.close(); return; }

  const ver = crypto.randomUUID();
  const now = new Date().toISOString().replace('T', ' ').replace('Z', '').slice(0, 23);
  const nodesJson = JSON.stringify(nodes);

  db.run('UPDATE workflow_entity SET nodes=?, versionId=?, updatedAt=? WHERE name=?',
    [nodesJson, ver, now, 'local-ollama-agent'], err => {
      if (err) { console.error(err.message); db.close(); return; }

      db.run(`INSERT OR REPLACE INTO workflow_history
        (versionId, workflowId, authors, createdAt, updatedAt, nodes, connections)
        SELECT ?, id, 'Henry Faleye', ?, ?, ?, connections
        FROM workflow_entity WHERE name='local-ollama-agent'`,
        [ver, now, now, nodesJson], err => {
          if (err) console.error(err.message);
          else console.log('Done — switched to', NEW_MODEL);
          db.close();
        });
    });
});
