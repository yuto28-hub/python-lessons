# YouTube Data API で、キーワードに合う動画を検索し
# タイトルとURLを表示するプログラム
# 認証は APIキー（公開動画の検索なので、ブラウザ許可の OAuth は不要）
#
# 使い方:
#   python3 youtube_search.py キーワード
#   python3 youtube_search.py キーワード 件数
#   python3 youtube_search.py キーワード 件数 --min-minutes 15 --days 365
#   例: python3 youtube_search.py "Python 入門" 5
#   例: python3 youtube_search.py "警察 ボディカメラ 解説" 10 --min-minutes 15 --days 365
#
# --min-minutes と --days は、課題の「タイトルとURLを出す」に条件を足すためのもの。
# 検索APIの返事には動画の長さが無い。15分以上だけ残すには、
# 見つかったIDでもう一度 videos.list を呼び、長さを見てから捨てる。
#
# 追加ライブラリは不要（標準ライブラリだけ）
#
# 事前準備（初回のみ）:
#   1. 課題1と同じ Google Cloud プロジェクトを開く
#   2. 「APIとサービス」→「ライブラリ」で「YouTube Data API v3」を有効にする
#   3. 「認証情報」→「認証情報を作成」→「APIキー」
#   4. 鍵はリポジトリの外に置く
#
#        mkdir -p ~/.config/youtube
#        printf '%s' 'ここにAPIキー' > ~/.config/youtube/api_key
#        chmod 600 ~/.config/youtube/api_key
#
#   キーの中身はチャットやGitに貼らない。

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

KEY_DIR_ENV = "YOUTUBE_CONFIG_DIR"
DEFAULT_KEY_DIR = "~/.config/youtube"
KEY_FILE = "api_key"
KEY_ENV = "YOUTUBE_API_KEY"

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
WATCH_URL = "https://www.youtube.com/watch?v="

# 課題の確認用なので、既定は5件。APIの上限は1回50件
DEFAULT_MAX = 5
HARD_MAX = 50

BAR = "=" * 45
THIN = "-" * 45


def get_key_dir():
    """APIキーを置くフォルダのパスを返す"""

    raw = os.environ.get(KEY_DIR_ENV, DEFAULT_KEY_DIR)
    return Path(raw).expanduser()


def load_api_key():
    """APIキーを返す。環境変数を優先し、無ければ設定ファイルを読む"""

    key = os.environ.get(KEY_ENV, "").strip()
    if key:
        return key

    key_path = get_key_dir() / KEY_FILE
    if not key_path.exists():
        print("エラー: APIキーが見つかりません")
        print(f"→ 環境変数 {KEY_ENV} を設定するか、次のファイルに1行で保存してください")
        print(f"　 {key_path}")
        print("　 Google Cloud で YouTube Data API v3 を有効にし、APIキーを作成してください")
        return None

    key = key_path.read_text(encoding="utf-8").strip()
    if not key:
        print(f"エラー: {key_path} が空です")
        return None

    return key


def search_videos(api_key, keyword, max_results, published_after=None):
    """キーワードで動画を検索し、APIの返事（辞書）を返す

    published_after を渡すと、その日時より新しい動画だけが返る。
    検索結果に入るのはタイトルとIDまでで、長さは入らない。
    """

    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "maxResults": max_results,
        "key": api_key,
    }
    if published_after is not None:
        # 再生が多い順にすると、ベンチマーク候補が上に来る
        params["order"] = "viewCount"
        params["publishedAfter"] = published_after

    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{SEARCH_URL}?{query}", method="GET")

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def iso_duration_seconds(value):
    """PT1H2M3S のような長さを秒に直す。読めなければ 0"""

    matched = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not matched:
        return 0

    hours, minutes, seconds = (int(part or 0) for part in matched.groups())
    return hours * 3600 + minutes * 60 + seconds


def fetch_durations(api_key, video_ids):
    """動画IDのリストから、長さ（秒）の辞書を返す"""

    if not video_ids:
        return {}

    query = urllib.parse.urlencode(
        {
            "part": "contentDetails",
            "id": ",".join(video_ids),
            "key": api_key,
        }
    )
    request = urllib.request.Request(f"{VIDEOS_URL}?{query}", method="GET")

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    durations = {}
    for item in payload.get("items", []):
        raw = item.get("contentDetails", {}).get("duration", "")
        durations[item.get("id")] = iso_duration_seconds(raw)

    return durations


def format_duration(seconds):
    """秒を 18:38 の形にする"""

    minutes, remain = divmod(seconds, 60)
    return f"{minutes}:{remain:02d}"


