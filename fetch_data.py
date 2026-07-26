import json
import datetime
import urllib.request
import urllib.error
import os

api_key    = os.environ['API_KEY']
login_id   = os.environ['LOGIN_ID']
login_pass = os.environ['LOGIN_PASS']

body = json.dumps({
    'api-key':    api_key,
    'login-id':   login_id,
    'login-pass': login_pass
}).encode('utf-8')

req = urllib.request.Request(
    'https://api.webstorage.jp:443/v1/devices/current',
    data=body,
    headers={
        'Content-Type':           'application/json',
        'X-HTTP-Method-Override': 'GET'
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req) as res:
        raw = json.loads(res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('HTTPエラー:', e.code)
    print('エラー詳細:', e.read().decode('utf-8'))
    exit(1)

# ★★★ 使いたい機器のシリアル番号をここだけ変える ★★★
TARGET_SERIAL = 'E28400AF'
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★

target = None
for d in raw['devices']:
    if d.get('serial') == TARGET_SERIAL:
        target = d
        break

if target is None:
    print('エラー: シリアル番号', TARGET_SERIAL, 'の機器が見つかりません')
    exit(1)

print('使用機器:', target.get('name'), target.get('serial'))

try:
    temp = float(target['channel'][0]['value'])
    hum  = float(target['channel'][1]['value'])
except (ValueError, TypeError):
    print('Communication Errorのため終了します')
    exit(0)

# nowをここで定義
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
today_str = now.strftime('%Y-%m-%d')

try:
    existing = json.load(open('data.json'))
    history  = existing.get('history', [])
    # 今日の日付のデータだけ残す
    history = [h for h in history if h.get('date', today_str) == today_str]
except:
    history = []

history.append({
    'date': today_str,
    'time': now.strftime('%H:%M'),
    'temp': temp,
    'hum':  hum
})
history = history[-24:]

out = {
    'temperature':     temp,
    'humidity':        hum,
    'set_temperature': 28,
    'updated_at':      now.isoformat(),
    'history':         history
}

json.dump(out, open('data.json', 'w'), ensure_ascii=False, indent=2)
print('完了:', temp, hum)
