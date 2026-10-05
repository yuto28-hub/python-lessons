# Google Meet API を使って、オンライン会議のスペースを作り
# 参加リンク（https://meet.google.com/xxx-xxxx-xxx）を発行するプログラム
# 認証は OAuth 2.0（課題1・2とは別のスコープが必要なので、トークンも別ファイル）
#
# 使い方:
#   python3 meet_create.py                 会議を作って参加リンクを表示
#   python3 meet_create.py --open          誰でもノックなしで入れる会議を作る
#   python3 meet_create.py --get abc-defg-hij   作成済みの会議の情報を調べる
#
# 必要なライブラリ（課題1と同じ。追加は不要）:
#   pip3 install --user google-api-python-client google-auth-httplib2 google-auth-oauthlib
#
# 事前準備（初回のみ）は 課題1 フォルダの README.md を参照
#   ※ Google Cloud で「Google Meet API」を有効にしておくこと

import os         # 環境変数の読み取りやファイル権限の変更に使う標準ライブラリ
import sys        # コマンドラインの引数を受け取るための標準ライブラリ
import warnings   # 警告メッセージの表示を調整するための標準ライブラリ
from pathlib import Path  # ファイルのパスを扱いやすくする標準ライブラリ

# Google製ライブラリが Python 3.9 に対して出す警告を隠す
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
# 設定
# ------------------------------------------------------------

CRED_DIR_ENV = "GDRIVE_CONFIG_DIR"
DEFAULT_CRED_DIR = "~/.config/gdrive"

CRED_FILE = "credentials.json"   # 課題1で配置したものをそのまま使う

# トークンは課題1・2と「別ファイル」にする。
# スコープが違うため同じ token.json を使い回すと、課題1・2側が認証やり直しになる
TOKEN_FILE = "token_meet.json"

# 権限の範囲。meetings.space.created は「このアプリが作った会議だけ」
# 作成・変更・参照できる最小限の権限。他人の会議には触れない
SCOPES = ["https://www.googleapis.com/auth/meetings.space.created"]

# 会議への入り方の設定値（アクセス種別）
#   OPEN       : リンクを知っていれば誰でもノックなしで入れる
#   TRUSTED    : 同じ組織のメンバーと招待者はノック不要。それ以外はノックが必要
#   RESTRICTED : 招待者だけがノック不要
ACCESS_OPEN = "OPEN"

BAR = "=" * 45   # 見出し用の太い区切り線
THIN = "-" * 45  # 中身用の細い区切り線


def get_cred_dir():
    """認証情報を置くフォルダのパスを返す（環境変数があればそちらを優先）"""

    raw = os.environ.get(CRED_DIR_ENV, DEFAULT_CRED_DIR)

    # expanduser() は「~」を実際のホームフォルダのパスに展開する
    return Path(raw).expanduser()


def build_service():
    """OAuth認証を行い、Meet APIを操作するオブジェクトを返す。失敗したら None を返す"""

    cred_dir = get_cred_dir()
    cred_path = cred_dir / CRED_FILE
    token_path = cred_dir / TOKEN_FILE

    creds = None  # 認証情報を入れる変数。まだ何も無いので None にしておく

    # --- 手順1: 前回の認証情報が残っていれば読み込む ---
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except ValueError:
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
            print("（課題1とは別の権限なので、初回はもう一度許可が必要です）")
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
            # port=0 は「空いているポートを自動で選ぶ」という意味
            creds = flow.run_local_server(port=0)

        # --- 手順3: 次回はブラウザ不要にするため、認証情報を保存する ---
        cred_dir.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        # chmod 0o600 は「自分だけが読み書きできる」という権限
        os.chmod(token_path, 0o600)
        print(f"認証情報を保存しました: {token_path}")

    # --- 手順4: 認証情報を使って Meet API の窓口を作る ---
    return build("meet", "v2", credentials=creds)


