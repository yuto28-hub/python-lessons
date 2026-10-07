# Zoom API を使って会議を作り、会議ID・パスワード・参加リンクを表示するプログラム
# 認証は Server-to-Server OAuth（ブラウザの許可は不要。アプリの鍵3つでトークンを取る）
#
# 使い方:
#   python3 zoom_create.py                  既定の議題で会議を作る
#   python3 zoom_create.py "朝会"            議題を指定して会議を作る
#
# 追加ライブラリは不要（標準ライブラリだけ）
#
# 事前準備（初回のみ）:
#   1. https://marketplace.zoom.us/ に Zoom アカウントでログイン
#   2. Develop → Build App →「Server-to-Server OAuth」を選んで作る
#   3. アプリの Information で Account ID / Client ID / Client Secret を控える
#   4. Scopes で会議の作成を許可する
#        画面が古い形式なら meeting:write:admin
#        新しい形式なら「Create a meeting for a user」（admin）
#   5. アプリを Activate する（有効化するまで API は 401 になる）
#   6. 鍵はリポジトリの外に置く
#
#        mkdir -p ~/.config/zoom
#        cat > ~/.config/zoom/credentials.env <<'EOF'
#        ZOOM_ACCOUNT_ID=控えたAccount ID
#        ZOOM_CLIENT_ID=控えたClient ID
#        ZOOM_CLIENT_SECRET=控えたClient Secret
#        ZOOM_USER_EMAIL=自分のZoomメールアドレス
#        EOF
#        chmod 600 ~/.config/zoom/credentials.env
#
#   Server-to-Server では「me」が使えない。会議の主催者をメールアドレスで指定する。

import base64       # Client ID と Secret を Basic 認証の形に変換する
import json         # APIの返事（JSON）を辞書に戻す
import os           # 環境変数の読み取りに使う
import sys          # コマンドラインの引数を受け取る
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# 認証情報の置き場所。課題1と同じく、リポジトリの外に置く
CRED_DIR_ENV = "ZOOM_CONFIG_DIR"
DEFAULT_CRED_DIR = "~/.config/zoom"
CRED_FILE = "credentials.env"

TOKEN_URL = "https://zoom.us/oauth/token"
API_BASE = "https://api.zoom.us/v2"

# type: 1 は「今すぐ入れる会議」。開始日時を決めなくてよい
MEETING_TYPE_INSTANT = 1

BAR = "=" * 45
THIN = "-" * 45


def get_cred_dir():
    """認証情報を置くフォルダのパスを返す（環境変数があればそちらを優先）"""

    raw = os.environ.get(CRED_DIR_ENV, DEFAULT_CRED_DIR)
    return Path(raw).expanduser()


def load_credentials():
    """Account ID / Client ID / Client Secret / 主催者メールを辞書で返す

    環境変数が優先。無ければ ~/.config/zoom/credentials.env を読む。
    ファイルの形は「名前=値」を1行ずつ。
    """

    names = (
        "ZOOM_ACCOUNT_ID",
        "ZOOM_CLIENT_ID",
        "ZOOM_CLIENT_SECRET",
        "ZOOM_USER_EMAIL",
    )

    # 4つとも環境変数にあれば、ファイルは読まない
    if all(os.environ.get(name, "").strip() for name in names):
        return {name: os.environ[name].strip() for name in names}

    cred_path = get_cred_dir() / CRED_FILE
    if not cred_path.exists():
        print("エラー: Zoomの認証情報が見つかりません")
        print(f"→ 次のファイルに4行で保存してください: {cred_path}")
        print("　 ZOOM_ACCOUNT_ID / ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET / ZOOM_USER_EMAIL")
        print("　 鍵の中身はチャットやGitに貼らないでください")
        return None

    values = {}
    for line in cred_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    missing = [name for name in names if not values.get(name)]
    if missing:
        print(f"エラー: {cred_path} に次がありません: {', '.join(missing)}")
        return None

    return {name: values[name] for name in names}