def explain_http_error(error):
    """HTTPエラーを日本語で説明する。APIキー自体は表示しない"""

    status = getattr(error, "code", None)
    detail = error.read().decode("utf-8", errors="replace")

    print("失敗しました")

    try:
        reason = json.loads(detail)["error"]["errors"][0].get("reason", "")
        message = json.loads(detail)["error"].get("message", "")
    except (json.JSONDecodeError, KeyError, IndexError):
        reason = ""
        message = detail[:300]

    if status == 403 and reason == "accessNotConfigured":
        print("→ YouTube Data API v3 が有効になっていません")
        print("　 Google Cloud のライブラリで有効にしてください")
    elif status == 400 and "API key" in message:
        print("→ APIキーが無効です。~/.config/youtube/api_key を確認してください")
    elif reason == "quotaExceeded":
        print("→ 1日の利用上限に達しました。日付が変わってから再実行してください")
    else:
        print(f"→ APIエラー（状態コード: {status}）")
        if message:
            print(f"　 {message[:300]}")


def read_option(args, name):
    """--name の次の値を整数で返す。無ければ None"""

    if name not in args:
        return None

    index = args.index(name)
    if index + 1 >= len(args):
        print(f"エラー: {name} のあとに数値を指定してください")
        return "error"

    try:
        return int(args[index + 1])
    except ValueError:
        print(f"エラー: {name} は整数で指定してください")
        return "error"


def main():
    args = sys.argv[1:]
    min_minutes = read_option(args, "--min-minutes")
    within_days = read_option(args, "--days")
    if min_minutes == "error" or within_days == "error":
        return

    # フラグとその値を除いた残りが、キーワードと件数
    skip = set()
    for name in ("--min-minutes", "--days"):
        if name in args:
            index = args.index(name)
            skip.add(index)
            skip.add(index + 1)
    positionals = [value for index, value in enumerate(args) if index not in skip]

    if not positionals:
        print('使い方: python3 youtube_search.py キーワード [件数] [--min-minutes 15 --days 365]')
        print('例    : python3 youtube_search.py "Python 入門" 5')
        print('例    : python3 youtube_search.py "警察 ボディカメラ 解説" 10 --min-minutes 15 --days 365')
        return

    keyword = positionals[0]

    if len(positionals) >= 2:
        try:
            max_results = int(positionals[1])
        except ValueError:
            print("エラー: 件数は整数で指定してください")
            return
        if not 1 <= max_results <= HARD_MAX:
            print(f"エラー: 件数は 1〜{HARD_MAX} です")
            return
    else:
        max_results = DEFAULT_MAX

    published_after = None
    if within_days is not None:
        if within_days < 1:
            print("エラー: --days は 1 以上にしてください")
            return
        start = datetime.now(timezone.utc) - timedelta(days=within_days)
        published_after = start.strftime("%Y-%m-%dT%H:%M:%SZ")

    if min_minutes is not None and min_minutes < 1:
        print("エラー: --min-minutes は 1 以上にしてください")
        return

    print(BAR)
    print("【課題6】YouTube 動画の検索")
    print(BAR)
    print(f"キーワード : {keyword}")
    print(f"件数       : {max_results}")
    if min_minutes is not None:
        print(f"最短       : {min_minutes}分")
    if within_days is not None:
        print(f"期間       : 直近{within_days}日")
    print(THIN)

    api_key = load_api_key()
    if api_key is None:
        return

    # 長さで捨てるので、検索は上限まで取ってから絞り込む
    fetch_count = HARD_MAX if min_minutes is not None else max_results

    try:
        payload = search_videos(api_key, keyword, fetch_count, published_after)
        items = [item for item in payload.get("items", []) if item.get("id", {}).get("videoId")]
        durations = {}
        if min_minutes is not None:
            video_ids = [item["id"]["videoId"] for item in items]
            durations = fetch_durations(api_key, video_ids)
    except urllib.error.HTTPError as error:
        explain_http_error(error)
        return
    except urllib.error.URLError as error:
        print("失敗しました")
        print(f"→ YouTube に接続できません: {error.reason}")
        return

    shown = 0
    min_seconds = (min_minutes or 0) * 60

    for item in items:
        video_id = item["id"]["videoId"]
        seconds = durations.get(video_id, 0)
        if min_minutes is not None and seconds < min_seconds:
            continue

        shown += 1
        snippet = item.get("snippet", {})
        title = snippet.get("title", "（タイトルなし）")
        print(f"{shown}. {title}")
        print(f"   {WATCH_URL}{video_id}")

        if min_minutes is not None or within_days is not None:
            published = snippet.get("publishedAt", "")[:10]
            channel = snippet.get("channelTitle", "")
            print(f"   {format_duration(seconds)} / {published} / {channel}")

        if shown >= max_results:
            break

    if shown == 0:
        print("該当する動画はありませんでした")

    print(BAR)


if __name__ == "__main__":
    main()