def create_space(service, access_type=None):
    """会議スペースを新しく作り、APIの返事（辞書）を返す

    Meet API での「スペース」は、会議室そのもの。
    カレンダーの予定とは独立していて、作った時点で参加リンクが決まる。
    """

    # body が空の辞書なら、設定はすべてGoogle側の既定値になる
    body = {}

    if access_type is not None:
        # config の中に設定を入れる。キー名はAPIの定義どおり accessType
        body["config"] = {"accessType": access_type}

    # spaces().create() が「新しい会議スペースを作る」命令
    space = service.spaces().create(body=body).execute()

    return space


def get_space(service, code):
    """会議コード（abc-defg-hij）から、その会議の情報を調べて返す

    会議コードはスペース名の別名として使える。
    ただし参照できるのは「このプログラムが作った会議」だけ（スコープの制限）。
    """

    # spaces/ に続けてコードを書くと、名前の代わりに使える
    return service.spaces().get(name=f"spaces/{code}").execute()


def show_space(space):
    """会議の情報を人が読める形で表示する"""

    # dict.get は「キーがあればその値、なければ第2引数」を返す命令。
    # APIの返事に必ず入っているとは限らない項目は get で読むと落ちない
    uri = space.get("meetingUri", "（不明）")
    code = space.get("meetingCode", "（不明）")
    name = space.get("name", "（不明）")
    access = space.get("config", {}).get("accessType", "（Google側の既定値）")

    print(f"参加リンク : {uri}")
    print(f"会議コード : {code}")
    print(f"スペース名 : {name}")
    print(f"入室設定   : {access}")


def main():
    # sys.argv には実行時の引数が入る。argv[0] はプログラム自身の名前
    args = sys.argv[1:]

    # --- 引数の読み取り ---
    want_open = "--open" in args
    get_code = None

    if "--get" in args:
        i = args.index("--get")
        if i + 1 >= len(args):
            print("エラー: --get のあとに会議コードを指定してください")
            print("例: python3 meet_create.py --get abc-defg-hij")
            return
        get_code = args[i + 1]

    print(BAR)
    print("【課題3】Google Meet の会議作成と参加リンクの発行")
    print(BAR)

    if get_code is not None:
        print(f"調べる会議 : {get_code}")
    else:
        print("作成する会議 : 新規スペース")
        print(f"入室設定     : {'OPEN（誰でも入れる）' if want_open else 'Google側の既定値'}")

    print(THIN)

    # 認証してAPIの窓口を用意する
    service = build_service()
    if service is None:   # 認証に失敗していたら、ここで終了する
        return

    print(THIN)

    # API通信はここから。失敗したら HttpError が飛んでくる
    try:
        if get_code is not None:
            space = get_space(service, get_code)
            print("会議の情報を取得しました")
        else:
            space = create_space(service, ACCESS_OPEN if want_open else None)
            print("会議スペースを作成しました")

    except HttpError as e:
        # status_code で原因を切り分けて日本語で説明する
        status = getattr(e.resp, "status", None)
        print("失敗しました")

        if status == 403:
            print("→ 権限またはAPIが有効になっていない可能性があります")
            print("　 Google Cloud で「Google Meet API」が有効か確認してください")
        elif status == 404:
            print("→ その会議が見つかりません")
            print("　 このプログラムが作った会議しか調べられません（スコープの制限）")
        elif status == 401:
            print(f"→ 認証が無効です。{get_cred_dir() / TOKEN_FILE} を削除して再実行してください")
        elif status == 400:
            print(f"→ 指定内容に問題があります: {e}")
        else:
            print(f"→ APIエラー（状態コード: {status}）: {e}")

        return

    # 成功した場合は、中身を表示する
    print(THIN)
    show_space(space)
    print(BAR)

    if get_code is None:
        print("このリンクを相手に送れば、そのまま会議に参加できます")
        print(f"あとで調べ直すとき: python3 meet_create.py --get {space.get('meetingCode', '')}")


# このファイルを直接実行したときだけ main() を動かすおまじない
if __name__ == "__main__":
    main()
