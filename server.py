from flask import Flask, request, jsonify, render_template_string
import os, json
import psycopg

app = Flask(__name__)
DATABASE_URL = os.environ.get('DATABASE_URL', '')

def db(): return psycopg.connect(DATABASE_URL)

def init_db():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS signals (id BIGSERIAL PRIMARY KEY, payload JSONB NOT NULL, received_at TIMESTAMPTZ NOT NULL DEFAULT NOW())')

def save_signal(payload):
    init_db()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO signals (payload) VALUES (%s::jsonb)', (json.dumps(payload),))

def load_signals(limit=100):
    init_db()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT payload, received_at FROM signals ORDER BY id DESC LIMIT %s', (limit,))
            rows=cur.fetchall()
    result=[]
    for payload, received in rows:
        item=dict(payload); item['received_at']=received.isoformat(); result.append(item)
    return result

@app.get('/health')
def health():
    try:
        init_db(); return {'ok': True, 'database': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}, 500

@app.post('/webhook')
def webhook():
    payload=request.get_json(silent=True)
    if payload is None:
        raw=request.get_data(as_text=True)
        try: payload=json.loads(raw)
        except Exception: payload={'message':raw}
    if not isinstance(payload,dict): payload={'message':payload}
    save_signal(payload)
    return {'ok':True}

@app.get('/api/signals')
def api_signals(): return jsonify(load_signals())

@app.get('/')
def dashboard():
    html='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Trend Scanner Dashboard</title><style>body{margin:0;background:#07111d;color:#f5f7fb;font-family:system-ui,-apple-system,Segoe UI,sans-serif}.wrap{max-width:1100px;margin:auto;padding:32px}.muted{color:#9fb1c7}.card{background:#0e1c2b;border:1px solid #23384f;border-radius:16px;padding:18px;margin:12px 0}.row{display:grid;grid-template-columns:1.2fr .9fr .7fr .7fr .9fr;gap:12px;align-items:center}.score{font-size:24px;font-weight:800}.green{color:#49e6ad}.red{color:#ff7c7c}.pill{display:inline-block;padding:5px 9px;border-radius:999px;border:1px solid #23384f}.top{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:24px}h1{margin:0;font-size:42px}small{color:#9fb1c7}@media(max-width:760px){.row{grid-template-columns:1fr 1fr}.top{align-items:start;flex-direction:column}}</style></head><body><div class="wrap"><div class="top"><div><h1>AI Trend Scanner</h1><div class="muted">TradingView webhook dashboard</div></div><div class="pill" id="count">Loading…</div></div><div id="list"></div></div><script>function prettyTime(v){if(!v)return '';const d=new Date(v);return isNaN(d)?v:d.toLocaleString();}async function load(){const r=await fetch('/api/signals');const data=await r.json();document.getElementById('count').textContent=data.length+' recent signals';const list=document.getElementById('list');list.innerHTML='';if(!data.length){list.innerHTML='<div class="card muted">No TradingView signals received yet.</div>';return}data.forEach(s=>{const raw=(s.signal||s.direction||s.side||'').toString().toUpperCase();const dir=raw==='LONG'?'STRONG LONG':raw==='SHORT'?'STRONG SHORT':raw;const cls=dir.includes('LONG')?'green':dir.includes('SHORT')?'red':'';const div=document.createElement('div');div.className='card';div.innerHTML=`<div class="row"><div><b>${s.symbol||s.ticker||'Market'}</b><br><small>${s.timeframe||s.interval||''}</small></div><div class="${cls}"><b>${dir||s.alert||s.message||'Signal'}</b></div><div><small>Setup</small><div class="score">${s.setup_score??s.setupScore??'-'}</div></div><div><small>Trend</small><div class="score">${s.trend_score??s.trendScore??'-'}</div></div><div><small>Received</small><br><small>${prettyTime(s.received_at)}</small></div></div>`;list.appendChild(div);});}load();setInterval(load,15000);</script></body></html>'''
    return render_template_string(html)

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
