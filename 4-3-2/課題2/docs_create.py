# Google ドキュメント API を使って、新しいドキュメントを作成し
# 指定したテキストを挿入するプログラム
# 認証は OAuth 2.0（課題1で取得した token.json をそのまま利用）
#
# 使い方:
#   python3 docs_create.py [挿入したいテキスト]
#   例1（既定の文章）  : python3 docs_create.py
#   例2（文章を指定）  : python3 docs_create.py "議事録のたたき台"
#
# 必要なライブラリ:
#   pip3 install --user google-api-python-client google-auth-httplib2 google-auth-oauthlib
#
# 事前準備（初回のみ）は 課題1 フォルダの README.md を参照
#   ※ Google Cloud で Google Docs API を有効にしておくこと

import os         # 環境変数の読み取りやファイル権限の変更に使う標準ライブラリ
import sys        # コマンドラインの引数を受け取るための標準ライブラリ
import warnings   # 警告メッセージの表示を調整するための標準ライブラリ
from pathlib import Path  # ファイルのパスを扱いやすくする標準ライブラリ

# Google製ライブラリは Python 3.9 に対して「古いバージョンです」という警告を大量に出す。
# 動作には影響がなく、本来の表示が埋もれて読みにくくなるので隠しておく。
# （※この2行は Google のライブラリを import する「前」に書く必要がある）
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*OpenSSL.*")

# --- Google が用意しているライブラリ群 ---
from google.auth.exceptions import RefreshError          # 認証の期限切れエラー
from google.auth.transport.requests import Request       # 認証の自動更新に使う
from google.oauth2.credentials import Credentials        # 保存済みの認証情報を読む
from google_auth_oauthlib.flow import InstalledAppFlow   # ブラウザを開いて許可をもらう
from googleapiclient.discovery import build              # APIの窓口を作る
from googleapiclient.errors import HttpError             # API通信のエラー

# ------------------------------------------------------------
# 設定（ファイル名などをここにまとめておくと後から変更しやすい）
# ------------------------------------------------------------

# 認証情報の置き場所。GitHubに公開されないよう「リポジトリの外」に置くのが鉄則
# 環境変数 GDRIVE_CONFIG_DIR を設定すれば置き場所を変更できる
CRED_DIR_ENV = "GDRIVE_CONFIG_DIR"
DEFAULT_CRED_DIR = "~/.config/gdrive"

CRED_FILE = "credentials.json"  # 自分で用意するファイル（GCPからダウンロードする）
TOKEN_FILE = "token.json"       # 初回の認証後にプログラムが自動で作るファイル

# 権限の範囲（スコープ）。drive.file は「このプログラムが作ったファイルだけ」
# 触れる最小限の権限。Docs API もこの権限で作成・編集ができる
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

BAR = "=" * 45   # 見出し用の太い区切り線
THIN = "-" * 45  # 中身用の細い区切り線


def get_cred_dir():
    """認証情報を置くフォルダのパスを返す（環境変数があればそちらを優先）"""

    # os.environ.get は「環境変数があればその値、なければ第2引数」を返す命令
    raw = os.environ.get(CRED_DIR_ENV, DEFAULT_CRED_DIR)

    # expanduser() は「~」を実際のホームフォルダのパスに展開する
    return Path(raw).expanduser()


