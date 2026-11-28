"""奥美濃8スキー場の公式ゲレンデ情報を読み取り、snow.json を作る(試作版)。
使い方: python scrape.py [出力先.json] [--raw 保存済みHTMLフォルダ]
読み取れなかった項目は null にする(推測で埋めない)。"""
import json, re, sys, os, time, datetime, urllib.request
from bs4 import BeautifulSoup

JST = datetime.timezone(datetime.timedelta(hours=9))
UA = {'User-Agent': 'Mozilla/5.0 (compatible; tokai-ski-snowmap/0.1; +https://tokai-ski-snowboard.com/)'}
OPEN_MARKS = ('◯', '○', '〇', '△', 'OPEN', '運行中', '滑走可')

RESORTS = [
  dict(id='takasu', drive=90, planned='12月11日', article='/ski-area/takasu_dyna/', hotel='/hotel/takasu-dyna-hotel/',
       name='高鷲スノーパーク', lat=35.9982091, lng=136.8773292, kind='template',
       pages={'cond': 'https://www.takasu.gr.jp/condition/'}),
  dict(id='dyna', drive=90, planned='12月5日', article='/ski-area/takasu_dyna/', hotel='/hotel/takasu-dyna-hotel/',
       name='ダイナランド', lat=35.9902088, lng=136.8705351, kind='template',
       pages={'cond': 'https://www.dynaland.co.jp/condition/'}),
  dict(id='washi', drive=84, planned='11月21日', article='/ski-area/washitopia/', hotel='/hotel/washigatake-hotel/',
       name='鷲ヶ岳スキー場', lat=35.9432183, lng=136.9197344, kind='template',
       pages={'cond': 'https://ski.washigatake.jp/condition/'}),
  dict(id='hirugano', drive=93, planned='12月23日', article='/ski-area/hirugano/', hotel='/hotel/hotel-by-walk/',
       name='ひるがの高原スキー場', lat=36.0055472, lng=136.9085684, kind='template',
       pages={'cond': 'https://www.hiruganokogen.com/condition/'}),
  dict(id='whitepia', drive=92, planned='11月28日', article='/ski-area/washitopia/', hotel='/hotel/washigatake-hotel/',
       name='ホワイトピアたかす', lat=35.9558169, lng=136.9348753, kind='whitepia',
       pages={'top': 'https://whitepia.jp/', 'cond': 'https://whitepia.jp/operation/'}),
  dict(id='meiho', drive=100, planned='12月12日', article='/ski-area/meiho/', hotel='/hotel/hotel-by-walk/',
       name='めいほうスキー場', lat=35.941763, lng=137.042953, kind='meiho',
       pages={'top': 'https://www.meihoski.co.jp/', 'cond': 'https://www.meihoski.co.jp/gelande/'}),
  dict(id='wing', drive=100, planned='12月11日', article='/ski-area/winghills/', hotel='/hotel/hotel-by-walk/',
       name='ウイングヒルズ白鳥リゾート', lat=35.9659079, lng=136.8028258, kind='wing',
       pages={'top': 'https://winghills.net/', 'cond': 'https://winghills.net/snow/coursemap/'}),
  dict(id='swp', drive=102, planned='11月28日', article='/ski-area/siratori-kougen/', hotel='/hotel/hotel-by-walk/',
       name='スノーウェーブパーク白鳥高原', lat=35.957247, lng=136.805089, kind='swp',
       pages={'top': 'https://siratori-k.jp/swp/', 'cond': 'https://siratori-k.jp/swp/gelande'}),
]
# 保存済みHTMLで試すときのファイル名
RAW_NAMES = {('whitepia', 'top'): 'whitepia', ('whitepia', 'cond'): 'whitepia_op', ('meiho', 'top'): 'meiho',
             ('meiho', 'cond'): 'meiho_g', ('wing', 'top'): 'wing', ('wing', 'cond'): 'wing_c',
             ('swp', 'top'): 'swp', ('swp', 'cond'): 'swp_g'}


def get(url, rawdir=None, key=None):
    if rawdir:
        return open(os.path.join(rawdir, key + '.html'), 'rb').read()
    for i in range(3):  # 一時的な失敗に備えて3回まで試す
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
        except Exception:
            if i == 2:
                raise
            time.sleep(10)


def soup(b):
    s = BeautifulSoup(b, 'html.parser')
    for x in s(['script', 'style', 'noscript', 'svg']):
        x.decompose()
    return s


def T(el):
    return re.sub(r'\s+', ' ', el.get_text(' ')).strip() if el else ''


def num(text):
    m = re.search(r'-?\d+(?:\.\d+)?', (text or '').replace('－', '-').replace('−', '-'))
    return float(m.group()) if m else None


