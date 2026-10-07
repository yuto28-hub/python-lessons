# ローカルのファイルを Google Drive API を使って Google ドライブにアップロードするプログラム
# 認証は OAuth 2.0（初回だけブラウザで許可 → 2回目以降は自動）
#
# 使い方:
#   python3 drive_upload.py <ファイルまたはフォルダのパス>
#   例1（ファイル1つ）  : python3 drive_upload.py ../../4-3-1/課題3/課題3_円グラフ.png
#   例2（フォルダ一括）  : python3 drive_upload.py ../../4-3-1/課題3
#
# 必要なライブラリ:
#   pip3 install --user google-api-python-client google-auth-httplib2 google-auth-oauthlib
#
# 事前準備（初回のみ）は同じフォルダの README.md を参照

import mimetypes  # ファイルの種類（画像/テキストなど）を拡張子から判定する標準ライブラリ
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
from googleapiclient.discovery import build              # Drive APIの窓口を作る
from googleapiclient.errors import HttpError             # API通信のエラー
from googleapiclient.http import MediaFileUpload         # ファイル送信の部品

# ------------------------------------------------------------
# 設定（ファイル名などをここにまとめておくと後から変更しやすい）
# ------------------------------------------------------------

# 認証情報の置き場所。GitHubに公開されないよう「リポジトリの外」に置くのが鉄則
# 環境変数 GDRIVE_CONFIG_DIR を設定すれば置き場所を変更できる
CRED_DIR_ENV = "GDRIVE_CONFIG_DIR"
DEFAULT_CRED_DIR = "~/.config/gdrive"

CRED_FILE = "credentials.json"  # 自分で用意するファイル（GCPからダウンロードする）
TOKEN_FILE = "token.json"       # 初回の認証後にプログラムが自動で作るファイル

# アップロード先フォルダのID。未設定ならマイドライブの直下に入る（設定は任意）
FOLDER_ID_ENV = "GDRIVE_FOLDER_ID"

# 権限の範囲（スコープ）。drive.file は「このプログラムが作ったファイルだけ」
# 触れる最小限の権限。既存ファイルを勝手に読まれる心配がないので安全
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# 拡張子から種類が判定できなかったときに使う汎用の種類
DEFAULT_MIME = "application/octet-stream"

BAR = "=" * 45   # 見出し用の太い区切り線
THIN = "-" * 45  # 中身用の細い区切り線


def get_cred_dir():
    """認証情報を置くフォルダのパスを返す（環境変数があればそちらを優先）"""

    # os.environ.get は「環境変数があればその値、なければ第2引数」を返す命令
    raw = os.environ.get(CRED_DIR_ENV, DEFAULT_CRED_DIR)

    # expanduser() は「~」を実際のホームフォルダのパスに展開する
    return Path(raw).expanduser()


def build_service():
    """OAuth認証を行い、Drive APIを操作するオブジェクトを返す。失敗したら None を返す"""

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
                print("→ README.md の手順1〜5を実行して credentials.json を配置してください")
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

    # --- 手順4: 認証情報を使って Drive API の窓口を作る ---
    return build("drive", "v3", credentials=creds)


def collect_targets(arg):
    """引数のパスから、アップロードするファイルの一覧を作って返す。対象が無ければ空リスト"""

    target = Path(arg).expanduser()

    if not target.exists():
        print(f"エラー: 指定されたパスが見つかりません（{target}）")
        print("→ パスの綴りが正しいか、実行しているフォルダの位置を確認してください")
        return []

    # ファイルが直接指定された場合は、それ1つだけのリストにする
    if target.is_file():
        return [target]

    # フォルダが指定された場合は、その中のファイルを集める
    files = []
    for path in sorted(target.iterdir()):   # sorted で名前順に並べる
        if not path.is_file():
            continue                        # 中のフォルダは対象外（1階層だけ扱う）
        if path.name.startswith("."):
            continue                        # .DS_Store などの隠しファイルは除外
        files.append(path)

    if not files:
        print(f"エラー: フォルダの中にアップロードできるファイルがありません（{target}）")
        print("→ 中身が空でないか確認してください")

    return files


