"""Generates the synthetic test corpus served by the `demo-sites` container.

Every firm, person, quote and number here is fictional. Each item carries a
gold label (does it violate / is it a third-party ad / is it shadow advisory)
which the API uses to compute precision and recall in the calibration panel.

Run:  python demo-sites/generate.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent / "site"
SYNTH = '<meta name="iw-synthetic" content="Materiał syntetyczny — korpus testowy InvestWatch">'


def page(*, title: str, site: str, body: str, css: str = "", author: str | None = None, viewport: bool = True,
         published: str = "2026-11-20T10:00:00+01:00") -> str:
    author_meta = f'<meta name="author" content="{author}">' if author else ""
    vp = '<meta name="viewport" content="width=device-width, initial-scale=1">' if viewport else ""
    return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8">{vp}
<title>{title}</title>
<meta property="og:site_name" content="{site}">{author_meta}
<meta property="article:published_time" content="{published}">
{SYNTH}
<style>
body {{ font-family: Arial, sans-serif; font-size: 16px; color: #1a1a1a; background: #ffffff; max-width: 860px; margin: 0 auto; padding: 24px; }}
h1 {{ font-size: 32px; }} .cta {{ background: #0b3d91; color: #ffffff; padding: 12px 18px; display: inline-block; }}
.ad-label {{ font-size: 13px; color: #555555; text-transform: uppercase; }}
{css}
</style></head>
<body>
{body}
</body></html>
"""


M2: list[dict] = []
M1: list[dict] = []
M3: list[dict] = []

# ======================================================================== M2
NORD = "Dom Maklerski Nordwisła S.A."
VIST = "Vistula Invest Dom Maklerski S.A."
MAZ = "Mazowiecki Dom Inwestycyjny S.A."

M2.append(dict(path="m2/01-etf-zgodny.html", label=False, note="Zgodny: ryzyko przy zyskach, 5 lat wyników, opłaty, źródło", html=page(
    title="Fundusze ETF z Nordwisłą", site=NORD, body=f"""
<p class="ad-label">Materiał marketingowy</p>
<h1>Inwestuj w globalne ETF-y z niską prowizją</h1>
<p>Otwórz rachunek w {NORD} i kupuj ETF-y na ponad 20 giełdach.</p>
<p>Indeks MSCI World osiągnął w ostatnich 5 latach średnią stopę zwrotu 9,1% rocznie (pełne okresy 12-miesięczne 2021–2025, źródło: MSCI, dane w PLN, po uwzględnieniu opłat i prowizji).
Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanego kapitału. Wyniki historyczne nie są wiarygodnym wskaźnikiem przyszłych wyników.</p>
<p>Wartość inwestycji w instrumenty notowane w USD lub EUR zależy także od zmian kursów walut, które mogą zwiększyć lub zmniejszyć wynik.</p>
<a class="cta" href="#">Otwórz rachunek</a>
<p>{NORD}, ul. Przykładowa 1, Warszawa — firma inwestycyjna.</p>""")))

M2.append(dict(path="m2/02-cfd-przypis.html", label=True, note="Ryzyko tylko w stopce, mała szara czcionka, brak oznaczenia reklamy", html=page(
    title="CFD na indeksy — zarabiaj na wzrostach i spadkach", site=NORD,
    css=".legal { font-size: 10px; color: #c4c4c4; } footer { margin-top: 80px; }", body=f"""
<h1>Zarabiaj nawet 300% na wzrostach i spadkach</h1>
<p>Handluj kontraktami CFD na DAX, S&amp;P 500 i złoto z dźwignią do 1:30. Twoje zyski mogą rosnąć szybciej niż kiedykolwiek.</p>
<p>Załóż konto w 5 minut i odbierz bonus na start.</p>
<a class="cta" href="#">Zacznij inwestować</a>
<footer><p class="legal">{NORD}. Kontrakty CFD są złożonymi instrumentami i wiążą się z wysokim ryzykiem szybkiej utraty środków pieniężnych z powodu dźwigni finansowej. 74% rachunków inwestorów detalicznych odnotowuje straty.</p></footer>""")))

