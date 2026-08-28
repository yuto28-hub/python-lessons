# 1から100までの数当てゲーム

import random  # ランダムな数字を作るための標準ライブラリ


def main():
    # コンピューターが1〜100の中からランダムに1つ選ぶ（1も100も選ばれる）
    answer = random.randint(1, 100)

    # 何回目の挑戦かを数える箱（最初は0回）
    count = 0

    # 偶数・奇数ヒントを出し始める回数
    HINT_START = 6

    print("=" * 30)
    print("数当てゲーム")
    print("1から100までの数字を当ててね！")
    print("=" * 30)

    # 正解するまでずっと繰り返す（break が実行されたら抜ける）
    while True:
        # 入力は必ず文字列で返ってくるので、あとで数字に変換する
        guess_text = input("数字を入力: ")

        # 数字以外が入力されたときにエラーで止まらないようにする
        try:
            guess = int(guess_text)  # 文字列 → 整数に変換
        except ValueError:
            # int() に変換できなかった場合はここに来る
            print("→ 数字を入力してください")
            continue  # 回数を増やさずに、もう一度入力へ戻る

        # 範囲外のチェック（1〜100以外は無効とする）
        if guess < 1 or guess > 100:
            print("→ 1から100までの数字を入力してください")
            continue

        # ここまで来たら有効な入力なので、挑戦回数を1増やす
        count += 1

        # 正解した場合は結果を表示してゲーム終了
        if guess == answer:
            print("=" * 30)
            print(f"正解！ 答えは {answer} でした")
            print(f"{count} 回目で当たりました！")
            print("=" * 30)
            break  # while ループを抜けてゲーム終了

        # ここから下は「はずれ」のときの処理
        # 答えと比べて、大きい／小さいのヒントを出す
        if guess < answer:
            print("→ もっと大きい！")
        else:
            print("→ もっと小さい！")

        # 6回目以降のはずれには、偶数か奇数かのヒントも追加で出す
        if count >= HINT_START:
            # % は「割ったあまり」を求める記号。2で割ったあまりが0なら偶数
            if answer % 2 == 0:
                kind = "偶数"
            else:
                kind = "奇数"
            print(f"→ ヒント: 答えは{kind}だよ")


# このファイルを直接実行したときだけ main() を動かすおまじない
if __name__ == "__main__":
    main()
