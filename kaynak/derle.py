#!/usr/bin/env python3
"""Ahvâl-i Şahsiyye · kaynak dosyalarından index.html üretir.

Kullanım:  python3 kaynak/derle.py
Okur:      kaynak/01.txt … 11.txt (üniteler), kaynak/sorular.txt, kaynak/kisiler.txt, kaynak/sinav.txt (boş olabilir), kaynak/sablon.html,
           kaynak/bildir.html ve kaynak/altcubuk.html (Giray Akademi ortak parçaları)
Yazar:     index.html (depo kökü)

Ünite dosyası biçimi:
  # Ünite başlığı            > giriş cümlesi
  ## Bölüm başlığı           ### Alt başlık        #### Küçük alt başlık
  ¶ düz paragraf              - madde              1. numaralı madde
  : Terim = tanım            (kavram kartı ve teste girer)
  ! not kutusu               !! dikkat kutusu (karıştırılan / eleştiri)
  ~ örnek kutusu             ?? soru | cevap  (soru–cevap kutusu)
  @ Arapça metin | açıklama  (ayet / Arapça blok; açıklama isteğe bağlı)
  >> adım                    (art arda gelenler numaralı adım şeridi olur)
  | a | b | c                (tablo satırı; art arda gelenler tek tablo, ilk satır başlık)
  * hızlı tekrar maddesi     (ünite sonundaki "Hızlı tekrar" kutusunda toplanır)
  % ek kutusu (kaynakta olmayan, onay bekleyen tamamlama)
  **kalın**  «Arapça»  [[satır içi ek]] (onay bekleyen tamamlama)
Şema blokları (art arda gelen satırlar tek blok olur):
  Karar ağacı (adım adım, bütün şema, kendini dene):   ^# Başlık | Arapça başlık
     ^? Soru | Arapça            soru düğümü; seçenekleri bir girinti (2 boşluk) içeride
     ^  - Seçenek                seçenek; altındaki soru ya da sonuç bir girinti daha içeride
     ^    = tür | Hüküm | Arapça | Not     tür: caiz · degil · ihtilaf · bilgi
  Açılır kart (liste niteliğindeki şemalar):            &# Başlık | Arapça başlık
     & Grup başlığı | Arapça     &- madde
Görüş eşleştirmesi kaynak/kisiler.txt dosyasından gelir (ünite | bölüm | görüş | görüş sahibi).
"""
import json, re, sys
from pathlib import Path

K = Path(__file__).resolve().parent
KOK = K.parent


def hata(msg):
    sys.exit('HATA: ' + msg)


def hucre(s):
    s = s.strip()
    if s.startswith('|'):
        s = s[1:]
    return [c.strip() for c in s.split(' | ')] if ' | ' in s else [c.strip() for c in s.split('|')]


def iki(x):
    """'metin | arapça' → (metin, arapça); arapça boş olabilir."""
    a, _, b = x.partition('|')
    return a.strip(), b.strip()


