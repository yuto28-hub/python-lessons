# 課題2.csv を pandas で読み込んで、生徒ごとの平均・最高点・最低点を表示するプログラム
# 素のPython版（csv_summary.py）と同じ結果になるかを比べるためのコードです

import pandas as pd  # pandas を pd という短い名前で使うのが世界共通の慣習

# 読み込むファイル名（このプログラムと同じフォルダに置いてある想定）
CSV_FILE = "課題2.csv"


def main():
    # ファイルが見つからない場合にエラーで止まらないようにする
    try:
        # read_csv だけでCSV全体を「表（DataFrame）」として読み込める
        # encoding="utf-8-sig" はExcel由来の見えない文字(BOM)対策
        df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    except FileNotFoundError:
        print(f"エラー: {CSV_FILE} が見つかりません")
        print("→ このプログラムと同じフォルダに CSV があるか確認してください")
        return

    # groupby("名前") で生徒ごとにグループ分けし、
    # agg で「スコア列に対して複数の集計をまとめて実行」する
    summary = df.groupby("名前", sort=False)["スコア"].agg(
        件数="count",   # 件数（データの個数）
        平均="mean",    # 平均
        最高="max",     # 最高点
        最低="min",     # 最低点
    )

    # 平均を小数第1位に丸める（round(1) は四捨五入して1桁にする命令）
    summary["平均"] = summary["平均"].round(1)

    # 日本語が混ざった表でも桁がそろうようにする設定
    pd.set_option("display.unicode.east_asian_width", True)

    print("=" * 40)
    print("【pandas版】生徒ごとのスコア集計")
    print("=" * 40)
    print(summary)
    print("=" * 40)


# このファイルを直接実行したときだけ main() を動かすおまじない
if __name__ == "__main__":
    main()
