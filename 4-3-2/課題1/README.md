# 課題1: Google Drive API でファイルをアップロードする

ローカルのファイルを Google ドライブへアップロードするプログラムです。
認証方式は **OAuth 2.0**（初回だけブラウザで許可 → 2回目以降は自動）。

## ファイル構成

| ファイル | 内容 |
|---------|------|
| `drive_upload.py` | 本体 |
| `README.md` | このファイル（初回セットアップ手順） |
| `../課題2/docs_create.py` | 課題2（ドキュメント API）の本体。セットアップはこのREADMEを参照 |
| `../課題3/meet_create.py` | 課題3（Meet API）の本体。セットアップはこのREADMEを参照 |
| `../課題4/zoom_create.py` | 課題4（Zoom API）の本体。認証は Google ではない。手順はファイル先頭のコメント |
| `../課題5/gmail_send.py` | 課題5（Gmail API）の本体。セットアップはこのREADMEを参照 |

---

## 初回セットアップ

初回だけブラウザでの設定作業が必要です。1回やれば以降は不要です。

### 手順1: Google Cloud のプロジェクトを作る

1. https://console.cloud.google.com/ を開く
2. 画面上部のプロジェクト選択 →「新しいプロジェクト」
3. 名前は何でもよい（例: `python-drive-upload`）→ 作成
> 実際に使っているプロジェクトは「My First Project」（ID: silken-network-507121-q2）。
> 新しく作らず、最初からあるプロジェクトをそのまま使っている。

### 手順2: Google Drive API を有効にする
> 課題2（ドキュメント API）をやるときは、同じ手順で Google Docs API も有効にする。
> スコープ（drive.file）は変更不要。課題1の token.json がそのまま使える。
>
> 課題3（Meet API）をやるときは、同じ手順で **Google Meet API** も有効にする。
> こちらは**スコープが違う**（`meetings.space.created`）ため、初回だけブラウザでの
> 許可がもう一度必要になる。認証情報は `token_meet.json` という別ファイルに保存され、
> 課題1・2の `token.json` には影響しない。
>
> 課題5（Gmail API）をやるときは、同じ手順で **Gmail API** も有効にする。
> スコープは `gmail.send`（送信だけ）で、トークンは `token_gmail.json` に分かれる。
> 受信箱の中身は読めない。
>
> 課題4（Zoom）は Google Cloud ではない。`zoom_create.py` 先頭のコメントを参照。

1. 左メニュー「APIとサービス」→「ライブラリ」
2. 「Google Drive API」を検索して開く
3. **「有効にする」** をクリック

### 手順3: OAuth同意画面を設定する

1. 「APIとサービス」→「OAuth同意画面」
2. User Type は **「外部」** を選んで作成
3. アプリ名（例: `ドライブアップローダー`）と自分のメールアドレスを入力
4. スコープはそのまま次へ
5. **「テストユーザー」に自分のGoogleアカウントを追加する**

> ⚠️ 手順5を忘れると、認証時に `access_denied` エラーになります。
> 一番よくあるつまずきポイントです。

### 手順4: OAuthクライアントIDを作る

1. 「APIとサービス」→「認証情報」
2. 「+ 認証情報を作成」→「OAuth クライアント ID」
3. アプリケーションの種類は **「デスクトップアプリ」** を選ぶ
4. 作成すると JSON をダウンロードできる

### 手順5: JSONをリポジトリの外に置く

ダウンロードしたJSONは**秘密情報**です。GitHubに公開されないよう、
リポジトリの外に移動します。

```bash
mkdir -p ~/.config/gdrive
mv ~/Downloads/client_secret_*.json ~/.config/gdrive/credentials.json
chmod 600 ~/.config/gdrive/credentials.json
```

`chmod 600` は「自分だけが読み書きできる」という権限設定です。

### 手順6: ライブラリをインストールする

```bash
pip3 install --user google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

インストールできたか確認:

```bash
python3 -c "import googleapiclient, google_auth_oauthlib; print('OK')"
```

### 手順7: 初回実行

```bash
cd "/Users/user/Desktop/コンテンツ用/テスト/4-3-2/課題1"
python3 drive_upload.py ../../4-3-1/課題3/課題3_円グラフ.png
```

ブラウザが自動で開くので、Googleアカウントを選んで「許可」を押します。

> 「このアプリは Google で確認されていません」と表示されたら、
> 「詳細」→「（アプリ名）に移動」をクリックして進めてください。
> 自作アプリなので想定内の表示です。

許可すると `~/.config/gdrive/token.json` が自動で作られ、
**2回目以降はブラウザが開きません**。

---

## 使い方

```bash
# ファイルを1つアップロード
python3 drive_upload.py ../../4-3-1/課題3/課題3_円グラフ.png

# フォルダの中身をまとめてアップロード
python3 drive_upload.py ../../4-3-1/課題3
```

アップロード先は既定で**マイドライブの直下**です。

特定のフォルダに入れたい場合は、そのフォルダをブラウザで開き、
URL末尾のIDを環境変数に設定します。

```
https://drive.google.com/drive/folders/【ここがフォルダID】
```

```bash
export GDRIVE_FOLDER_ID="＜調べたフォルダID＞"
```

毎回設定するのが面倒な場合は `~/.zshrc` に追記すると常時有効になります。

---

## 困ったときは

| 症状 | 原因と対処 |
|------|-----------|
| `access_denied` と出る | 手順3の**テストユーザー登録**が漏れています |
| `認証ファイルが見つかりません` | 手順5で `~/.config/gdrive/credentials.json` に配置できていません |
| しばらく使ったら再認証を求められる | 下の「7日間の期限」を参照 |
| `ModuleNotFoundError` | 手順6のインストールが未実施です |

### 7日間の期限について

OAuth同意画面の公開ステータスが **「テスト」** のままだと、
`token.json` の有効期限が **7日間** で切れます。

切れた場合は次のコマンドで削除して再実行すれば、再認証されます。

```bash
rm ~/.config/gdrive/token.json
```

毎週の再認証が面倒な場合は、OAuth同意画面で **「本番環境に公開」** すると
期限が無くなります（自分だけで使う分には審査は不要です）。

---

## セキュリティ上の注意

- `credentials.json` と `token.json` は**絶対にGitにコミットしない**こと
- 対策として、リポジトリ直下の `.gitignore` に登録済み
- さらに安全のため、ファイル自体をリポジトリ外（`~/.config/gdrive/`）に置いている
- コミット前には `git status` に認証情報が出ていないか必ず確認する