M2.append(dict(path="m2/03-ryzyko-w-akordeonie.html", label=True, note="Ryzyko schowane w zwiniętej sekcji", html=page(
    title="Konto maklerskie Vistula — 0 zł prowizji", site=VIST, body=f"""
<p class="ad-label">Reklama</p>
<h1>0 zł prowizji od akcji przez pierwsze 3 miesiące</h1>
<p>Inwestorzy {VIST} zarobili w tym roku średnio 14% na akcjach spółek z GPW.</p>
<a class="cta" href="#">Otwórz konto</a>
<details><summary>Informacje prawne i dotyczące ryzyka</summary>
<p>Inwestowanie w akcje wiąże się z ryzykiem utraty części lub całości zainwestowanych środków. Wyniki historyczne nie są gwarancją przyszłych wyników.</p>
</details>""")))

M2.append(dict(path="m2/04-ostrzezenie-po-angielsku.html", label=True, note="Przekaz po polsku, ostrzeżenie po angielsku", html=page(
    title="Forex z Baltic Capital Markets", site="Baltic Capital Markets Ltd", body="""
<p class="ad-label">Materiał reklamowy</p>
<h1>Forex bez tajemnic — inwestuj na parach walutowych</h1>
<p>Dołącz do 200 000 klientów i handluj EUR/USD z najniższym spreadem. Zyski nawet 25% miesięcznie dla aktywnych traderów.</p>
<p>Baltic Capital Markets Ltd jest firmą inwestycyjną działającą w Polsce transgranicznie.</p>
<p>CFDs are complex instruments and come with a high risk of losing money rapidly due to leverage. You should consider whether you can afford to take the high risk of losing your money.</p>
<a class="cta" href="#">Załóż konto demo</a>""")))

M2.append(dict(path="m2/05-wyniki-historyczne.html", label=True, note="Wynik z jednego roku jako nagłówek, brak ostrzeżeń i okresu 5 lat", html=page(
    title="Fundusz Akcji Nordwisła +38%", site=NORD, body=f"""
<p class="ad-label">Reklama</p>
<h1>+38% w 2025 roku!</h1>
<p>Strategia Akcji Polskich {NORD} zarobiła w 2025 roku 38%, a w 2024 roku 21%. Dołącz do zadowolonych inwestorów.</p>
<p>Inwestycje wiążą się z ryzykiem utraty kapitału.</p>
<a class="cta" href="#">Sprawdź strategię</a>""")))

M2.append(dict(path="m2/06-aprobata-knf.html", label=True, note="Sugeruje zatwierdzenie przez KNF i bezpieczeństwo", html=page(
    title="Obligacje korporacyjne Mazowiecki DI", site=MAZ, body=f"""
<p class="ad-label">Materiał marketingowy</p>
<h1>Obligacje z oprocentowaniem 9,5% rocznie</h1>
<p>Oferta zatwierdzona przez Komisję Nadzoru Finansowego — inwestycja w pełni bezpieczna, bo spełniamy rygorystyczne wymogi nadzorcze KNF.</p>
<p>Inwestowanie w obligacje wiąże się z ryzykiem niewypłacalności emitenta i utraty części kapitału.</p>
<p>{MAZ} — firma inwestycyjna.</p>
<a class="cta" href="#">Zapisz się na obligacje</a>""")))

M2.append(dict(path="m2/07-ike-prognoza.html", label=True, note="Korzyści podatkowe bez zastrzeżeń, prognoza bez ostrzeżenia", html=page(
    title="IKE z Vistula Invest", site=VIST, body=f"""
<p class="ad-label">Reklama</p>
<h1>IKE — oszczędzaj bez podatku Belki</h1>
<p>Na IKE w {VIST} nie zapłacisz 19% podatku od zysków kapitałowych.</p>
<p>Nasz portfel modelowy w przyszłym roku osiągnie 12% zysku — przewidujemy dalsze wzrosty indeksów.</p>
<p>Inwestowanie wiąże się z ryzykiem utraty części środków.</p>
<a class="cta" href="#">Otwórz IKE</a>""")))

