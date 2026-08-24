# -*- coding: utf-8 -*-
"""
酷狗插件 Token 管理服务（PC 版 v2）—— 支持扫码登录（中间人）
- GET  /login/qr      生成酷狗官方登录二维码（PNG），并启动后台轮询
- GET  /login/status  轮询状态: waiting / scanned / success
- GET  /token         返回配置 JSON（插件拉取）
- POST /save          手动保存配置（备用）
- GET  /              管理网页（扫码登录 + 手动配置）
用法: python token_server.py [端口，默认 8765]
"""
import json, os, sys, time, io, random, string, hashlib, uuid, threading
import urllib.request, urllib.parse
import http.server, socketserver

import qrcode  # pip install qrcode[pil]

VERSION = "0.2.0"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE, 'config.json')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'
KEY = "NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt"          # 酷狗签名密钥
QRCODE_H5 = "https://h5.kugou.com/apps/loginQRCode/html/index.html"
LOCK = threading.Lock()

# 当前登录会话状态
LOGIN = {'mid': '', 'dfid': '', 'code': '', 'state': 'idle',
         'userid': '', 'token': '', 'nickname': '', 'error': ''}

DEFAULT_CONFIG = {
    "userid": "", "token": "", "mid": "", "dfid": "", "updated_at": "",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    cfg['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------- 酷狗扫码登录（中间人）----------
def kg_sign(params):
    return hashlib.md5((KEY + "".join(f"{k}={params[k]}" for k in sorted(params)) + KEY).encode()).hexdigest()


def kg_get(base, extra):
    p = {'appid': '1014', 'srcappid': '2919', 'clientver': '20000',
         'clienttime': str(int(time.time() * 1000)), 'mid': LOGIN['mid'],
         'uuid': LOGIN['mid'], 'dfid': LOGIN['dfid'], 'plat': '4'}
    p.update(extra)
    if 'qrcode_txt' in p:
        p['qrcode_txt'] = urllib.parse.quote(p['qrcode_txt'], safe='')
    p['signature'] = kg_sign(p)
    url = base + '?' + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://www.kugou.com/'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8', 'ignore'))
    except Exception as e:
        return {'status': 0, 'error_code': 0, 'data': str(e)}


def gen_mid():
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()


def gen_dfid():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(25))


def start_login():
    """生成官方二维码 code，返回二维码内容"""
    with LOCK:
        LOGIN['mid'] = gen_mid()
        LOGIN['dfid'] = gen_dfid()
        LOGIN['state'] = 'idle'
        LOGIN['error'] = ''
    j = kg_get('https://login-user.kugou.com/v2/qrcode',
               {'type': '1', 'qrcode_txt': QRCODE_H5 + '?appid=1014&'})
    if j.get('status') != 1:
        with LOCK:
            LOGIN['state'] = 'fail'
            LOGIN['error'] = f"获取二维码失败: {j.get('data')}"
        return None
    code = j['data']['qrcode']
    with LOCK:
        LOGIN['code'] = code
        LOGIN['state'] = 'waiting'
    qr_content = f"{QRCODE_H5}?appid=1014&qrcode={code}&name={urllib.parse.quote('酷狗登录确认')}"
    threading.Thread(target=poll_login, daemon=True).start()
    return qr_content


def poll_login():
    """后台轮询登录状态: waiting -> scanned -> success"""
    code = LOGIN['code']
    for _ in range(150):  # 5 分钟
        j = kg_get('https://login-user.kugou.com/v2/get_userinfo_qrcode', {'qrcode': code})
        try:
            st = j.get('data', {}).get('status')
        except Exception:
            st = None
        if st == 2:
            with LOCK:
                LOGIN['state'] = 'scanned'
                LOGIN['nickname'] = j['data'].get('nickname', '')
                LOGIN['userid'] = str(j['data'].get('userid', ''))
        elif st == 4:
            data = j['data']
            with LOCK:
                LOGIN['state'] = 'success'
                LOGIN['userid'] = str(data.get('userid', ''))
                LOGIN['token'] = data.get('token', '')
                LOGIN['nickname'] = data.get('nickname', '')
            # 保存到配置（插件使用）
            cfg = load_config()
            cfg.update({'userid': LOGIN['userid'], 'token': LOGIN['token'],
                        'mid': LOGIN['mid'], 'dfid': LOGIN['dfid']})
            save_config(cfg)
            return
        elif st in (0, -1):
            with LOCK:
                LOGIN['state'] = 'fail'
                LOGIN['error'] = '二维码已过期或已取消'
            return
        time.sleep(2)
    with LOCK:
        LOGIN['state'] = 'fail'
        LOGIN['error'] = '登录超时'


# ---------- 管理网页 ----------
PAGE = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>酷狗 Token 管理</title>
<style>
body{font-family:system-ui;max-width:560px;margin:40px auto;padding:0 16px;background:#f5f6f8}
h1{font-size:20px} label{display:block;margin:12px 0 4px;font-size:13px;color:#444}
input{width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;box-sizing:border-box;font-family:monospace}
button{margin-top:10px;width:100%;padding:10px;background:#2f6fed;color:#fff;border:none;border-radius:6px;font-size:15px;cursor:pointer}
.card{background:#fff;border-radius:10px;padding:16px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
#qrArea{text-align:center;min-height:120px;padding:12px}
#qrImg{width:240px;height:240px;display:none;margin:0 auto}
#state{font-size:14px;margin-top:10px;color:#666}
#msg{margin-top:10px;font-size:13px;color:#2e7d32}
.hint{background:#fff8e1;border:1px solid #ffe082;padding:10px;border-radius:6px;font-size:12px;line-height:1.6;margin-top:12px}
</style></head><body>
<h1>酷狗 Token 管理（扫码登录）</h1>
<div class="card">
  <button id="loginBtn" onclick="startLogin()">📱 扫码登录</button>
  <div id="qrArea"><div id="state">点击上方按钮生成二维码</div><img id="qrImg"></div>
</div>
<div class="card">
  <h3>手动配置（备用）</h3>
  <form id="f">
    <label>userid</label><input name="userid" required>
    <label>token</label><input name="token" required>
    <label>mid</label><input name="mid" required>
    <label>dfid</label><input name="dfid" required>
    <button type="submit">保存 Token</button>
  </form>
  <div id="msg"></div>
  <div class="hint"><b>获取方式：</b>浏览器登录 www.kugou.com → F12 → Network → 找 wwwapi/gateway 请求，复制 URL 参数里的 userid/token/mid/dfid</div>
</div>
<script>
let pollTimer=null;
async function startLogin(){
  document.getElementById('state').textContent='正在生成二维码...';
  const r=await fetch('/login/qr');
  if(r.ok){
    document.getElementById('qrImg').src='/login/qr?t='+Date.now();
    document.getElementById('qrImg').style.display='block';
    document.getElementById('state').textContent='请用手机酷狗App扫码，然后在手机上确认登录';
    pollTimer=setInterval(pollStatus,2000);
  } else { document.getElementById('state').textContent='生成失败'; }
}
async function pollStatus(){
  const r=await fetch('/login/status'); const j=await r.json();
  if(j.state==='scanned') document.getElementById('state').textContent='已扫码，请在手机/确认页点【确认登录】...';
  else if(j.state==='success'){
    document.getElementById('state').textContent='✅ 登录成功：'+j.nickname+' (userid='+j.userid+')，token 已保存';
    clearInterval(pollTimer);
    ['userid','token','mid','dfid'].forEach(k=>{const el=document.querySelector('[name='+k+']'); if(el&&j[k])el.value=j[k];});
  } else if(j.state==='fail'){ document.getElementById('state').textContent='❌ '+j.error; clearInterval(pollTimer); }
}
fetch('/token').then(r=>r.json()).then(c=>{['userid','token','mid','dfid'].forEach(k=>{const el=document.querySelector('[name='+k+']'); if(el)el.value=c[k]||'';});});
document.getElementById('f').onsubmit=async e=>{
  e.preventDefault();
  const d=Object.fromEntries(new FormData(e.target));
  const r=await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
  document.getElementById('msg').textContent=await r.text();
};
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/token':
            self._json(load_config())
        elif path == '/login/qr':
            qr_content = start_login()
            if qr_content is None:
                with LOCK:
                    self._json({'error': LOGIN['error']}, 500)
                return
            img = qrcode.make(qr_content)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            data = buf.getvalue()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(data)))
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        elif path == '/login/status':
            with LOCK:
                self._json({'state': LOGIN['state'], 'userid': LOGIN['userid'],
                            'nickname': LOGIN['nickname'], 'token': LOGIN['token'],
                            'mid': LOGIN['mid'], 'dfid': LOGIN['dfid'],
                            'error': LOGIN['error']})
        else:
            body = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        path = self.path.split('?')[0]
        if path == '/save':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8', 'ignore')
            try:
                data = json.loads(raw)
                cfg = {k: str(data.get(k, '')).strip() for k in ('userid', 'token', 'mid', 'dfid')}
                save_config(cfg)
                self._json({'status': 'saved'})
            except Exception as e:
                self._json({'error': str(e)}, 400)


if __name__ == '__main__':
    with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
        print(f'酷狗 Token 服务已启动: http://127.0.0.1:{PORT}/  (Ctrl+C 停止)')
        httpd.serve_forever()