def is_open(text):
    return any(k in text for k in OPEN_MARKS)


def table_counts(s, name_word, status_words=('可否', '状況')):
    """見出しに name_word(リフト名/コース名)を含む表の、行数と営業中の数を数える。"""
    total = op = 0
    for t in s.find_all('table'):
        rows = t.find_all('tr')
        if not rows:
            continue
        head = [T(c) for c in rows[0].find_all(['th', 'td'])]
        if not any(name_word in h for h in head):
            continue
        si = next((i for i, h in enumerate(head) if any(w in h for w in status_words)), None)
        if si is None:
            continue
        for r in rows[1:]:
            cells = r.find_all(['th', 'td'])
            if len(cells) <= si:
                continue
            total += 1
            st = T(cells[si])
            img = cells[si].find('img')
            if img and img.get('alt'):
                st += ' ' + img['alt']
            if is_open(st):
                op += 1
    return (op, total) if total else (None, None)


def notice_from(text):
    """オープン日の告知を探す(「オープン予定」を優先し、なければ「オープン決定」など)。"""
    for kw in (r'(?:オープン|OPEN)予定', r'オープン決定|全面オープン'):
        for m in re.finditer(r'[^。！!\s]{0,30}(?:' + kw + r')[^。\s]{0,20}', text):
            # パーク・ナイター・キッズ広場など、一部の施設だけのオープン日は除く
            if re.search(PART_WORDS, text[max(0, m.start() - 40):m.end()]):
                continue
            return m.group().strip(' ！!')[:60]
    return None


PART_WORDS = r'パーク|PARK|Park|ナイト|ナイター|キッズ|KIDS|Baboon|バブーン|ゴンドラ|限定'


def to_iso(text, now):
    """「12月11日」「12/11」から日付(YYYY-MM-DD)を作る。年は今シーズン(10〜12月は今年、1〜5月は翌年)。"""
    if not text:
        return None
    m = re.search(r'(?<![\d/])(\d{1,2})月(\d{1,2})日', text) or re.search(r'(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])', text)
    if not m:
        return None
    mo, dy = int(m.group(1)), int(m.group(2))
    season = now.year if now.month >= 6 else now.year - 1
    y = season if mo >= 6 else season + 1
    try:
        return datetime.date(y, mo, dy).isoformat()
    except ValueError:
        return None


def parse_template(r, B):
    s = soup(B['cond'])
    d = {}
    tm = s.select_one('section.date time') or s.find('time')
    d['site_updated'] = T(tm).replace('更新', '').strip() or None
    w = s.select_one('div.weather')
    if w:
        lis = [T(li) for li in w.select('ul li')
               if not {'btn', 'condition', 'ico'} & set(li.get('class') or []) and T(li)]
        d['weather'] = lis[0] if lis else None
        d['status_text'] = T(w.select_one('li.condition')) or None
        for dt in w.select('dl.snow dt'):
            v = T(dt.find_next_sibling('dd'))
            if '積雪' in T(dt):
                d['snow_cm'] = num(v)
            if '気温' in T(dt):
                d['temp_c'] = num(v)
    else:  # 高鷲・ダイナ型(山頂/中腹の表)
        for t in s.select('table.table_wes'):
            label = T(t.find('th'))
            for tr in t.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) < 2:
                    continue
                k, v = T(tds[-2]), T(tds[-1])
                if '積雪' in k and num(v) is not None and d.get('snow_cm') is None:
                    d['snow_cm'] = num(v)
                    d['snow_where'] = label.replace('の状況', '')
                if '気温' in k and num(v) is not None and d.get('temp_c') is None:
                    d['temp_c'] = num(v)
        # 高鷲・ダイナの新しい作り(2026-11〜):div.weather-wrapper の li.weather / condition / snow / temperature
        ww = s.select_one('div.weather-wrapper')
        if ww:
            def li(cls):
                return T(ww.select_one('li.' + cls))
            if not d.get('weather'):
                d['weather'] = li('weather') or None
            if not d.get('status_text'):
                d['status_text'] = li('condition') or None
            if d.get('snow_cm') is None:
                d['snow_cm'] = num(li('snow'))
            if d.get('temp_c') is None:
                d['temp_c'] = num(li('temperature'))
    d['lifts_open'], d['lifts_total'] = table_counts(s, 'リフト名')
    d['courses_open'], d['courses_total'] = table_counts(s, 'コース名')
    d['notice'] = notice_from(T(s))
    return d


