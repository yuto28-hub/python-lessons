# Discord の Webhook で、特定チャンネルに通知を1件送るプログラム
# 課題文は「ボットを作成し、自動通知を送る」。ヒントどおり Webhook を使う。
# Webhook は、そのチャンネル専用の送信口で、常駐するボットプログラムは要らない。
# チャンネル側では、Webhook の名前でメッセージが届く。
#
# 使い方:
#   python3 discord_notify.py "メッセージ"
#   例: python3 discord_notify.py "課題8から通知しました"
#
# 追加ライブラリは不要（標準ライブラリだけ）
#
# 事前準備（初回のみ）:
#   1. Discord でサーバーを開き、通知先のチャンネルを選ぶ
#   2. チャンネル名の横の歯車 → 連携サービス → ウェブフック
#   3. 「新しいウェブフック」を作り、ウェブフックURLをコピーする
#      URL はそのチャンネルに結び付いている。別チャンネルには届かない
#   4. URL はリポジトリの外に置く。チャットやGitに貼らない
#
#        mkdir -p ~/.config/discord
#        printf 'DISCORD_WEBHOOK_URL=%s\n' 'https://discord.com/api/webhooks/...' \
#          > ~/.config/discord/webhook.env
#        chmod 600 ~/.config/discord/webhook.env

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CRED_DIR_ENV = "DISCORD_CONFIG_DIR"
DEFAULT_CRED_DIR = "~/.config/discord"
CRED_FILE = "webhook.env"
URL_ENV = "DISCORD_WEBHOOK_URL"

WEBHOOK_PREFIXES = (
    "https://discord.com/api/webhooks/",
    "https://discordapp.com/api/webhooks/",
    "https://canary.discord.com/api/webhooks/",
    "https://ptb.discord.com/api/webhooks/",
)

# Discord は User-Agent が無いリクエストを拒むことがある
USER_AGENT = "assignment-discord-webhook (python-urllib)"

# Webhook の本文は 2000 文字まで
MAX_CONTENT = 2000

BAR = "=" * 45
THIN = "-" * 45


def get_cred_dir():
    """Webhook URL を置くフォルダのパスを返す"""

    raw = os.environ.get(CRED_DIR_ENV, DEFAULT_CRED_DIR)
    return Path(raw).expanduser()


def load_webhook_url():
    """Webhook URL を返す。環境変数を優先し、無ければ設定ファイルを読む"""

    url = os.environ.get(URL_ENV, "").strip()
    if not url:
        cred_path = get_cred_dir() / CRED_FILE
        if not cred_path.exists():
            print("エラー: Webhook URL が見つかりません")
            print(f"→ 環境変数 {URL_ENV} を設定するか、次のファイルに保存してください")
            print(f"　 {cred_path}")
            print("　 中身は DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/... の1行です")
            return None

        for line in cred_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == URL_ENV:
                url = value.strip().strip('"').strip("'")

        if not url:
            print(f"エラー: {cred_path} に {URL_ENV} がありません")
            return None

    if not url.startswith(WEBHOOK_PREFIXES):
        print("エラー: Discord のウェブフックURLを入れてください")
        print("　 https://discord.com/api/webhooks/ で始まるものです")
        print("　 ボットトークンやサーバーIDでは通知できません")
        return None

    return url


def post_notification(url, text):
    """Webhook に通知を送り、Discord が返したメッセージ（辞書）を返す

    wait=true を付けると、204 ではなく作成されたメッセージが返る。
    届いたことの確認に、メッセージIDを表示できる。
    """

    separator = "&" if "?" in url else "?"
    target = f"{url}{separator}wait=true"
    body = json.dumps({"content": text}).encode("utf-8")
    request = urllib.request.Request(
        target,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
        if not raw:
            return {}
        return json.loads(raw)


def explain_http_error(error):
    """HTTPエラーを日本語にする。URL 自体は表示しない"""

    status = getattr(error, "code", None)
    detail = error.read().decode("utf-8", errors="replace")

    print("失敗しました")

    try:
        message = json.loads(detail).get("message", "")
    except json.JSONDecodeError:
        message = ""

    if status in (401, 404):
        print("→ ウェブフックURLが無効です。チャンネルの設定でURLをコピーし直してください")
        print("　 ウェブフックを削除したあとのURLも、このエラーになります")
    elif status == 429:
        print("→ 短時間に送りすぎです。少し待ってから再実行してください")
    else:
        print(f"→ APIエラー（状態コード: {status}）")
        if message:
            print(f"　 {message[:300]}")


def main():
    if len(sys.argv) < 2:
        print('使い方: python3 discord_notify.py "メッセージ"')
        print('例    : python3 discord_notify.py "課題8から通知しました"')
        return

    text = sys.argv[1]
    if not text.strip():
        print("エラー: メッセージが空です")
        return
    if len(text) > MAX_CONTENT:
        print(f"エラー: メッセージは {MAX_CONTENT} 文字までです")
        return

    print(BAR)
    print("【課題8】Discord へ通知を送る")
    print(BAR)
    print(f"本文 : {text}")
    print(THIN)

    url = load_webhook_url()
    if url is None:
        return

    try:
        result = post_notification(url, text)
    except urllib.error.HTTPError as error:
        explain_http_error(error)
        return
    except urllib.error.URLError as error:
        print("失敗しました")
        print(f"→ Discord に接続できません: {error.reason}")
        return

    print("通知しました")
    print(f"チャンネルID : {result.get('channel_id', '（不明）')}")
    print(f"メッセージID : {result.get('id', '（不明）')}")
    print(BAR)


if __name__ == "__main__":
    main()