M2.append(dict(path="m2/08-obligacje-zgodne.html", label=False, note="Zgodny: zastrzeżenia podatkowe i ryzyko obok zysku", html=page(
    title="Obligacje skarbowe przez rachunek maklerski", site=MAZ, body=f"""
<p class="ad-label">Materiał reklamowy</p>
<h1>Obligacje skarbowe na rachunku maklerskim</h1>
<p>Kupuj obligacje skarbowe notowane na Catalyst z oprocentowaniem zależnym od inflacji. Inwestowanie w obligacje wiąże się z ryzykiem zmiany ich ceny i utraty części kapitału przy sprzedaży przed terminem.</p>
<p>Traktowanie podatkowe zależy od indywidualnej sytuacji klienta i może ulec zmianie w przyszłości.</p>
<p>{MAZ}, firma inwestycyjna nadzorowana przez KNF.</p>
<a class="cta" href="#">Sprawdź ofertę</a>""")))

M2.append(dict(path="m2/09-niski-kontrast.html", label=True, note="Ryzyko widoczne, ale bladoszare i mniejsze", html=page(
    title="Akcje amerykańskie od 1 dolara", site=NORD, css=".risk { color: #c9c9c9; font-size: 12px; }", body=f"""
<p class="ad-label">Reklama</p>
<h1>Akcje Apple, Tesli i Nvidii już od 1 dolara</h1>
<p>Kupuj ułamkowe akcje z {NORD}. Zyskuj na wzrostach największych spółek świata.</p>
<p class="risk">Inwestowanie w akcje wiąże się z ryzykiem utraty kapitału oraz ryzykiem walutowym wynikającym ze zmian kursów walut.</p>
<a class="cta" href="#">Otwórz konto</a>""")))

M2.append(dict(path="m2/10-prognoza-zgodna.html", label=False, note="Zgodny: prognoza z wymaganym ostrzeżeniem", html=page(
    title="Raport kwartalny — perspektywy rynku", site=VIST, body=f"""
<p class="ad-label">Komunikat marketingowy</p>
<h1>Perspektywy rynku akcji na 2026</h1>
<p>Nasi analitycy przewidujemy umiarkowane wzrosty indeksu WIG20 w przyszłym roku. Prognozy nie są wiarygodnym wskaźnikiem przyszłych wyników.</p>
<p>Inwestowanie w akcje wiąże się z ryzykiem utraty części lub całości kapitału. Opisane zyski nie są gwarantowane.</p>
<p>{VIST}.</p>
<a class="cta" href="#">Pobierz raport</a>""")))

M2.append(dict(path="m2/11-porownanie-z-lokata.html", label=True, note="Porównanie z lokatą bez źródła (subtelne naruszenie)", html=page(
    title="Lepsze niż lokata", site=MAZ, body=f"""
<p class="ad-label">Reklama</p>
<h1>Fundusz obligacji lepszy niż lokata bankowa</h1>
<p>Nasz fundusz obligacji daje wyższy zwrot niż lokata w banku. Inwestowanie w fundusz wiąże się z ryzykiem utraty części kapitału, a zysk nie jest gwarantowany.</p>
<p>{MAZ}.</p>
<a class="cta" href="#">Sprawdź fundusz</a>""")))

M2.append(dict(path="m2/12-mobile-nowrap.html", label=True, note="Ryzyko w bloku bez zawijania o stałej szerokości (ucinane na telefonie)", html=page(
    title="Kryptowaluty ETN", site=NORD, viewport=False,
    css=".banner-risk { white-space: nowrap; width: 980px; overflow: hidden; }", body=f"""
<p class="ad-label">Reklama</p>
<h1>ETN na bitcoina na rachunku maklerskim</h1>
<p>Inwestuj w bitcoina bez portfela kryptowalut. Zyski z ETN mogą być wysokie.</p>
<p class="banner-risk">Instrumenty ETN na kryptowaluty są bardzo zmienne i wiążą się z ryzykiem utraty całości zainwestowanego kapitału.</p>
<p>{NORD}.</p>
<a class="cta" href="#">Kup ETN</a>""")))

M2.append(dict(path="m2/13-drobniejsza-czcionka.html", label=False, note="Zgodny z uwagą: ryzyko nieco mniejszą czcionką", html=page(
    title="Lokata strukturyzowana", site=VIST, css=".note { font-size: 15px; }", body=f"""
<p class="ad-label">Materiał reklamowy</p>
<h1>Produkt strukturyzowany z ochroną 90% kapitału</h1>
<p>Zysk powiązany z indeksem WIG20, maksymalnie 7% w skali roku.</p>
<p class="note">Produkt wiąże się z ryzykiem utraty do 10% zainwestowanego kapitału oraz ryzykiem kredytowym emitenta. Zysk nie jest gwarantowany.</p>
<p>{VIST}.</p>
<a class="cta" href="#">Dowiedz się więcej</a>""")))