def upload_file(service, path, folder_id):
    """1つのファイルをアップロードする。成功したら True、失敗したら False を返す"""

    # 拡張子から種類を判定する。guess_type は (種類, 圧縮方式) の2つを返すので [0] を使う
    mime_type = mimetypes.guess_type(path.name)[0] or DEFAULT_MIME

    # body はファイルにつける情報。name は Drive 上での表示名になる
    body = {"name": path.name}

    # 保存先フォルダが指定されている時だけ parents を付ける
    # 付けない場合はマイドライブの直下に入る
    if folder_id:
        body["parents"] = [folder_id]

    # resumable=True にすると、大きいファイルでも分割して確実に送れる
    media = MediaFileUpload(str(path), mimetype=mime_type, resumable=True)

    try:
        # files().create() が「新しいファイルを作る」命令
        # fields には「結果として何を返してほしいか」を指定する
        result = service.files().create(
            body=body,
            media_body=media,
            fields="id, name, webViewLink",
        ).execute()

    except HttpError as e:
        # API側が返したエラー。status_code で原因を切り分けて日本語で説明する
        status = getattr(e.resp, "status", None)
        print(f"失敗しました: {path.name}")

        if status == 403:
            print("→ 権限または保存容量の問題です。Drive の空き容量を確認してください")
        elif status == 404:
            print("→ 指定した保存先フォルダが見つかりません。GDRIVE_FOLDER_ID を確認してください")
        elif status == 401:
            print(f"→ 認証が無効です。{get_cred_dir() / TOKEN_FILE} を削除して再実行してください")
        else:
            print(f"→ APIエラー（状態コード: {status}）: {e}")

        return False

    except OSError as e:
        # ファイルが読めない、通信が切れたなどの環境側のエラー
        print(f"失敗しました: {path.name}")
        print(f"→ ファイルの読み込みか通信に問題がありました: {e}")
        return False

    # 成功した場合は、Drive上の名前とブラウザで開けるURLを表示する
    print(f"アップロードしました: {result['name']}")
    print(f"  URL: {result.get('webViewLink', '(リンク情報なし)')}")
    return True


def main():
    # sys.argv には実行時の引数が入る。argv[0] はプログラム自身の名前
    if len(sys.argv) < 2:
        print("使い方: python3 drive_upload.py <ファイルまたはフォルダのパス>")
        print("  例1（ファイル1つ）: python3 drive_upload.py ../../4-3-1/課題3/課題3_円グラフ.png")
        print("  例2（フォルダ一括）: python3 drive_upload.py ../../4-3-1/課題3")
        return

    print(BAR)
    print("【課題1】Google ドライブへのアップロード")
    print(BAR)

    # 先にファイル一覧を作る（対象が無ければ認証する前に終われるので無駄がない）
    targets = collect_targets(sys.argv[1])
    if not targets:
        return

    print(f"対象ファイル : {len(targets)}件")

    # 保存先フォルダIDを環境変数から読む。未設定なら空文字になる
    folder_id = os.environ.get(FOLDER_ID_ENV, "")
    print(f"保存先       : {'フォルダID ' + folder_id if folder_id else 'マイドライブ直下'}")
    print(THIN)

    # 認証してAPIの窓口を用意する
    service = build_service()
    if service is None:   # 認証に失敗していたら、ここで終了する
        return

    print(THIN)

    # 1件ずつアップロードする。1件失敗しても止めず、最後に結果をまとめて表示する
    success = 0
    for path in targets:
        if upload_file(service, path, folder_id):
            success += 1

    failed = len(targets) - success

    print(THIN)
    print(f"完了しました。成功 {success}件 / 失敗 {failed}件")
    print(BAR)


# このファイルを直接実行したときだけ main() を動かすおまじない
if __name__ == "__main__":
    main()
