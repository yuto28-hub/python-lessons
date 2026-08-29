# 課題3.csv を読み込んで、3種類のグラフ（円・棒・ヒストグラム）を作成し、
# それぞれPNG画像として保存するプログラム
#
# 使い方: ターミナルで「python3 csv_graphs.py」と実行するだけ
# 必要なライブラリ: pandas, matplotlib

import matplotlib                 # グラフ作成ライブラリ本体
matplotlib.use("Agg")             # 画面に表示せず「画像ファイル保存専用」で動かす設定

import matplotlib.pyplot as plt   # 実際にグラフを描く部分。plt という短縮名が世界共通の慣習
import pandas as pd               # CSVを表として扱うライブラリ

# ------------------------------------------------------------
# 設定（ファイル名などをここにまとめておくと後から変更しやすい）
# ------------------------------------------------------------
CSV_FILE = "課題3.csv"                  # 読み込むCSV（このプログラムと同じフォルダに置く）
PIE_FILE = "課題3_円グラフ.png"          # 保存する画像1: 円グラフ
BAR_FILE = "課題3_棒グラフ.png"          # 保存する画像2: 棒グラフ
HIST_FILE = "課題3_ヒストグラム.png"      # 保存する画像3: ヒストグラム

# 日本語がグラフ内で「□□□（豆腐）」に化けないようにフォントを指定する
# Mac に標準で入っている「Hiragino Sans」を最優先で使う設定
plt.rcParams["font.family"] = ["Hiragino Sans", "Arial Unicode MS", "AppleGothic"]
# マイナス記号が文字化けするのを防ぐお約束の設定
plt.rcParams["axes.unicode_minus"] = False


def load_data():
    """CSVを読み込んでDataFrame（表）として返す。失敗したら None を返す"""

    try:
        # encoding="utf-8-sig" はExcel由来の見えない文字(BOM)対策
        df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    except FileNotFoundError:
        print(f"エラー: {CSV_FILE} が見つかりません")
        print("→ このプログラムと同じフォルダに CSV があるか確認してください")
        return None

    # スコア列を数値に変換する（数値でない値は NaN = 欠損値 になる）
    # errors="coerce" は「変換できなければエラーで止めずに欠損扱いにする」という指定
    df["スコア"] = pd.to_numeric(df["スコア"], errors="coerce")

    # スコアが欠損している行があれば知らせてから取り除く
    ng = df["スコア"].isna().sum()
    if ng > 0:
        print(f"※ スコアが数値でない行が {ng} 件あったため除外しました")
        df = df.dropna(subset=["スコア"])

    return df


def make_pie_chart(df):
    """グラフ1: 所属ごとの参加者数を円グラフで表示して保存する"""

    # value_counts() で「所属ごとの人数」を数える
    counts = df["所属"].value_counts()

    # figsize=(横インチ, 縦インチ) でキャンバスの大きさを決める
    fig, ax = plt.subplots(figsize=(7, 7))

    # 円グラフの各扇形の色（見分けやすい落ち着いた配色）
    colors = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#B279A2"]

    # ラベルは「所属名（○人）」の形にして、人数も一目で分かるようにする
    labels = [f"{name}\n({n}人)" for name, n in counts.items()]

    ax.pie(
        counts,                        # 各扇形の大きさのもとになる数値
        labels=labels,                 # 各扇形につける名前
        autopct="%1.1f%%",             # 割合を小数第1位まで自動表示（例: 28.6%）
        startangle=90,                 # 真上(12時の位置)から描き始める
        counterclock=False,            # 時計回りに並べる（見慣れた向きにする）
        colors=colors[:len(counts)],   # 所属の数だけ色を使う
        # 扇形の内側に書く文字（パーセント）の見た目を調整
        textprops={"fontsize": 12},
        # 扇形の境界に白い線を入れて区切りを見やすくする
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )

    # 円グラフを正しい「真円」にする（これがないと楕円になることがある）
    ax.axis("equal")
    ax.set_title(f"所属ごとの参加者数の内訳（全{len(df)}人）", fontsize=15, pad=20)

    # bbox_inches="tight" で余白を自動で切り詰める。dpi=150 で高画質にする
    fig.savefig(PIE_FILE, dpi=150, bbox_inches="tight")
    plt.close(fig)   # 使い終わったグラフはメモリ節約のため閉じる
    print(f"保存しました: {PIE_FILE}")


