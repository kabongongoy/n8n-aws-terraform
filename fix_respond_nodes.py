import sqlite3, json, uuid
from datetime import datetime, timezone

def now_str():
    t = datetime.now(timezone.utc)
    return t.strftime('%Y-%m-%d %H:%M:%S.') + f'{t.microsecond // 1000:03d}'

db = sqlite3.connect('/opt/n8n/data/database.sqlite')
cur = db.cursor()

cur.execute("SELECT nodes, connections FROM workflow_entity WHERE id='oJsTkNqq1u7jDJfN'")
row = cur.fetchone()
nodes = json.loads(row[0])
conn = row[1]

# The expression uses $json which must be preserved
search_expr  = '={{ JSON.stringify({ output: $json.choices[0].message.content.replace(/<think>[\\s\\S]*?<\\/think>/g, "").trim(), searched: true }) }}'
direct_expr  = '={{ JSON.stringify({ output: $json.choices[0].message.content.replace(/<think>[\\s\\S]*?<\\/think>/g, "").trim(), searched: false }) }}'

for node in nodes:
    if node['name'] == 'Respond with Search Answer':
        node['parameters']['respondWith'] = 'json'
        node['parameters']['responseBody'] = search_expr
        print('Updated: Respond with Search Answer')
    if node['name'] == 'Respond Directly':
        node['parameters']['respondWith'] = 'json'
        node['parameters']['responseBody'] = direct_expr
        print('Updated: Respond Directly')

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