# ======================================================================== M1
M1.append(dict(path="m1/01-blog-finfluencera.html", label=True, note="Blog z kodem polecającym, bez oznaczenia reklamy", html=page(
    title="Jak zarobiłem pierwsze 10 000 zł na giełdzie", site="Blog Młody Inwestor", author="Kuba z bloga Młody Inwestor", body=f"""
<h1>Jak zarobiłem pierwsze 10 000 zł na giełdzie</h1>
<p>Od dwóch lat inwestuję przez {VIST} i jestem mega zadowolony — zero prowizji, świetna aplikacja.</p>
<p>Załóż konto z mojego linku poniżej i wpisz mój kod polecający MLODY50, a dostaniesz 50 zł bonusu na start!</p>
<p>Mój portfel zarobił w tym roku 32%. Serio, polecam każdemu.</p>
<a href="#">Załóż konto — link polecający</a>""")))

M1.append(dict(path="m1/02-ranking-brokerow.html", label=True, note="Ranking z linkami partnerskimi", html=page(
    title="Ranking brokerów 2026 — który wybrać?", site="FinRanking", author="Redakcja FinRanking", body=f"""
<h1>Ranking brokerów 2026</h1>
<p>1. {MAZ} — najlepszy broker dla początkujących. Skorzystaj z naszego linku partnerskiego i odbierz bonus na start.</p>
<p>2. {NORD} — szeroka oferta ETF.</p>
<p>Ranking zawiera linki afiliacyjne — możemy otrzymać prowizję.</p>""")))

M1.append(dict(path="m1/03-artykul-prasowy.html", label=False, note="Neutralny artykuł prasowy (wzmianka, nie reklama)", html=page(
    title="Vistula Invest zwiększa zatrudnienie", site="Gazeta Gospodarcza Demo", author="Redakcja", body=f"""
<h1>Vistula Invest zwiększa zatrudnienie w Krakowie</h1>
<p>{VIST} poinformował o otwarciu nowego biura w Krakowie i zatrudnieniu 40 analityków. Według zarządu firma koncentruje się na obsłudze klientów instytucjonalnych.</p>
<p>W trzecim kwartale liczba rachunków w sektorze maklerskim wzrosła o 3%.</p>""")))

SOCIAL = [
    dict(path="social/instagram-post-01.json", label=True, note="Instagram: współpraca z firmą zagraniczną, bonus", post={
        "platform": "instagram", "id": "IG-3301", "author": "@kasia.inwestuje", "followers": 84200,
        "url": "https://instagram.example/p/IG-3301", "published_at": "2026-11-20T18:04:00+01:00",
        "text": "Od dziś handluję z Baltic Capital Markets Ltd 🚀 Odbierz bonus na start z linku w bio! #współpraca #forex #zarabiaj"}),
    dict(path="social/tiktok-video-01.json", label=True, note="TikTok: darmowe akcje za rejestrację z linku", post={
        "platform": "tiktok", "id": "TT-99120", "author": "@zysk.codziennie", "followers": 212000,
        "url": "https://tiktok.example/@zysk.codziennie/video/99120", "published_at": "2026-11-21T09:12:00+01:00",
        "text": "3 darmowe akcje za założenie konta w Dom Maklerski Nordwisła S.A.! Link w bio, mój kod: ZYSK3. Ja zarobiłem już 40% 💸"}),
    dict(path="social/facebook-post-01.json", label=False, note="Facebook: informacja prasowa, bez promocji", post={
        "platform": "facebook", "id": "FB-5521", "author": "Portal Rynki Demo", "followers": 15300,
        "url": "https://facebook.example/rynkidemo/posts/5521", "published_at": "2026-11-19T11:30:00+01:00",
        "text": "Dom Maklerski Nordwisła S.A. otworzył nowy oddział w Gdańsku. Firma zatrudnia obecnie 320 osób."}),
    dict(path="social/youtube-desc-01.json", label=True, note="YouTube: sponsor odcinka z kodem", post={
        "platform": "youtube", "id": "YT-ab12", "author": "Inwestowanie po Godzinach", "followers": 56000,
        "url": "https://youtube.example/watch?v=ab12", "published_at": "2026-11-18T20:00:00+01:00",
        "text": "Sponsor odcinka: Vistula Invest Dom Maklerski S.A. — załóż konto z kodem GODZINY i odbierz bonus na start. Inwestowanie wiąże się z ryzykiem."}),
    dict(path="social/telegram-vip-01.json", label=True, module="m3", note="Telegram: płatne sygnały VIP (doradztwo)", post={
        "platform": "telegram", "id": "TG-777", "author": "Sygnały GPW VIP", "followers": 9100,
        "url": "https://t.example/sygnalygpwvip/777", "published_at": "2026-11-21T07:45:00+01:00",
        "text": "Dołącz do grupy VIP: codziennie sygnały kupna i sprzedaży akcji z GPW dopasowane do Twojego portfela. Abonament 199 zł/mies. Dziś kupuj CD Projekt, cel cenowy 250 zł!"}),
]

