# Slack API で、指定したチャンネルにメッセージを1件投稿するプログラム
# 認証は Bot トークン（xoxb- で始まる文字列）
#
# 使い方:
#   python3 slack_post.py チャンネル "メッセージ"
#   例1: python3 slack_post.py "#general" "課題7から投稿しました"
#   例2: python3 slack_post.py C0123456789 "課題7から投稿しました"
#
# 追加ライブラリは不要（標準ライブラリだけ）
#
# 事前準備（初回のみ）:
#   1. https://api.slack.com/apps で Create New App → From scratch
#   2. OAuth & Permissions → Bot Token Scopes に chat:write を追加する
#      このスコープが無いと、トークンがあっても投稿できない
#   3. Install to Workspace を押し、Bot User OAuth Token（xoxb-）を控える
#   4. 投稿先チャンネルで /invite @アプリ名 を実行し、Bot を参加させる
#      参加していないチャンネルには書けない
#   5. トークンはリポジトリの外に置く
#
#        mkdir -p ~/.config/slack
#        printf 'SLACK_BOT_TOKEN=%s\n' 'xoxb-...' > ~/.config/slack/token.env
#        chmod 600 ~/.config/slack/token.env
#
#   トークンの中身はチャットやGitに貼らない。

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CRED_DIR_ENV = "SLACK_CONFIG_DIR"
DEFAULT_CRED_DIR = "~/.config/slack"
CRED_FILE = "token.env"
TOKEN_ENV = "SLACK_BOT_TOKEN"

POST_URL = "https://slack.com/api/chat.postMessage"

BAR = "=" * 45
THIN = "-" * 45


def get_cred_dir():
    """トークンを置くフォルダのパスを返す"""

    raw = os.environ.get(CRED_DIR_ENV, DEFAULT_CRED_DIR)
    return Path(raw).expanduser()


def load_token():
    """Botトークンを返す。環境変数を優先し、無ければ設定ファイルを読む"""

    token = os.environ.get(TOKEN_ENV, "").strip()
    if token:
        return token

    cred_path = get_cred_dir() / CRED_FILE
    if not cred_path.exists():
        print("エラー: Botトークンが見つかりません")
        print(f"→ 環境変数 {TOKEN_ENV} を設定するか、次のファイルに保存してください")
        print(f"　 {cred_path}")
        print("　 中身は SLACK_BOT_TOKEN=xoxb-... の1行です")
        return None

    token = ""
    for line in cred_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == TOKEN_ENV:
            token = value.strip().strip('"').strip("'")

    if not token:
        print(f"エラー: {cred_path} に {TOKEN_ENV} がありません")
        return None

    if not token.startswith("xoxb-"):
        print("エラー: Bot User OAuth Token（xoxb- で始まるもの）を入れてください")
        print("　 アプリの管理用トークン（xoxe- や xapp-）では投稿できません")
        return None

    return token


def post_message(token, channel, text):
    """チャンネルにメッセージを投稿し、APIの返事（辞書）を返す

    Slack は失敗しても HTTP 200 を返し、本文の ok が false になることがある。
    呼び出し側で ok を見る。
    """

    body = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        POST_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def explain_slack_error(error_code):
    """Slack が ok:false で返した理由を日本語にする"""

    print("失敗しました")

    if error_code == "invalid_auth":
        print("→ トークンが無効です。Bot User OAuth Token（xoxb-）を入れ直してください")
    elif error_code == "missing_scope":
        print("→ スコープが足りません。Bot Token Scopes に chat:write を追加し、")
        print("　 アプリを再インストールしてから、新しいトークンを保存してください")
    elif error_code == "not_in_channel":
        print("→ Bot がそのチャンネルに入っていません。チャンネルで /invite @アプリ名 を実行してください")
    elif error_code == "channel_not_found":
        print("→ チャンネルが見つかりません。チャンネルID（Cで始まる）か、#付きの名前を確認してください")
    elif error_code == "is_archived":
        print("→ そのチャンネルはアーカイブされています")
    else:
        print(f"→ Slackエラー: {error_code}")


def main():
    if len(sys.argv) < 3:
        print('使い方: python3 slack_post.py チャンネル "メッセージ"')
        print('例    : python3 slack_post.py "#general" "課題7から投稿しました"')
        return

    channel = sys.argv[1]
    text = sys.argv[2]

    print(BAR)
    print("【課題7】Slack へメッセージを投稿")
    print(BAR)
    print(f"チャンネル : {channel}")
    print(f"本文       : {text}")
    print(THIN)

    token = load_token()
    if token is None:
        return

    try:
        result = post_message(token, channel, text)
    except urllib.error.HTTPError as error:
        print("失敗しました")
        print(f"→ APIエラー（状態コード: {error.code}）")
        return
    except urllib.error.URLError as error:
        print("失敗しました")
        print(f"→ Slack に接続できません: {error.reason}")
        return

    if not result.get("ok"):
        explain_slack_error(result.get("error", "unknown"))
        return

    print("投稿しました")
    print(f"チャンネルID : {result.get('channel', '（不明）')}")
    print(f"時刻         : {result.get('ts', '（不明）')}")
    print(BAR)


if __name__ == "__main__":
    main()