def get_access_token(creds):
    """Server-to-Server OAuth で、1時間有効なアクセストークンを取る"""

    # Basic 認証は「ID:秘密」を Base64 にした文字列を Authorization に載せる
    pair = f"{creds['ZOOM_CLIENT_ID']}:{creds['ZOOM_CLIENT_SECRET']}"
    basic = base64.b64encode(pair.encode("utf-8")).decode("ascii")

    # grant_type=account_credentials が「ユーザーの許可なしで、アプリとして取る」という意味
    body = urllib.parse.urlencode(
        {
            "grant_type": "account_credentials",
            "account_id": creds["ZOOM_ACCOUNT_ID"],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    token = payload.get("access_token")
    if not token:
        raise RuntimeError("アクセストークンが返事に含まれていません")

    return token


def create_meeting(token, host_email, topic):
    """主催者のメールアドレス宛に会議を作り、APIの返事（辞書）を返す"""

    # メールアドレスの @ はそのままでよい。パスに載せるので念のためエンコードする
    host = urllib.parse.quote(host_email)
    url = f"{API_BASE}/users/{host}/meetings"

    body = json.dumps(
        {
            "topic": topic,
            "type": MEETING_TYPE_INSTANT,
            # パスワードは指定しない。アカウントの設定に従って Zoom が発行する
            "settings": {
                "waiting_room": True,
                "join_before_host": False,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def explain_http_error(error):
    """HTTPエラーを日本語で説明する"""

    status = getattr(error, "code", None)
    detail = error.read().decode("utf-8", errors="replace")

    print("失敗しました")

    if status == 401:
        print("→ 認証が拒否されました。Client ID / Secret / Account ID を確認してください")
        print("　 アプリが Activate 済みかも確認してください")
    elif status == 400 and "me" in detail:
        print("→ Server-to-Server では me が使えません。ZOOM_USER_EMAIL を確認してください")
    elif status == 404:
        print("→ 主催者が見つかりません。ZOOM_USER_EMAIL がその Zoom アカウントのユーザーか確認してください")
    elif status == 403:
        print("→ 権限が足りません。アプリのスコープに会議の作成（meeting:write:admin など）があるか確認してください")
    else:
        print(f"→ APIエラー（状態コード: {status}）")

    # Zoom の返事は JSON なので、message だけ取り出して短く出す
    try:
        message = json.loads(detail).get("message", detail)
    except json.JSONDecodeError:
        message = detail

    if message:
        print(f"　 {message[:300]}")


def main():
    if len(sys.argv) >= 2:
        topic = sys.argv[1]
    else:
        topic = "課題4_APIで作成した会議"

    print(BAR)
    print("【課題4】Zoom 会議の作成")
    print(BAR)
    print(f"議題 : {topic}")
    print(THIN)

    creds = load_credentials()
    if creds is None:
        return

    print(f"主催者 : {creds['ZOOM_USER_EMAIL']}")
    print(THIN)

    try:
        token = get_access_token(creds)
        print("アクセストークンを取得しました")
        meeting = create_meeting(token, creds["ZOOM_USER_EMAIL"], topic)
    except urllib.error.HTTPError as error:
        explain_http_error(error)
        return
    except urllib.error.URLError as error:
        print("失敗しました")
        print(f"→ Zoom に接続できません: {error.reason}")
        return

    # 課題が求めている3つ。start_url は主催者用の秘密リンクなので出さない
    meeting_id = meeting.get("id", "（不明）")
    password = meeting.get("password") or "（返事にありません。アカウント設定でパスコード必須にしてください）"
    join_url = meeting.get("join_url", "（不明）")

    print(THIN)
    print("会議を作成しました")
    print(f"会議ID     : {meeting_id}")
    print(f"パスワード : {password}")
    print(f"参加リンク : {join_url}")
    print(BAR)


if __name__ == "__main__":
    main()
