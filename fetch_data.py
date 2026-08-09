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

# =============================================
# ★★★ フロアごとに変えるのはここだけ ★★★
TARGET_SERIAL = 'E28400AF'   # ← シリアル番号を変える
# =============================================

target = None
for d in raw['devices']:
    if d.get('serial') == TARGET_SERIAL:
        target = d
        break

if target is None:
    print('エラー: シリアル番号', TARGET_SERIAL, 'の機器が見つかりません')
    exit(1)

print('使用機器:', target.get('name'), target.get('serial'))

# センサーの最終通信時刻を確認（古いデータの書き込みを防ぐ）
record_time = target.get('record_time')
if record_time:
    sensor_time = datetime.datetime.fromtimestamp(
        int(record_time),
        tz=datetime.timezone(datetime.timedelta(hours=9))
    )
    now_check = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    diff_minutes = (now_check - sensor_time).total_seconds() / 60
    print(f'センサー最終通信: {sensor_time.strftime("%H:%M")} ({diff_minutes:.0f}分前)')
    if diff_minutes > 30:
        print(f'最終通信が{diff_minutes:.0f}分前のため書き込みをスキップします')
        exit(0)
else:
    print('record_timeが取得できません（チェックをスキップ）')

try:
    temp = float(target['channel'][0]['value'])
except (ValueError, TypeError, IndexError):
    print('温度のCommunication Errorのため前回の値を維持します')
    exit(0)

# nowをAPIアクセス成功後に定義
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
today_str = now.strftime('%Y-%m-%d')

# 既存のdata.jsonを読み込んでhistoryを引き継ぐ
try:
    with open('data.json') as f:
        existing = json.load(f)
    history = existing.get('history', [])
    # 今日のデータだけ残す（dateフィールドがないものは除外）
    history = [h for h in history if h.get('date') == today_str]
except Exception:
    history = []

history.append({
    'date': today_str,
    'time': now.strftime('%H:%M'),
    'temp': temp,
})
history = history[-300:]  # 最大300件（5分おき×1日分の余裕）

out = {
    'temperature': temp,
    'updated_at':  now.isoformat(),
    'history':     history
}

with open('data.json', 'w') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('完了:', temp)
