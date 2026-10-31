# LINE Messaging API で、公式アカウントからテキストを1件送るプログラム
# 認証はチャネルアクセストークン（長期）。送り先はユーザーID
#
# 使い方:
#   python3 line_send.py "メッセージ"
#   例: python3 line_send.py "課題9から送りました"
#
# 追加ライブラリは不要（標準ライブラリだけ）
#
# 事前準備（初回のみ）:
#   1. LINE公式アカウントを作る
#      https://account.line.biz/signup
#   2. LINE Official Account Manager で Messaging API を有効にする
#      https://manager.line.biz/
#   3. LINE Developers コンソールの「Messaging API設定」で
#      チャネルアクセストークン（長期）を発行する
#      https://developers.line.biz/console/
#   4. 同じ画面の QR コードで、その公式アカウントを自分の LINE に友だち追加する
#      友だちでない相手には届かない
#   5. 「チャネル基本設定」の「あなたのユーザーID」（U で始まる）を控える
#   6. トークンとユーザーIDはリポジトリの外に置く。チャットやGitに貼らない
#
#        mkdir -p ~/.config/line
#        cat > ~/.config/line/token.env << 'EOF'
#        LINE_CHANNEL_ACCESS_TOKEN=長期トークン
#        LINE_USER_ID=Uから始まるID
#        EOF
#        chmod 600 ~/.config/line/token.env
#
# Webhook URL は空のままでよい。このスクリプトは返事を待たず、こちらから送る。

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CRED_DIR_ENV = "LINE_CONFIG_DIR"
DEFAULT_CRED_DIR = "~/.config/line"
CRED_FILE = "token.env"
TOKEN_ENV = "LINE_CHANNEL_ACCESS_TOKEN"
USER_ENV = "LINE_USER_ID"

PUSH_URL = "https://api.line.me/v2/bot/message/push"

# ユーザーIDは U のあとに16進が32文字
USER_ID_PATTERN = re.compile(r"^U[0-9a-f]{32}$")

# テキストメッセージは 5000 文字まで
MAX_TEXT = 5000

BAR = "=" * 45
THIN = "-" * 45


def get_cred_dir():
    """トークンを置くフォルダのパスを返す"""

    raw = os.environ.get(CRED_DIR_ENV, DEFAULT_CRED_DIR)
    return Path(raw).expanduser()


def load_credentials():
    """チャネルアクセストークンとユーザーIDを返す。足りなければ None"""

    values = {
        TOKEN_ENV: os.environ.get(TOKEN_ENV, "").strip(),
        USER_ENV: os.environ.get(USER_ENV, "").strip(),
    }

    if not values[TOKEN_ENV] or not values[USER_ENV]:
        cred_path = get_cred_dir() / CRED_FILE
        if not cred_path.exists():
            print("エラー: 認証情報が見つかりません")
            print(f"→ 次のファイルに2行で保存してください")
            print(f"　 {cred_path}")
            print(f"　 {TOKEN_ENV}=長期のチャネルアクセストークン")
            print(f"　 {USER_ENV}=Uで始まるユーザーID")
            return None

        for line in cred_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in values and not values[key]:
                values[key] = value.strip().strip('"').strip("'")

    token = values[TOKEN_ENV]
    user_id = values[USER_ENV]

    if not token or not user_id:
        print("エラー: トークンとユーザーIDの両方が必要です")
        print(f"　 {TOKEN_ENV} と {USER_ENV} を設定してください")
        return None

    if USER_ID_PATTERN.fullmatch(token):
        print("エラー: トークンの欄にユーザーIDが入っています")
        print("　 チャネルアクセストークン（長期）は、Messaging API設定で発行した長い文字列です")
        return None

    if not USER_ID_PATTERN.fullmatch(user_id):
        print("エラー: ユーザーIDは U で始まる33文字です")
        print("　 チャネル基本設定の「あなたのユーザーID」を入れてください")
        print("　 チャネルシークレットや LINE ID では送れません")
        return None

    return token, user_id


def push_text(token, user_id, text):
    """ユーザーにテキストを1件送り、APIの返事（辞書）を返す

    成功すると HTTP 200 で、中身は空の JSON オブジェクトになる。
    """

    body = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": text}]}
    ).encode("utf-8")
    request = urllib.request.Request(
        PUSH_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
        if not raw:
            return {}
        return json.loads(raw)


def explain_http_error(error):
    """HTTPエラーを日本語にする。トークン自体は表示しない"""

    status = getattr(error, "code", None)
    detail = error.read().decode("utf-8", errors="replace")

    print("失敗しました")

    try:
        payload = json.loads(detail)
        message = payload.get("message", "")
    except json.JSONDecodeError:
        message = ""

    if status == 401:
        print("→ チャネルアクセストークンが無効です")
        print("　 Messaging API設定の「チャネルアクセストークン（長期）」を発行し直してください")
    elif status == 400 and "user" in message.lower():
        print("→ ユーザーIDが無効か、その公式アカウントを友だち追加していません")
        print("　 Messaging API設定の QR コードから、自分の LINE に追加してください")
    elif status == 400:
        print("→ リクエストが拒否されました")
        if message:
            print(f"　 {message[:300]}")
    elif status == 403:
        print("→ このチャネルではプッシュ送信ができません")
        print("　 Messaging API が有効か、メッセージ通数の上限に達していないかを確認してください")
    elif status == 429:
        print("→ 短時間に送りすぎです。少し待ってから再実行してください")
    else:
        print(f"→ APIエラー（状態コード: {status}）")
        if message:
            print(f"　 {message[:300]}")


def main():
    if len(sys.argv) < 2:
        print('使い方: python3 line_send.py "メッセージ"')
        print('例    : python3 line_send.py "課題9から送りました"')
        return

    text = sys.argv[1]
    if not text.strip():
        print("エラー: メッセージが空です")
        return
    if len(text) > MAX_TEXT:
        print(f"エラー: メッセージは {MAX_TEXT} 文字までです")
        return

    print(BAR)
    print("【課題9】LINE へメッセージを送る")
    print(BAR)
    print(f"本文 : {text}")
    print(THIN)

    credentials = load_credentials()
    if credentials is None:
        return
    token, user_id = credentials

    try:
        push_text(token, user_id, text)
    except urllib.error.HTTPError as error:
        explain_http_error(error)
        return
    except urllib.error.URLError as error:
        print("失敗しました")
        print(f"→ LINE に接続できません: {error.reason}")
        return

    print("送信しました")
    print(f"ユーザーID : {user_id}")
    print(BAR)


if __name__ == "__main__":
    main()
