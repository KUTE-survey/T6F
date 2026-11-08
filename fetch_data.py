import json
import datetime
import urllib.request
import urllib.error
import os

api_key    = os.environ['API_KEY']
login_id   = os.environ['LOGIN_ID']
login_pass = os.environ['LOGIN_PASS']

# =============================================
# ★★★ フロアごとに変えるのはここだけ ★★★
# 4F: E28400EC / 5F: NTHのシリアルに変更 / 6F: E28400AF
TARGET_SERIAL = 'E28400AF'
# =============================================

JST = datetime.timezone(datetime.timedelta(hours=9))

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

target = None
for d in raw.get('devices', []):
    if d.get('serial') == TARGET_SERIAL:
        target = d
        break

if target is None:
    print('エラー: シリアル番号', TARGET_SERIAL, 'の機器が見つかりません')
    print('利用可能な機器:')
    for d in raw.get('devices', []):
        print('  ', d.get('name'), d.get('serial'))
    exit(1)

print('使用機器:', target.get('name'), target.get('serial'))

# センサーの最終通信時刻を確認（record_timeがある機器のみ）
record_time = target.get('record_time')
if record_time:
    try:
        sensor_time = datetime.datetime.fromtimestamp(int(record_time), tz=JST)
        now_check = datetime.datetime.now(JST)
        diff_minutes = (now_check - sensor_time).total_seconds() / 60
        print(f'センサー最終通信: {sensor_time.strftime("%H:%M")} ({diff_minutes:.0f}分前)')
        if diff_minutes > 30:
            print('最終通信が30分以上前のため書き込みをスキップします')
            exit(0)
    except (ValueError, TypeError):
        print('record_timeを解釈できません（時刻チェックをスキップ）')
else:
    print('record_timeが取得できません（時刻チェックをスキップ）')

channels = target.get('channel', [])

# 温度（必須）
try:
    temp = float(channels[0]['value'])
except (ValueError, TypeError, IndexError, KeyError):
    print('温度が取得できない(Communication Error等)ため前回の値を維持します')
    exit(0)

# 湿度（任意：2ch目がなければ None）
hum = None
try:
    hum = float(channels[1]['value'])
except (ValueError, TypeError, IndexError, KeyError):
    hum = None
    print('湿度は取得できませんでした（温度のみ記録します）')

now = datetime.datetime.now(JST)
today_str = now.strftime('%Y-%m-%d')

# 既存のdata.jsonを読み込んでhistoryを引き継ぐ
history = []
try:
    with open('data.json', encoding='utf-8') as f:
        existing = json.load(f)
    history = [h for h in existing.get('history', []) if h.get('date') == today_str]
    # 直近60件すべて同じ温度・湿度なら通信不良とみなしスキップ
    if len(history) >= 60:
        last = history[-60:]
        temps = {h.get('temp') for h in last}
        hums  = {h.get('hum') for h in last}
        if len(temps) == 1 and len(hums) == 1 and temp in temps and hum in hums:
            print('直近60件で値が変化していません。通信不良の可能性があるためスキップします')
            exit(0)
except Exception:
    history = []

entry = {'date': today_str, 'time': now.strftime('%H:%M'), 'temp': temp}
if hum is not None:
    entry['hum'] = hum
history.append(entry)
history = history[-300:]

out = {
    'temperature': temp,
    'humidity':    hum,
    'updated_at':  now.isoformat(),
    'history':     history
}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('完了: 温度', temp, '/ 湿度', hum)