def parse_whitepia(r, B):
    s = soup(B['top'])
    d = {}
    box = s.select_one('.fl_weather')
    if box:
        d['weather'] = T(box.select_one('.el_weather')) or None
        ths = [T(x) for x in box.select('table.tb_weather th')]
        if len(ths) >= 4:
            d['temp_c'], d['snow_cm'] = num(ths[0]), num(ths[2])
        dt = T(box.select_one('.el_date'))
        d['site_updated'] = None if re.search(r'-\s*-', dt) else dt
    c = soup(B['cond'])
    d['lifts_open'], d['lifts_total'] = table_counts(c, 'リフト名')
    d['courses_open'], d['courses_total'] = table_counts(c, 'コース名')
    d['notice'] = notice_from(T(s))
    a = s.select_one('a.el_news_btn')
    if a:
        tm = a.find('time')
        d['news'] = {'date': tm.get('datetime') if tm else None, 'title': T(a.find('h5')), 'url': a.get('href')}
    return d


def parse_meiho(r, B):
    s = soup(B['top'])
    d = {}
    for row in s.select('.p-topInfoClimate__row'):
        k, v = T(row.find('dt')), T(row.find('dd'))
        if '積雪' in k:
            d['snow_cm'] = num(v)
        if '山頂' in k:
            d['temp_c'] = num(v)
            d['temp_where'] = '山頂'
    c = soup(B['cond'])
    st = c.select('.p-gelandeCourse__item .p-gelandeCourse__status')
    if st:
        d['courses_total'] = len(st)
        d['courses_open'] = sum(1 for x in st if is_open(T(x)) or '--open' in x.get('class', []))
    d['lifts_open'], d['lifts_total'] = table_counts(c, 'リフト名', ('稼動', '稼働', '状況'))
    d['notice'] = notice_from(T(s))
    return d


def ic_open(el):
    ic = el.select_one('span.ic') if el else None
    return bool(ic) and 'close' not in ic.get('class', [])


def parse_wing(r, B):
    s = soup(B['top'])
    d = {}
    sp = s.select_one('.view_sp ul.wrp_wea')
    if sp:
        for li in sp.find_all('li', recursive=False):
            k = T(li.select_one('.sst'))
            nums = [num(T(x)) for x in li.select('.number')]
            if k.startswith('天気'):
                d['weather'] = T(li.select_one('.text')) or None
            if '積雪' in k and nums:
                d['snow_cm'] = nums[0]
            # 気温は「最高/最低」の予報値なので、現在の気温としては使わない
    c = soup(B['cond'])
    lt = []
    for t in c.select('table.tbl_basic3'):
        rows = t.find_all('tr')
        if rows and 'リフト名' in T(rows[0]):
            lt += rows[1:]
    if lt:
        d['lifts_total'] = len(lt)
        d['lifts_open'] = sum(1 for tr in lt if ic_open(tr))
    gere = c.select_one('.con_gere')
    items = gere.select_one('.box_info').select('.item') if gere and gere.select_one('.box_info') else []
    if items:
        d['courses_total'] = len(items)
        d['courses_open'] = sum(1 for it in items if ic_open(it))
    d['notice'] = notice_from(T(s))
    a = s.select_one('#js-infoSlider a')
    if a:
        d['news'] = {'date': None, 'title': T(a), 'url': a.get('href')}
    return d


def parse_swp(r, B):
    s = soup(B['top'])
    d = {}
    info = s.select_one('#info')
    tx = T(info)
    m = re.search(r'(\d{4}/\d{1,2}/\d{1,2})', tx)
    d['site_updated'] = m.group(1) if m else None
    m = re.search(r'気温\s*/\s*(-?\d+(?:\.\d+)?)', tx)
    d['temp_c'] = float(m.group(1)) if m else None
    m = re.search(r'積雪\s*/\s*(\d+)', tx)
    d['snow_cm'] = float(m.group(1)) if m else None
    w = info.select_one('.weather') if info else None
    d['weather'] = T(w) or None
    for tr in (info.select('tr') if info else []):
        if 'リフト' in T(tr.find('th')):
            marks = re.findall(r'：\s*(\S+)', T(tr.find('td')))
            d['lifts_total'] = len(marks)
            d['lifts_open'] = sum(1 for x in marks if is_open(x))
    p = info.find('p') if info else None
    d['notice'] = T(p) or notice_from(tx)
    return d