META_ADS = {
    "path": "social/meta-ad-library.json",
    "note": "Odpowiedź w formacie Meta Ad Library API (ads_archive)",
    "data": [
        {"id": "AD-880011", "page_name": "Finanse z Olą", "ad_creative_bodies": [
            "Zacznij inwestować z Mazowiecki Dom Inwestycyjny S.A. — skorzystaj z mojego kodu OLA100 i odbierz bonus! #współpraca"],
         "ad_snapshot_url": "https://facebook.example/ads/library/?id=AD-880011", "ad_delivery_start_time": "2026-11-17",
         "publisher_platforms": ["facebook", "instagram"], "_label": True},
        {"id": "AD-880012", "page_name": "Złota Ścieżka Wealth Management", "ad_creative_bodies": [
            "Złota Ścieżka Wealth Management Sp. z o.o. — indywidualne strategie inwestycyjne dopasowane do Twojego profilu ryzyka. Umów pierwszą konsultację inwestycyjną (490 zł) i dowiedz się, które akcje i ETF-y kupić."],
         "ad_snapshot_url": "https://facebook.example/ads/library/?id=AD-880012", "ad_delivery_start_time": "2026-11-15",
         "publisher_platforms": ["facebook"], "_label": True, "_module": "m3"},
        {"id": "AD-880013", "page_name": "Kurs Oszczędzania", "ad_creative_bodies": [
            "Darmowy e-book: jak zbudować fundusz awaryjny i zaplanować budżet domowy. Materiał ma charakter edukacyjny."],
         "ad_snapshot_url": "https://facebook.example/ads/library/?id=AD-880013", "ad_delivery_start_time": "2026-11-12",
         "publisher_platforms": ["instagram"], "_label": False, "_module": "m3"},
    ],
}

# ======================================================================== M3
M3.append(dict(path="m3/01-family-office.html", label=True, note="Family office spoza rejestru, rekomendacje zakupu, success fee", html=page(
    title="Kowalski & Partners Family Office", site="Kowalski & Partners Family Office", body="""
<h1>Kowalski &amp; Partners Family Office</h1>
<p>Zarządzanie majątkiem rodzinnym i indywidualne strategie inwestycyjne dla zamożnych rodzin.</p>
<p>Na podstawie analizy Twojej sytuacji rekomendujemy zakup konkretnych akcji, obligacji i funduszy ETF oraz wskazujemy, kiedy sprzedać.</p>
<p>Wynagrodzenie: success fee 20% od zysku powyżej 8% rocznie. Umów pierwszą konsultację 1:1.</p>""")))

M3.append(dict(path="m3/02-wealth-management.html", label=True, note="Wealth management spoza rejestru, płatne konsultacje", html=page(
    title="Złota Ścieżka Wealth Management", site="Złota Ścieżka Wealth Management", body="""
<h1>Złota Ścieżka Wealth Management Sp. z o.o.</h1>
<p>Spersonalizowany portfel inwestycyjny dopasowany do Twoich celów inwestycyjnych i profilu ryzyka.</p>
<p>Doradzamy, w które spółki z GPW i fundusze inwestować. Pakiet Premium: 690 zł/mies.</p>
<p>Gwarantujemy zysk wyższy niż inflacja.</p>""")))

