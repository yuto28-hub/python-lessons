# Gmail API を使って、指定した宛先にメールを1通送るプログラム
# 認証は OAuth 2.0（課題1〜3とは別のスコープなので、トークンも別ファイル）
#
# 使い方:
#   python3 gmail_send.py 宛先メール "件名" "本文"
#   例: python3 gmail_send.py taro@example.com "課題5" "Gmail API から送りました。"
#
# 必要なライブラリ（課題1と同じ。追加は不要）:
#   pip3 install --user google-api-python-client google-auth-httplib2 google-auth-oauthlib
#
# 事前準備（初回のみ）は 課題1 フォルダの README.md を参照
#   ※ Google Cloud で「Gmail API」を有効にしておくこと
#   ※ 送れるのは、ブラウザで許可した自分のアカウントからだけ

import base64      # メール本文を API が求める形（URL-safe Base64）に変換する
import os          # 環境変数の読み取りやファイル権限の変更に使う標準ライブラリ
import sys         # コマンドラインの引数を受け取るための標準ライブラリ
import warnings    # 警告メッセージの表示を調整するための標準ライブラリ
from email.message import EmailMessage  # 件名と本文を正しいメールの形に組み立てる
from pathlib import Path

# Google製ライブラリが Python 3.9 に対して出す警告を隠す
# （※この2行は Google のライブラリを import する「前」に書く必要がある）
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*OpenSSL.*")

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ------------------------------------------------------------
# 設定
# ------------------------------------------------------------

CRED_DIR_ENV = "GDRIVE_CONFIG_DIR"
DEFAULT_CRED_DIR = "~/.config/gdrive"

CRED_FILE = "credentials.json"  # 課題1で配置したものをそのまま使う

# トークンは課題1〜3と別ファイル。スコープが違うと同じ token.json が使えなくなる
TOKEN_FILE = "token_gmail.json"

# gmail.send は「メールを送る」だけ。受信箱の閲覧や削除はできない最小限の権限
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

BAR = "=" * 45
THIN = "-" * 45


def get_cred_dir():
    """認証情報を置くフォルダのパスを返す（環境変数があればそちらを優先）"""

    raw = os.environ.get(CRED_DIR_ENV, DEFAULT_CRED_DIR)
    return Path(raw).expanduser()


def build_service():
    """OAuth認証を行い、Gmail APIを操作するオブジェクトを返す。失敗したら None を返す"""

    cred_dir = get_cred_dir()
    cred_path = cred_dir / CRED_FILE
    token_path = cred_dir / TOKEN_FILE

    creds = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except ValueError:
            print(f"※ {TOKEN_FILE} が読めなかったため、認証をやり直します")
            creds = None

    if creds is None or not creds.valid:
        if creds is not None and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("認証情報を自動更新しました")
            except RefreshError:
                print("※ 認証の期限が切れていたため、ブラウザで再認証します")
                creds = None

        if creds is None or not creds.valid:
            if not cred_path.exists():
                print(f"エラー: 認証ファイルが見つかりません（{cred_path}）")
                print("→ 課題1の README.md の手順1〜5を実行して credentials.json を配置してください")
                return None

            print("ブラウザを開いて Google アカウントの許可を求めます...")
            print("（メール送信だけの権限です。受信箱は読みません）")
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
            creds = flow.run_local_server(port=0)

        cred_dir.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        os.chmod(token_path, 0o600)
        print(f"認証情報を保存しました: {token_path}")

    return build("gmail", "v1", credentials=creds)


def build_raw_message(to_address, subject, body):
    """宛先・件名・本文から、APIに渡す raw 文字列を作る"""

    message = EmailMessage()
    message["To"] = to_address
    message["Subject"] = subject
    # From は付けない。Gmail が「許可したアカウント」を差出人にする
    message.set_content(body)

    # urlsafe_b64encode は「+」や「/」を使わない Base64。Gmail API はこの形を要求する
    encoded = base64.urlsafe_b64encode(message.as_bytes())
    return encoded.decode("utf-8")


def send_message(service, to_address, subject, body):
    """メールを1通送り、APIの返事（辞書）を返す"""

    raw = build_raw_message(to_address, subject, body)

    # userId="me" は「今許可している本人」という意味
    sent = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )
    return sent


def main():
    if len(sys.argv) < 4:
        print('使い方: python3 gmail_send.py 宛先メール "件名" "本文"')
        print('例    : python3 gmail_send.py taro@example.com "課題5" "Gmail API から送りました。"')
        return

    to_address = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]

    if "@" not in to_address:
        print(f"エラー: 宛先がメールアドレスの形ではありません（{to_address}）")
        return

    print(BAR)
    print("【課題5】Gmail でメールを送る")
    print(BAR)
    print(f"宛先 : {to_address}")
    print(f"件名 : {subject}")
    print(f"本文 : {body}")
    print(THIN)

    service = build_service()
    if service is None:
        return

    print(THIN)

    try:
        sent = send_message(service, to_address, subject, body)
    except HttpError as error:
        status = getattr(error.resp, "status", None)
        print("失敗しました")

        if status == 403:
            print("→ 権限またはAPIが有効になっていない可能性があります")
            print("　 Google Cloud で Gmail API が有効か確認してください")
        elif status == 401:
            print(f"→ 認証が無効です。{get_cred_dir() / TOKEN_FILE} を削除して再実行してください")
        elif status == 400:
            print(f"→ 宛先または本文に問題があります: {error}")
        else:
            print(f"→ APIエラー（状態コード: {status}）: {error}")

        return

    print("送信しました")
    print(f"メッセージID : {sent.get('id', '（不明）')}")
    print(BAR)
    print("差出人は、ブラウザで許可した Google アカウントです")


if __name__ == "__main__":
    main()