def jma():
    """気象庁:美濃地方の予報と、アメダス長滝(郡上市白鳥町、標高430m)の観測値。"""
    d = {}
    try:
        f = json.load(urllib.request.urlopen('https://www.jma.go.jp/bosai/forecast/data/forecast/210000.json', timeout=30))
        ts = f[0]['timeSeries'][0]
        area = next(a for a in ts['areas'] if a['area']['code'] == '210010')
        days = {t[:10]: {'date': t[:10], 'code': c, 'text': w.replace('　', ' ')}
                for t, c, w in zip(ts['timeDefines'], area['weatherCodes'], area['weathers'])}
        # 短期予報の降水確率(6時間ごと)は、その日の最大値を使う
        pts = f[0]['timeSeries'][1]
        pa = next(a for a in pts['areas'] if a['area']['code'] == '210010')
        for t, p in zip(pts['timeDefines'], pa['pops']):
            if t[:10] in days and p != '':
                days[t[:10]]['pop'] = max(int(p), days[t[:10]].get('pop', 0))
        # 週間予報(翌日から7日分)
        wk = f[1]['timeSeries'][0]
        wa = next(a for a in wk['areas'] if a['area']['code'] == '210010')
        for i, t in enumerate(wk['timeDefines']):
            dd = days.setdefault(t[:10], {'date': t[:10], 'code': wa['weatherCodes'][i]})
            if wa['pops'][i] != '' and 'pop' not in dd:
                dd['pop'] = int(wa['pops'][i])
            if wa['reliabilities'][i]:
                dd['rel'] = wa['reliabilities'][i]
        d['forecast'] = {'report': f[0]['reportDatetime'][:16].replace('T', ' '), 'area': '美濃地方',
                         'weekly_report': f[1]['reportDatetime'][:16].replace('T', ' '),
                         'days': [days[k] for k in sorted(days)]}
    except Exception as e:
        d['forecast_error'] = str(e)[:100]
    try:
        lt = urllib.request.urlopen('https://www.jma.go.jp/bosai/amedas/data/latest_time.txt', timeout=30).read().decode()
        key = re.sub(r'\D', '', lt)[:12] + '00'
        m = json.load(urllib.request.urlopen(f'https://www.jma.go.jp/bosai/amedas/data/map/{key}.json', timeout=30))
        st = m.get('52221', {})
        d['amedas'] = {'name': '長滝(郡上市白鳥町・標高430m)', 'time': lt[:16].replace('T', ' '),
                       'temp_c': (st.get('temp') or [None])[0], 'snow_cm': (st.get('snow') or [None])[0]}
    except Exception as e:
        d['amedas_error'] = str(e)[:100]
    return d


PARSERS = dict(template=parse_template, whitepia=parse_whitepia, meiho=parse_meiho, wing=parse_wing, swp=parse_swp)
FIELDS = ('weather', 'status_text', 'snow_cm', 'temp_c', 'lifts_open', 'lifts_total',
          'courses_open', 'courses_total', 'site_updated', 'notice')


def main():
    args = sys.argv[1:]
    rawdir = None
    if '--raw' in args:
        i = args.index('--raw')
        rawdir = args[i + 1]
        del args[i:i + 2]
    out = args[0] if args else 'snow.json'
    nowdt = datetime.datetime.now(JST)
    now = nowdt.strftime('%Y-%m-%d %H:%M')
    res = []
    for r in RESORTS:
        item = {k: r[k] for k in ('id', 'name', 'lat', 'lng', 'drive', 'planned', 'article', 'hotel')}
        item['source'] = r['pages']['cond']
        item['fetched'] = now
        try:
            B = {k: get(u, rawdir, RAW_NAMES.get((r['id'], k), r['id'])) for k, u in r['pages'].items()}
            d = PARSERS[r['kind']](r, B)
            for k in FIELDS:
                item[k] = d.get(k)
            for k in ('snow_where', 'temp_where'):
                if d.get(k):
                    item[k] = d[k]
            item['open'] = (item['lifts_open'] or 0) > 0 or (item['courses_open'] or 0) > 0
            if d.get('news'):
                item['news'] = d['news']
            od = to_iso(item['notice'] if item['notice'] and 'オープン' in item['notice'].upper().replace('OPEN', 'オープン') else None, nowdt)
            item['open_date'] = od or to_iso(r['planned'], nowdt)
            item['open_date_src'] = '公式サイト' if od else '当ブログ調べ・11月23日時点'
            # 公式のお知らせやトップの告知に「延期」とあれば、予定日は出さない
            if not item['open'] and '延期' in ((item.get('news') or {}).get('title') or '') + (item['notice'] or ''):
                item['open_postponed'] = True
                item['open_date'] = None
            item['ok'] = True
        except Exception as e:
            item['ok'] = False
            item['error'] = f'{type(e).__name__}: {e}'[:200]
        res.append(item)
    if not any(x['ok'] for x in res):
        sys.exit('すべてのスキー場の読み取りに失敗したため、前回のデータを残します')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'generated': now, 'jma': jma(), 'resorts': res}, f, ensure_ascii=False, indent=1)
    print('wrote', out)


if __name__ == '__main__':
    main()