def make_bar_chart(df):
    """グラフ2: 所属ごとの平均・最高・最低スコアを棒グラフで表示して保存する"""

    # groupby("所属") で所属ごとにグループ分けし、agg で3種類の集計をまとめて行う
    stats = df.groupby("所属")["スコア"].agg(
        平均="mean",
        最高="max",
        最低="min",
    )
    # 平均が高い順に並べ替えると、順位が一目で分かるグラフになる
    stats = stats.sort_values("平均", ascending=False)

    fig, ax = plt.subplots(figsize=(9, 6))

    x = range(len(stats))   # 棒を置く横位置（0, 1, 2, 3 …）
    width = 0.26            # 棒1本あたりの幅

    # 3種類の棒を少しずつ横にずらして並べる（グループ化棒グラフ）
    b1 = ax.bar([i - width for i in x], stats["平均"], width,
                label="平均スコア", color="#4C78A8")
    b2 = ax.bar(list(x), stats["最高"], width,
                label="最高スコア", color="#54A24B")
    b3 = ax.bar([i + width for i in x], stats["最低"], width,
                label="最低スコア", color="#E45756")

    # 各棒の上に数値を書き込む（bar_label は棒に自動でラベルを付ける便利な命令）
    ax.bar_label(b1, fmt="%.1f", fontsize=9, padding=2)
    ax.bar_label(b2, fmt="%.0f", fontsize=9, padding=2)
    ax.bar_label(b3, fmt="%.0f", fontsize=9, padding=2)

    # タイトル・軸ラベル・凡例をきちんと付ける
    ax.set_title("所属ごとのスコア比較（平均・最高・最低）", fontsize=15, pad=15)
    ax.set_xlabel("所属", fontsize=12)
    ax.set_ylabel("スコア（点）", fontsize=12)
    ax.set_xticks(list(x))                 # 目盛りを置く位置
    ax.set_xticklabels(stats.index)        # 目盛りに表示する文字（所属名）
    ax.set_ylim(0, 110)                    # 0から始めることで棒の長さの比較が正しくなる
    ax.legend(loc="upper right")           # 凡例（どの色が何かの説明）
    ax.grid(axis="y", linestyle="--", alpha=0.4)   # 横線のグリッドで高さを読みやすくする
    ax.set_axisbelow(True)                 # グリッド線を棒の後ろに描く

    fig.savefig(BAR_FILE, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"保存しました: {BAR_FILE}")


def make_histogram(df):
    """グラフ3: 全参加者のスコア分布をヒストグラムで表示して保存する"""

    scores = df["スコア"]

    # ビン（区切りの箱）は 70〜100 を 5点刻みにする
    # スコアが70〜95に収まっているので、5点刻みだと分布の形が分かりやすい
    bins = range(70, 101, 5)

    fig, ax = plt.subplots(figsize=(9, 6))

    # n には各ビンの度数（人数）が入る
    n, edges, patches = ax.hist(
        scores,
        bins=bins,
        color="#4C78A8",
        edgecolor="white",   # 棒の境界を白線にして区切りを見やすくする
        linewidth=1.5,
    )

    # 各棒の上に「○人」と人数を書き込む（0人の箱には書かない）
    for count, left, right in zip(n, edges[:-1], edges[1:]):
        if count > 0:
            ax.text((left + right) / 2, count + 0.15, f"{int(count)}人",
                    ha="center", fontsize=10)

    # 平均点の位置に縦の点線を引くと、分布が平均より上下どちらに偏るか分かる
    mean = scores.mean()
    ax.axvline(mean, color="#E45756", linestyle="--", linewidth=2,
               label=f"全体平均 {mean:.1f}点")

    ax.set_title(f"全参加者のスコア分布（{len(scores)}人・5点刻み）", fontsize=15, pad=15)
    ax.set_xlabel("スコア（点）", fontsize=12)
    ax.set_ylabel("人数（人）", fontsize=12)
    ax.set_xticks(list(bins))            # 目盛りをビンの区切りと同じ位置にそろえる
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    fig.savefig(HIST_FILE, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"保存しました: {HIST_FILE}")


def main():
    df = load_data()
    if df is None:   # 読み込みに失敗していたら、ここで終了する
        return

    print("=" * 45)
    print("【課題3】CSVからグラフを作成します")
    print("=" * 45)
    print(f"読み込み件数 : {len(df)}人")
    print(f"所属の種類   : {df['所属'].nunique()}種類 ({', '.join(df['所属'].unique())})")
    print(f"スコア範囲   : {df['スコア'].min():.0f}点 〜 {df['スコア'].max():.0f}点")
    print(f"全体平均     : {df['スコア'].mean():.1f}点")
    print("-" * 45)

    # 3つのグラフを順番に作って保存する
    make_pie_chart(df)
    make_bar_chart(df)
    make_histogram(df)

    print("-" * 45)
    print("完了しました。3枚の画像を確認してください。")
    print("=" * 45)


# このファイルを直接実行したときだけ main() を動かすおまじない
if __name__ == "__main__":
    main()
