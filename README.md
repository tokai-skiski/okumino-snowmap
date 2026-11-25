# 奥美濃スキー場 積雪・営業状況マップ

[東海地方スキー・スノボ情報局](https://tokai-ski-snowboard.com/) の積雪マップ用のデータを作る置き場所です。

- 毎日 6:00・7:30・10:00・13:00(日本時間)ごろ、奥美濃8スキー場の公式サイトに載っている積雪・気温・リフトとコースの運行状況を読み取り、`docs/snow.json` に保存します(GitHub Actions)。
- 天気予報と観測値は気象庁のデータを使っています。
- 読み取れなかった値は空欄(null)にし、推測で埋めません。
- 確認用ページ:https://tokai-skiski.github.io/okumino-snowmap/

## ファイル

| ファイル | 内容 |
|---|---|
| `scrape.py` | 公式サイトと気象庁から読み取り、`snow.json` を作る |
| `snowmap_snippet.html` | ブログの固定ページ(カスタムHTMLブロック)に貼る地図と一覧 |
| `build_site.py` | 確認用ページ `docs/index.html` を作る |
| `.github/workflows/scrape.yml` | 自動実行の時刻と手順 |

地図:[地理院タイル](https://maps.gsi.go.jp/development/ichiran.html)、[Leaflet](https://leafletjs.com/)
