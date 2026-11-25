"""snowmap_snippet.html から、確認用のページ docs/index.html を作る。
(ブログの固定ページには snowmap_snippet.html の中身をそのまま貼る)"""
snip = open('snowmap_snippet.html', encoding='utf-8').read()
html = ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex">'
        '<title>奥美濃スキー場 積雪・営業状況マップ(データ確認用)</title>'
        '<style>body{margin:0;padding:12px 16px;background:#F4F8FC}</style></head><body>'
        + snip.replace("var DATA_URL = 'https://tokai-skiski.github.io/okumino-snowmap/snow.json'", "var DATA_URL = 'snow.json'")
        + '<p style="font-size:12px;color:#556372;max-width:760px;margin:16px auto">このページはデータ確認用です。'
          '<a href="https://tokai-ski-snowboard.com/">東海地方スキー・スノボ情報局</a></p></body></html>')
open('docs/index.html', 'w', encoding='utf-8').write(html)
print('wrote docs/index.html')