M3.append(dict(path="m3/03-licencjonowany-doradca.html", label=False, note="Licencjonowana firma z doradztwem w zakresie zezwolenia", html=page(
    title="Doradztwo inwestycyjne — Vistula Invest", site=VIST, body=f"""
<h1>Doradztwo inwestycyjne</h1>
<p>{VIST} świadczy usługę doradztwa inwestycyjnego na podstawie zezwolenia Komisji Nadzoru Finansowego.</p>
<p>Doradca przygotuje indywidualne rekomendacje dotyczące akcji i obligacji na podstawie Twojego profilu ryzyka.</p>
<p>Inwestowanie wiąże się z ryzykiem utraty części lub całości kapitału.</p>""")))

M3.append(dict(path="m3/04-blog-edukacyjny.html", label=False, note="Blog edukacyjny z zastrzeżeniem", html=page(
    title="Czym jest ETF? Poradnik", site="Akademia Oszczędzania Demo", author="Akademia Oszczędzania", body="""
<h1>Czym jest ETF i jak działa?</h1>
<p>ETF to fundusz notowany na giełdzie, który odwzorowuje indeks. Wyjaśniamy, jak działają opłaty i dywersyfikacja.</p>
<p>Materiał ma charakter wyłącznie edukacyjny i nie stanowi porady inwestycyjnej ani rekomendacji.</p>""")))

M3.append(dict(path="m3/05-konsulting-firmowy.html", label=False, note="Doradztwo biznesowe (nie inwestycyjne)", html=page(
    title="Consulting dla MŚP", site="Optima Business Consulting", body="""
<h1>Optima Business Consulting</h1>
<p>Pomagamy małym firmom obniżać koszty, planować budżet i przygotować wniosek o dotację.</p>
<p>Pierwsza konsultacja online jest bezpłatna.</p>""")))

M3.append(dict(path="m3/06-kurs-co-kupic.html", label=True, note="Kurs z rekomendacjami 'co kupić' w abonamencie", html=page(
    title="Akademia Tradera Pro — kurs i sygnały", site="Akademia Tradera Pro", body="""
<h1>Akademia Tradera Pro</h1>
<p>W ramach abonamentu co tydzień powiemy Ci, co kupić: wybrane akcje i kryptowaluty na 2026 rok.</p>
<p>Dostęp VIP: 149 zł miesięcznie. Kupuj razem z nami!</p>""")))


def main() -> None:
    manifest: list[dict] = []
    for module, items in (("m2", M2), ("m1", M1), ("m3", M3)):
        for it in items:
            p = ROOT / it["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            day = 8 + (sum(map(ord, it["path"])) % 14)  # spread publication dates over 8–21 Nov
            hour = 7 + (len(it["path"]) * 3) % 14
            html = it["html"].replace("2026-11-20T10:00:00+01:00", f"2026-11-{day:02d}T{hour:02d}:15:00+01:00")
            p.write_text(html, encoding="utf-8")
            manifest.append({"path": it["path"], "kind": "html", "module": module, "label": it["label"], "note": it["note"]})
    for it in SOCIAL:
        p = ROOT / it["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(it["post"], ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append({"path": it["path"], "kind": "social", "module": it.get("module", "m1"), "label": it["label"], "note": it["note"]})
    p = ROOT / META_ADS["path"]
    p.write_text(json.dumps({"data": [{k: v for k, v in ad.items() if not k.startswith("_")} for ad in META_ADS["data"]]},
                            ensure_ascii=False, indent=2), encoding="utf-8")
    manifest.append({"path": META_ADS["path"], "kind": "meta_ads", "module": "m1", "label": None, "note": META_ADS["note"],
                     "items": {ad["ad_snapshot_url"]: {"module": ad.get("_module", "m1"), "label": ad["_label"]} for ad in META_ADS["data"]}})
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>InvestWatch — korpus testowy</title><h1>Korpus testowy InvestWatch</h1><ul>"
        + "".join(f'<li><a href="{m["path"]}">{m["path"]}</a> — {m["note"]}</li>' for m in manifest) + "</ul>",
        encoding="utf-8")
    print(f"generated {len(manifest)} items into {ROOT}")


if __name__ == "__main__":
    main()