def agac_oku(satirlar, ad):
    """^ ile başlayan satırları ağaca çevirir. Girinti: 2 boşluk = 1 seviye."""
    bas = satirlar[0][1:].strip()
    if not bas.startswith('# '):
        hata(f'{ad}: ağaç "^# Başlık" ile başlamalı')
    t, a = iki(bas[2:])
    ogeler = []
    for s in satirlar[1:]:
        g = s[1:]
        bos = len(g) - len(g.lstrip(' '))
        if bos % 2:
            hata(f'{ad}: ağaçta tek sayıda boşluk: {s[:40]}')
        ogeler.append((bos // 2, g.strip()))
    def dugum(i, d):
        sev, x = ogeler[i]
        if sev != d:
            hata(f'{ad}: ağaçta girinti hatası: {x[:40]}')
        if x.startswith('? '):
            q, qa = iki(x[2:])
            n = {'q': q.strip(), 'a': qa.strip(), 'o': []}
            i += 1
            while i < len(ogeler) and ogeler[i][0] == d + 1 and ogeler[i][1].startswith('- '):
                sec = {'x': ogeler[i][1][2:].strip()}
                i += 1
                if i >= len(ogeler) or ogeler[i][0] != d + 2:
                    hata(f'{ad}: "{sec["x"]}" seçeneğinin altı boş')
                sec['n'], i = dugum(i, d + 2)
                n['o'].append(sec)
            if len(n['o']) < 2:
                hata(f'{ad}: "{q}" sorusunda en az iki seçenek olmalı')
            return n, i
        if x.startswith('= '):
            p = [y.strip() for y in x[2:].split(' | ')] + ['', '', '']
            if p[0] not in ('caiz', 'degil', 'ihtilaf', 'bilgi'):
                hata(f'{ad}: sonuç türü caiz/degil/ihtilaf/bilgi olmalı: {x[:40]}')
            return {'s': p[0], 'x': p[1], 'a': p[2], 'not': p[3]}, i + 1
        hata(f'{ad}: ağaçta tanınmayan satır: {x[:40]}')
    kok, son = dugum(0, 0)
    if son != len(ogeler):
        hata(f'{ad}: ağaçta fazla satır: {ogeler[son][1][:40]}')
    return {'k': 'agac', 't': t.strip(), 'a': a.strip(), 'r': kok}


def kart_oku(satirlar, ad):
    bas = satirlar[0]
    if not bas.startswith('&# '):
        hata(f'{ad}: açılır kart "&# Başlık" ile başlamalı')
    t, a = iki(bas[3:])
    g = []
    for s in satirlar[1:]:
        if s.startswith('&- '):
            if not g:
                hata(f'{ad}: maddeden önce "& Grup" gerekli')
            g[-1]['m'].append(s[3:].strip())
        elif s.startswith('& '):
            h, ha = iki(s[2:])
            g.append({'h': h.strip(), 'a': ha.strip(), 'm': []})
        else:
            hata(f'{ad}: kartta tanınmayan satır: {s[:40]}')
    return {'k': 'kart', 't': t.strip(), 'a': a.strip(), 'g': g}


def unite_oku(yol):
    u = {'t': '', 'intro': '', 's': [], 'ht': []}
    sec = None
    blok, bt = [], None   # şema bloğu (^ ağaç, & kart)
    satirlar = yol.read_text(encoding='utf-8').splitlines() + ['']
    for no, satir in enumerate(satirlar, 1):
        s = satir.rstrip()
        tur = '^' if s.startswith('^') else '&' if s.startswith('&') else None
        if blok and tur != bt:
            sec['b'].append(agac_oku(blok, yol.name) if bt == '^' else kart_oku(blok, yol.name))
            blok, bt = [], None
        if tur:
            if sec is None:
                hata(f'{yol.name}:{no} bölüm başlığından önce şema')
            if blok and s[1:].lstrip().startswith('# ') and s[:2] in ('^#', '&#'):
                sec['b'].append(agac_oku(blok, yol.name) if bt == '^' else kart_oku(blok, yol.name))
                blok = []
            blok.append(s); bt = tur
            continue
        if not s.strip():
            continue
        if s.startswith('## '):
            sec = {'h': s[3:].strip(), 'b': []}
            u['s'].append(sec)
            continue
        if s.startswith('# '):
            u['t'] = s[2:].strip()
            continue
        if s.startswith('> '):
            u['intro'] = s[2:].strip()
            continue
        if sec is None:
            hata(f'{yol.name}:{no} bölüm başlığından önce içerik')
        b = sec['b']
        son = b[-1] if b else None
        if s.startswith('#### '):
            b.append({'k': 'h5', 'x': s[5:].strip()})
        elif s.startswith('### '):
            b.append({'k': 'h', 'x': s[4:].strip()})
        elif s.startswith('| ') or s == '|' or s.startswith('| |'):
            satir_h = [c.strip() for c in s.split('|')[1:]]
            if son and son['k'] == 'tbl':
                son['r'].append(satir_h)
            else:
                b.append({'k': 'tbl', 'r': [satir_h]})
        elif s.startswith('>> '):
            if son and son['k'] == 'steps':
                son['x'].append(s[3:].strip())
            else:
                b.append({'k': 'steps', 'x': [s[3:].strip()]})
        elif s.startswith('* '):
            u['ht'].append({'s': len(u['s']) - 1, 'x': s[2:].strip()})
        elif s.startswith('!! '):
            b.append({'k': 'dikkat', 'x': s[3:].strip()})
        elif s.startswith('! '):
            b.append({'k': 'not', 'x': s[2:].strip()})
        elif s.startswith('% '):
            b.append({'k': 'ek', 'x': s[2:].strip()})
        elif s.startswith('~ '):
            b.append({'k': 'ornek', 'x': s[2:].strip()})
        elif s.startswith('?? '):
            if ' | ' not in s:
                hata(f'{yol.name}:{no} soru–cevap satırında " | " yok')
            q, a = s[3:].split(' | ', 1)
            b.append({'k': 'sc', 'q': q.strip(), 'x': a.strip()})
        elif s.startswith('@ '):
            a, m = (s[2:].split(' | ', 1) + [''])[:2]
            b.append({'k': 'ar', 'a': a.strip(), 'x': m.strip()})
        elif s.startswith('¶ '):
            b.append({'k': 'p', 'x': s[2:].strip()})
        elif s.startswith('- '):
            b.append({'k': 'li', 'x': s[2:].strip()})
        elif s.startswith(': '):
            if ' = ' not in s:
                hata(f'{yol.name}:{no} tanım satırında " = " yok')
            t, d = s[2:].split(' = ', 1)
            b.append({'k': 'd', 't': t.strip(), 'x': d.strip()})
        elif re.match(r'^\d+\.\s', s):
            n, x = s.split('.', 1)
            b.append({'k': 'n', 'n': int(n), 'x': x.strip()})
        else:
            hata(f'{yol.name}:{no} tanınmayan satır: {s[:40]}')
    if not u['t'] or not u['s']:
        hata(f'{yol.name} başlık veya bölüm eksik')
    for sec in u['s']:
        for b in sec['b']:
            if b['k'] == 'tbl':
                n = len(b['r'][0])
                for r in b['r']:
                    if len(r) != n:
                        hata(f'{yol.name}: "{sec["h"]}" tablosunda sütun sayısı tutmuyor: {r[:2]}')
    return u


def kisiler(uniteler):
    """kisiler.txt: ünite | bölüm başlığı | ifade | kişi  →  eşleştirme listesi (e = ifade, m = kişi)."""
    out = []
    for no, s in enumerate((K / 'kisiler.txt').read_text(encoding='utf-8').splitlines(), 1):
        if not s.strip() or s.startswith('#'):
            continue
        p = [x.strip() for x in s.split('|')]
        if len(p) != 4:
            hata(f'kisiler.txt:{no} dört alan olmalı')
        ui = int(p[0]) - 1
        bas = [x['h'] for x in uniteler[ui]['s']]
        if p[1] not in bas:
            hata(f'kisiler.txt:{no} "{p[1]}" bölümü {p[0]}. ünitede yok')
        if ',' in p[2]:
            hata(f'kisiler.txt:{no} ifadede virgül olmamalı')
        out.append({'u': ui, 's': bas.index(p[1]), 'e': p[2], 'm': p[3], 'not': ''})
    return out


def sorular_oku(yol, adet):
    out, q = [], None
    for no, s in enumerate(yol.read_text(encoding='utf-8').splitlines(), 1):
        if not s.strip() or s.startswith('#'):
            continue
        if s.startswith('? '):
            if q:
                out.append(q)
            u, metin = s[2:].split('|', 1)
            q = {'u': int(u) - 1, 'q': metin.strip(), 'a': [], 'x': ''}
        elif s.startswith('+ '):
            q['a'].insert(0, s[2:].strip())
        elif s.startswith('- '):
            q['a'].append(s[2:].strip())
        elif s.startswith('= '):
            q['x'] = s[2:].strip()
        else:
            hata(f'{yol.name}:{no} tanınmayan satır')
    if q:
        out.append(q)
    for i, q in enumerate(out):
        if len(q['a']) != 4 or len(set(q['a'])) != 4:
            hata(f'soru {i + 1}: 4 farklı şık olmalı ({q["q"][:40]})')
        if not (0 <= q['u'] < adet):
            hata(f'soru {i + 1}: ünite numarası geçersiz')
        if not q['x']:
            hata(f'soru {i + 1}: açıklama yok')
    return out


def sinav_oku(yol, uniteler):
    gruplar, q = [], None
    for no, s in enumerate(yol.read_text(encoding='utf-8').splitlines(), 1):
        if not s.strip() or s.startswith('#'):
            continue
        if s.startswith('[') and s.endswith(']'):
            gruplar.append({'t': s[1:-1].strip(), 'q': []})
            continue
        if not gruplar:
            hata(f'{yol.name}:{no} önce [sınav başlığı] yazılmalı')
        if s.startswith('? '):
            q = {'q': s[2:].strip(), 'r': [], 'x': [], 'n': ''}
            gruplar[-1]['q'].append(q)
        elif s.startswith('> '):
            u, h = s[2:].split(':', 1)
            ui = int(u) - 1
            basliklar = [x['h'] for x in uniteler[ui]['s']]
            if h.strip() not in basliklar:
                hata(f'{yol.name}:{no} "{h.strip()}" bölümü {u}. ünitede yok')
            q['r'].append([ui, basliklar.index(h.strip())])
        elif s.startswith('= '):
            q['x'].append(s[2:].strip())
        elif s.startswith('! '):
            q['n'] = s[2:].strip()
        else:
            hata(f'{yol.name}:{no} tanınmayan satır')
    for g in gruplar:
        for q in g['q']:
            if not q['x']:
                hata(f'sınav sorusu cevapsız: {q["q"][:40]}')
    return gruplar


def main():
    dosyalar = sorted(K.glob('[0-9][0-9].txt'))
    uniteler = [unite_oku(p) for p in dosyalar]
    sorular = sorular_oku(K / 'sorular.txt', len(uniteler))
    sinav = sinav_oku(K / 'sinav.txt', uniteler)
    eser = kisiler(uniteler)
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    veri = (f'const UNITELER = {j(uniteler)};\nconst SORULAR = {j(sorular)};\n'
            f'const SINAV = {j(sinav)};\nconst ESER_T = {j(eser)};')
    sablon = (K / 'sablon.html').read_text(encoding='utf-8')
    for etiket in ('/*VERI*/', '<!--BILDIR-->', '<!--ALTCUBUK-->'):
        if etiket not in sablon:
            hata(f'sablon.html içinde {etiket} yok')
    sablon = sablon.replace('<!--BILDIR-->', (K / 'bildir.html').read_text(encoding='utf-8'))
    sablon = sablon.replace('<!--ALTCUBUK-->', (K / 'altcubuk.html').read_text(encoding='utf-8'))  # ortak alt çubuk (Giray Akademi)
    (KOK / 'index.html').write_text(sablon.replace('/*VERI*/', veri), encoding='utf-8')
    tanim = sum(1 for u in uniteler for s in u['s'] for b in s['b'] if b['k'] == 'd')
    tablo = sum(1 for u in uniteler for s in u['s'] for b in s['b'] if b['k'] == 'tbl')
    agac = sum(1 for u in uniteler for s in u['s'] for b in s['b'] if b['k'] == 'agac')
    kart = sum(1 for u in uniteler for s in u['s'] for b in s['b'] if b['k'] == 'kart')
    ht = sum(len(u['ht']) for u in uniteler)
    print(f'{len(uniteler)} ünite, {sum(len(u["s"]) for u in uniteler)} bölüm, {tanim} tanım, {tablo} tablo, {agac} karar ağacı, {kart} açılır kart, '
          f'{ht} hızlı tekrar maddesi, {len(eser)} görüş eşleştirmesi, {len(sorular)} el ile soru, '
          f'{sum(len(g["q"]) for g in sinav)} sınav sorusu → index.html')


if __name__ == '__main__':
    main()