def build_service():
    """OAuth認証を行い、Docs APIを操作するオブジェクトを返す。失敗したら None を返す"""

    cred_dir = get_cred_dir()
    cred_path = cred_dir / CRED_FILE    # 「/」でパスをつなげるのが pathlib の書き方
    token_path = cred_dir / TOKEN_FILE

    creds = None  # 認証情報を入れる変数。まだ何も無いので None にしておく

    # --- 手順1: 前回の認証情報（token.json）が残っていれば読み込む ---
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except ValueError:
            # ファイルが壊れている場合は読み飛ばして、後で作り直す
            print(f"※ {TOKEN_FILE} が読めなかったため、認証をやり直します")
            creds = None

    # --- 手順2: 認証情報が無い、または期限切れなら取得し直す ---
    if creds is None or not creds.valid:

        # 期限切れでも「更新用の鍵（refresh_token）」があれば自動で更新できる
        if creds is not None and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("認証情報を自動更新しました")
            except RefreshError:
                print("※ 認証の期限が切れていたため、ブラウザで再認証します")
                creds = None

        # 更新できなかった場合は、ブラウザを開いて一から許可をもらう
        if creds is None or not creds.valid:
            if not cred_path.exists():
                print(f"エラー: 認証ファイルが見つかりません（{cred_path}）")
                print("→ 課題1の README.md の手順1〜5を実行して credentials.json を配置してください")
                return None

            print("ブラウザを開いて Google アカウントの許可を求めます...")
            # from_client_secrets_file で「どのアプリとして許可を求めるか」を読み込む
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
            # run_local_server は一時的に小さなサーバーを立ててブラウザの応答を受け取る
            # port=0 は「空いているポートを自動で選ぶ」という意味
            creds = flow.run_local_server(port=0)

        # --- 手順3: 次回はブラウザ不要にするため、認証情報を保存する ---
        cred_dir.mkdir(parents=True, exist_ok=True)  # フォルダが無ければ作る
        token_path.write_text(creds.to_json(), encoding="utf-8")
        # chmod 0o600 は「自分だけが読み書きできる」という権限。他人に見られないようにする
        os.chmod(token_path, 0o600)
        print(f"認証情報を保存しました: {token_path}")

    # --- 手順4: 認証情報を使って Docs API の窓口を作る ---
    return build("docs", "v1", credentials=creds)


def create_doc(service, title):
    """空のドキュメントを作り、そのIDを返す"""

    # documents().create() が「新しいドキュメントを作る」命令
    # body に渡せるのはタイトルだけ。中身はここでは入れられない
    doc = service.documents().create(body={"title": title}).execute()

    # 作成結果の中に documentId というキーで ID が入っている
    doc_id = doc["documentId"]

    print(f"ドキュメントを作成しました: {title}")
    print(f"  ID: {doc_id}")

    return doc_id


def insert_text(service, doc_id, text):
    """指定したドキュメントの先頭にテキストを挿入する"""

    # requests は「やってほしいこと」のリスト。1回の通信で複数の指示を送れる
    # 1つでも不正な指示があると全体が失敗し、何も適用されない
    requests = [
        {
            "insertText": {
                # index: 1 が本文の先頭。0 は文書の始まりを示す目印で書き込めない
                "location": {"index": 1},
                "text": text,
            }
        }
    ]

    # batchUpdate が「ドキュメントに変更を加える」命令
    # documentId でどのドキュメントか、body で何をするかを指定する
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()

    print("テキストを挿入しました")


def main():
    # sys.argv には実行時の引数が入る。argv[0] はプログラム自身の名前
    # 引数があればそれを本文にする。無ければ既定の文章を使う
    if len(sys.argv) >= 2:
        text = sys.argv[1]
    else:
        text = "Google ドキュメント API から挿入したテキストです。"

    title = "課題2_APIで作成したドキュメント"

    print(BAR)
    print("【課題2】Google ドキュメントの作成とテキスト挿入")
    print(BAR)
    print(f"タイトル : {title}")
    print(f"本文     : {text}")
    print(THIN)

    # 認証してAPIの窓口を用意する
    service = build_service()
    if service is None:   # 認証に失敗していたら、ここで終了する
        return

    print(THIN)

    # API通信はここから。失敗したら HttpError が飛んでくる
    try:
        doc_id = create_doc(service, title)
        insert_text(service, doc_id, text)

    except HttpError as e:
        # status_code で原因を切り分けて日本語で説明する
        status = getattr(e.resp, "status", None)
        print("失敗しました")

        if status == 403:
            print("→ 権限またはAPIが有効になっていない可能性があります")
            print("　 Google Cloud で Google Docs API が有効か確認してください")
        elif status == 404:
            print("→ 指定したドキュメントが見つかりません")
        elif status == 401:
            print(f"→ 認証が無効です。{get_cred_dir() / TOKEN_FILE} を削除して再実行してください")
        else:
            print(f"→ APIエラー（状態コード: {status}）: {e}")

        return

    # 成功した場合は、ブラウザで開けるURLを表示する
    print(THIN)
    print("完了しました。以下のURLで開けます")
    print(f"  https://docs.google.com/document/d/{doc_id}/edit")
    print(BAR)


# このファイルを直接実行したときだけ main() を動かすおまじない
if __name__ == "__main__":
    main()