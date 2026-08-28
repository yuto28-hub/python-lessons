# 課題2.csv を読み込んで、生徒ごとの平均・最高点・最低点を表示するプログラム
# pandas は使わず、Python標準ライブラリの csv だけで書いています

import csv          # CSVファイルを読み書きするための標準ライブラリ
import unicodedata  # 文字の種類（全角・半角）を調べるための標準ライブラリ

# 読み込むファイル名（このプログラムと同じフォルダに置いてある想定）
CSV_FILE = "課題2.csv"


def read_scores(filename):
    """CSVを読み込んで {生徒名: [スコア, スコア, ...]} の形にまとめて返す"""

    # 生徒名をキー、スコアのリストを値にする辞書を用意する
    scores = {}

    # encoding="utf-8-sig" は、Excelで作ったCSVの先頭に入る
    # 見えない文字（BOM）があっても正しく読めるようにするための指定
    # newline="" は csv モジュールを使うときのお約束
    with open(filename, encoding="utf-8-sig", newline="") as f:
        # DictReader を使うと、1行を {列名: 値} の辞書として受け取れる
        reader = csv.DictReader(f)

        for row in reader:
            name = row["名前"]

            # CSVから読んだ値は文字列なので、数値（整数）に変換する
            try:
                score = int(row["スコア"])
            except ValueError:
                # 数字でない値が入っていた行は、警告を出して読み飛ばす
                print(f"※ スコアが数値でないため1行スキップしました: {row}")
                continue

            # その生徒が初登場ならリストを新規作成し、スコアを追加する
            # setdefault は「キーが無ければ [] を入れてから返す」という便利な命令
            scores.setdefault(name, []).append(score)

    return scores


def display_width(text):
    """文字列を画面に表示したときの幅を数える（全角は2、半角は1として計算）"""
    width = 0
    for char in text:
        # east_asian_width が F(全角)/W(広い)/A(曖昧) の文字は幅2として扱う
        if unicodedata.east_asian_width(char) in ("F", "W", "A"):
            width += 2
        else:
            width += 1
    return width


def pad_right(text, width):
    """表示幅がそろうように、文字列の右側にスペースを足す（左寄せ）"""
    # 必要なスペースの数＝目標の幅 − 実際の表示幅
    return text + " " * max(0, width - display_width(text))


def pad_left(text, width):
    """表示幅がそろうように、文字列の左側にスペースを足す（右寄せ）"""
    return " " * max(0, width - display_width(text)) + text


def print_summary(scores):
    """生徒ごとの集計結果を表形式で表示する"""

    # 各列の幅（半角文字の個数で指定）
    NAME_W = 14   # 生徒名
    COUNT_W = 6   # 件数
    AVG_W = 8     # 平均
    MAX_W = 6     # 最高
    MIN_W = 6     # 最低

    # 表全体の横幅（区切り線の長さに使う）
    total_width = NAME_W + COUNT_W + AVG_W + MAX_W + MIN_W

    # 見出し行を作る（見出しも日本語なので pad_left で幅をそろえる）
    header = (pad_right("生徒名", NAME_W)
              + pad_left("件数", COUNT_W)
              + pad_left("平均", AVG_W)
              + pad_left("最高", MAX_W)
              + pad_left("最低", MIN_W))

    print("=" * total_width)
    print(header)
    print("-" * total_width)

    # 辞書を1件ずつ取り出して計算する（items() でキーと値を同時に取得）
    for name, values in scores.items():
        count = len(values)                 # 件数
        average = sum(values) / count       # 平均＝合計 ÷ 件数
        highest = max(values)               # 最高点
        lowest = min(values)                # 最低点

        # 数値は文字列に変換してから、見出しと同じ幅でそろえる
        # f"{average:.1f}" は小数第1位まで表示するという指定
        print(pad_right(name, NAME_W)
              + pad_left(str(count), COUNT_W)
              + pad_left(f"{average:.1f}", AVG_W)
              + pad_left(str(highest), MAX_W)
              + pad_left(str(lowest), MIN_W))

    print("=" * total_width)


def main():
    # ファイルが見つからない場合にエラーで止まらないようにする
    try:
        scores = read_scores(CSV_FILE)
    except FileNotFoundError:
        print(f"エラー: {CSV_FILE} が見つかりません")
        print("→ このプログラムと同じフォルダに CSV があるか確認してください")
        return  # main を終了する

    # データが1件も無かった場合の対応
    if not scores:
        print("データが1件もありませんでした")
        return

    print_summary(scores)


# このファイルを直接実行したときだけ main() を動かすおまじない
if __name__ == "__main__":
    main()
