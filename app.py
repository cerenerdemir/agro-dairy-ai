# -*- coding: utf-8 -*-
# Agro-Dairy AI | Çiftçi + Kooperatif Modlu Sürüm
# Kurulum:
#   pip install streamlit plotly pandas google-generativeai
# Çalıştırma:
#   streamlit run app.py

import datetime
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

try:
    import google.generativeai as genai
    GENAI_OK = True
except Exception:
    genai = None
    GENAI_OK = False

st.set_page_config(
    page_title="Agro-Dairy AI | Burdur Çiftçisi İçin",
    page_icon="🌾",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------------
# TASARIM (BÜYÜK YAZI, BÜYÜK BUTON, AÇIK YEŞİL/TOPRAK TONLARI)
# ----------------------------------------------------------------------------
CSS = """
<style>
.stApp {background: #f7f4ea;}
.block-container {padding-top: 1.2rem; max-width: 860px;}
.stApp [data-testid="stMarkdownContainer"] p {font-size: 1.25rem; line-height: 1.6; color: #1f2d1f;}
.stApp [data-testid="stWidgetLabel"] p {font-size: 1.45rem !important; font-weight: 700; color: #2f4a2a;}
.stApp [data-testid="stCaptionContainer"] p {font-size: 1.05rem !important; color: #5b6b57;}
.stApp [data-testid="stNumberInput"] input {font-size: 1.9rem !important; font-weight: 800; height: 3.6rem; color: #1b4d1f;}
.stApp [data-testid="stNumberInput"] button {width: 3.4rem;}
.stApp .stButton > button, .stApp .stDownloadButton > button, .stApp [data-testid="stLinkButton"] a {
    min-height: 4.4rem; border-radius: 18px; font-weight: 800; width: 100%;}
.stApp .stButton > button p, .stApp .stDownloadButton > button p, .stApp [data-testid="stLinkButton"] a p {
    font-size: 1.5rem !important; font-weight: 800;}
.stApp div[role="radiogroup"] {gap: 0.8rem; display: flex; flex-wrap: wrap;}
.stApp div[role="radiogroup"] > label {flex: 1 1 240px; background: #ffffff; border: 3px solid #cfe3c4;
    border-radius: 18px; padding: 18px 20px; min-height: 4.4rem; cursor: pointer;}
.stApp div[role="radiogroup"] > label:has(input:checked) {background: #e5f4dc; border-color: #2e7d32;}
.stApp div[role="radiogroup"] > label p {font-size: 1.4rem !important; font-weight: 800;}
.stApp [data-testid="stExpander"] summary p {font-size: 1.3rem !important; font-weight: 700;}

.hero {background: linear-gradient(135deg, #2e7d32 0%, #6a9f2a 100%); color: #fff;
       border-radius: 22px; padding: 22px 24px; margin-bottom: 14px;}
.hero .h1 {font-size: 2.1rem; font-weight: 900; line-height: 1.2;}
.hero .h2 {font-size: 1.2rem; color: #f1fbe1; margin-top: 6px;}

.card {background: #ffffff; border-radius: 20px; padding: 18px 20px; margin: 10px 0;
       border: 2px solid #e4ead9; box-shadow: 0 2px 6px rgba(60,80,40,.08);}
.sec-title {font-size: 1.6rem; font-weight: 900; color: #2f4a2a; margin: 18px 0 6px 0;}

.wx-now {display: flex; align-items: center; gap: 16px;}
.wx-now .emoji {font-size: 3.4rem;}
.wx-now .temp {font-size: 2.6rem; font-weight: 900; color: #1b4d1f; line-height: 1;}
.wx-now .desc {font-size: 1.25rem; color: #4a5a46;}
.wx-days {display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap;}
.wx-day {flex: 1 1 150px; background: #f4f8ee; border-radius: 14px; padding: 10px 12px; text-align: center;}
.wx-day .d {font-weight: 800; font-size: 1.1rem; color: #2f4a2a;}
.wx-day .t {font-size: 1.05rem; color: #3b4a38;}
.badge {border-radius: 16px; padding: 16px 18px; margin: 10px 0; font-size: 1.35rem; font-weight: 800; line-height: 1.4;}
.badge.frost {background: #fdecea; color: #a31515; border: 3px solid #e57373;}
.badge.rain {background: #e3f1fc; color: #0d47a1; border: 3px solid #64b5f6;}
.badge.ok {background: #e8f5e1; color: #1b5e20; border: 3px solid #81c784;}
.badge.tip {background: #fff6dd; color: #6d4c00; border: 3px solid #ffca28;}
.src {font-size: .95rem; color: #6b7a66; margin-top: 8px;}

.big {border-radius: 22px; padding: 22px 22px; margin: 12px 0; background: #fff; border-left: 14px solid #2e7d32;
      box-shadow: 0 3px 8px rgba(60,80,40,.12);}
.big.water {border-left-color: #1e88e5;}
.big.milk {border-left-color: #c68a3a;}
.big .lbl {font-size: 1.35rem; font-weight: 800; color: #4a5a46;}
.big .num {font-size: 3.2rem; font-weight: 900; line-height: 1.15; color: #1b5e20;}
.big.water .num {color: #0d47a1;}
.big.milk .num {color: #8a5a12;}
.big .sub {font-size: 1.2rem; color: #5b6b57; margin-top: 4px;}

.phone {background: #e5ddd5; border-radius: 20px; padding: 16px; border: 1px solid #cfc7bd;}
.phone .hdr {background: #075e54; color: #fff; padding: 10px 14px; border-radius: 12px; font-size: 1.1rem; font-weight: 700; margin-bottom: 12px;}
.bubble {background: #dcf8c6; color: #111; padding: 16px 18px; border-radius: 14px 0 14px 14px;
         box-shadow: 0 1px 2px rgba(0,0,0,.2); font-size: 1.4rem; line-height: 1.6; margin-left: 24px;}
.bubble .time {display: block; text-align: right; color: #667781; font-size: .95rem; margin-top: 6px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# SABİTLER (SENTETİK BURDUR VERİSİ - AYARLAR MENÜSÜNDEN DEĞİŞTİRİLEBİLİR)
# ----------------------------------------------------------------------------
G = 9.81
MIX_A = {"Silajlık mısır": 0.60, "Yonca": 0.40}
CORN_CUT = 0.40
_freed = MIX_A["Silajlık mısır"] * CORN_CUT
MIX_B = {
    "Silajlık mısır": MIX_A["Silajlık mısır"] * (1 - CORN_CUT),
    "Yonca": MIX_A["Yonca"],
    "Sorgum-sudan otu": _freed * 2 / 3,
    "Fiğ": _freed * 1 / 3,
}
WATER_PER_DA = {"Silajlık mısır": 620.0, "Yonca": 780.0}
FEEDS = {
    "Silajlık mısır": (6.6, 0.080),
    "Yonca": (5.6, 0.180),
    "Sorgum-sudan otu": (5.4, 0.095),
    "Fiğ": (5.5, 0.170),
    "Konsantre yem": (7.4, 0.180),
}
TANKER_TON = 5.0  # 1 traktör tankeri ≈ 5 ton su
TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
BURDUR_LAT, BURDUR_LON = 37.72, 30.29


def fmt(x, nd=0):
    s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ----------------------------------------------------------------------------
# HESAP MOTORU
# ----------------------------------------------------------------------------
def pump_energy_kwh(volume_m3, depth_m, eff):
    return (volume_m3 * depth_m * G) / (3600.0 * eff)


def ration_balance(shares, milk, bw):
    dmi = 0.025 * bw + 0.10 * milk
    forage, conc = dmi * 0.55, dmi * 0.45
    nel = sum(forage * sh * FEEDS[k][0] for k, sh in shares.items()) + conc * FEEDS["Konsantre yem"][0]
    cp = sum(forage * sh * FEEDS[k][1] * 1000 for k, sh in shares.items()) + conc * FEEDS["Konsantre yem"][1] * 1000
    req_nel = 0.335 * bw ** 0.75 + 3.14 * milk
    req_cp = 4.0 * bw ** 0.75 + 80.0 * milk
    need = max(0.0, (req_nel - nel) / FEEDS["Konsantre yem"][0],
               (req_cp - cp) / (FEEDS["Konsantre yem"][1] * 1000))
    nel_f = nel + need * FEEDS["Konsantre yem"][0]
    cp_f = cp + need * FEEDS["Konsantre yem"][1] * 1000
    return {"dmi": dmi, "req_nel": req_nel, "req_cp": req_cp, "extra_conc_kg": need,
            "nel_final": nel_f, "cp_final": cp_f,
            "nel_cov": nel_f / req_nel * 100, "cp_cov": cp_f / req_cp * 100}


def run_engine(p):
    months = p["season_months"]
    season_days = months * 30
    a_per_da = sum(WATER_PER_DA[k] * sh for k, sh in MIX_A.items())
    b_per_da = a_per_da * (1 - p["water_red"] / 100.0)
    water_a, water_b = a_per_da * p["area"], b_per_da * p["area"]
    e_a = pump_energy_kwh(water_a, p["depth"], p["eff"])
    e_b = pump_energy_kwh(water_b, p["depth"], p["eff"])
    price_a = p["price"]
    price_b = p["price"] * (1 - p["night_disc"] / 100.0) if p["night"] else p["price"]
    cost_a, cost_b = e_a * price_a, e_b * price_b
    elec_saving = cost_a - cost_b
    zA, zB = ration_balance(MIX_A, p["milk"], p["bw"]), ration_balance(MIX_B, p["milk"], p["bw"])
    extra_kg = max(0.0, zB["extra_conc_kg"] - zA["extra_conc_kg"])
    extra_feed_cost = extra_kg * p["cows"] * season_days * p["conc_price"]
    milk_change = 0.0 if (zB["nel_cov"] >= 99.99 and zB["cp_cov"] >= 99.99) else \
        -(100 - min(zB["nel_cov"], zB["cp_cov"]))
    night_extra = 0.0 if p["night"] else e_b * p["price"] * p["night_disc"] / 100.0
    return {
        "months": months, "season_days": season_days, "a_per_da": a_per_da, "b_per_da": b_per_da,
        "water_a": water_a, "water_b": water_b, "water_saved": water_a - water_b,
        "e_a": e_a, "e_b": e_b, "kwh_saved": e_a - e_b, "price_a": price_a, "price_b": price_b,
        "cost_a": cost_a, "cost_b": cost_b, "elec_saving": elec_saving,
        "elec_pct": elec_saving / cost_a * 100 if cost_a else 0.0,
        "zA": zA, "zB": zB, "extra_feed_cost": extra_feed_cost,
        "net_benefit": elec_saving - extra_feed_cost, "milk_change": milk_change,
        "milk_day": p["cows"] * p["milk"], "night_extra": night_extra,
        "round_cost": cost_b / max(1, p["rounds"]),
    }


# ----------------------------------------------------------------------------
# HAVA DURUMU (CANLI: Open-Meteo, anahtar gerektirmez; olmazsa ÖRNEK VERİ)
# ----------------------------------------------------------------------------
WMO = {0: ("☀️", "Açık"), 1: ("🌤️", "Az bulutlu"), 2: ("⛅", "Parçalı bulutlu"), 3: ("☁️", "Kapalı"),
       45: ("🌫️", "Sisli"), 48: ("🌫️", "Kırağılı sis"), 51: ("🌦️", "Çiseleme"), 53: ("🌦️", "Çiseleme"),
       55: ("🌦️", "Çiseleme"), 61: ("🌧️", "Yağmurlu"), 63: ("🌧️", "Yağmurlu"), 65: ("🌧️", "Kuvvetli yağmur"),
       71: ("🌨️", "Karlı"), 73: ("🌨️", "Karlı"), 75: ("🌨️", "Yoğun kar"), 80: ("🌦️", "Sağanak"),
       81: ("🌧️", "Sağanak"), 82: ("⛈️", "Kuvvetli sağanak"), 95: ("⛈️", "Gök gürültülü fırtına"),
       96: ("⛈️", "Dolu riski"), 99: ("⛈️", "Dolu riski")}


def wmo(code):
    return WMO.get(int(code or 0), ("⛅", "Parçalı bulutlu"))


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather_raw():
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&current=temperature_2m,weather_code"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max"
           "&timezone=Europe%%2FIstanbul&forecast_days=4") % (BURDUR_LAT, BURDUR_LON)
    with urllib.request.urlopen(url, timeout=6) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_weather():
    try:
        d = fetch_weather_raw()
        daily = d["daily"]
        days = []
        for i, dt in enumerate(daily["time"]):
            days.append({
                "date": dt, "code": daily["weather_code"][i],
                "tmax": float(daily["temperature_2m_max"][i]),
                "tmin": float(daily["temperature_2m_min"][i]),
                "rain_mm": float(daily["precipitation_sum"][i] or 0),
                "rain_prob": float(daily["precipitation_probability_max"][i] or 0),
            })
        return {"live": True, "temp": float(d["current"]["temperature_2m"]),
                "code": d["current"]["weather_code"], "days": days}
    except Exception:
        today = datetime.date.today()
        sample = [(7, 18, 0, 5, 2), (5, 17, 6, 70, 61), (0.5, 15, 0, 10, 1), (3, 16, 0, 5, 2)]
        days = []
        for i, (tmin, tmax, mm, prob, code) in enumerate(sample):
            days.append({"date": (today + datetime.timedelta(days=i)).isoformat(), "code": code,
                         "tmax": float(tmax), "tmin": float(tmin), "rain_mm": float(mm), "rain_prob": float(prob)})
        return {"live": False, "temp": 16.0, "code": 2, "days": days}


def day_name(date_str):
    return TR_DAYS[datetime.date.fromisoformat(date_str).weekday()]


def day_label(i, date_str):
    return "Bugün" if i == 0 else ("Yarın" if i == 1 else day_name(date_str))


def build_warnings(w, round_cost):
    out = []
    for i, d in enumerate(w["days"][:3]):
        if d["tmin"] <= 2.0:
            when = "Bu gece" if i == 0 else ("Yarın gece" if i == 1 else f"{day_name(d['date'])} gecesi")
            out.append({"kind": "frost",
                        "text": f"⚠️ DİKKAT: {when} don riski var (en düşük {d['tmin']:.0f}°C), sulama yapmayın!",
                        "short": f"{when} don riski var, suyu çalıştırma."})
            break
    for i, d in enumerate(w["days"][:2]):
        if d["rain_mm"] >= 2 or d["rain_prob"] >= 60:
            when = "BUGÜN" if i == 0 else "YARIN"
            out.append({"kind": "rain",
                        "text": f"🌧️ {when} YAĞMUR BEKLENİYOR: Kuyuyu çalıştırmayın, yaklaşık "
                                f"{fmt(round_cost)} TL elektrik cebinizde kalsın.",
                        "short": f"{when.capitalize()} yağmur var, motoru şimdilik çalıştırma."})
            break
    return out


def weather_html(w, warnings, p, r):
    emo, desc = wmo(w["code"])
    days_html = ""
    for i, d in enumerate(w["days"][:3]):
        e, _ = wmo(d["code"])
        days_html += (f'<div class="wx-day"><div class="d">{day_label(i, d["date"])}</div>'
                      f'<div class="t">{e} {d["tmin"]:.0f}° / {d["tmax"]:.0f}°</div>'
                      f'<div class="t">Yağış: {d["rain_mm"]:.0f} mm</div></div>')
    badges = ""
    for wr in warnings:
        badges += f'<div class="badge {wr["kind"]}">{html.escape(wr["text"])}</div>'
    if not warnings:
        badges = ('<div class="badge ok">✅ Önümüzdeki günlerde don ya da yağmur uyarısı yok. '
                  'Sulamaya devam edebilirsiniz.</div>')
    tip = (f'<div class="badge tip">🌙 Sulama saati önerisi: Bu gece 22:00 - 06:00 arası elektrik '
           f'%{int(p["night_disc"])} indirimli, sulamaya bu saatte başlayın.')
    if not p["night"] and r["night_extra"] > 0:
        tip += f' Geceye alırsanız sezonda yaklaşık {fmt(r["night_extra"])} TL daha kazanırsınız.'
    tip += "</div>"
    src = ("Canlı veri: Open-Meteo, 30 dakikada bir yenilenir." if w["live"]
           else "İnternet bağlantısı kurulamadı, ÖRNEK veri gösteriliyor.")
    return (f'<div class="card"><div class="sec-title" style="margin-top:0">🌦️ Burdur Hava Durumu ve Tarla Uyarıları</div>'
            f'<div class="wx-now"><div class="emoji">{emo}</div><div><div class="temp">{w["temp"]:.0f}°C</div>'
            f'<div class="desc">Burdur Merkez · {desc}</div></div></div>'
            f'<div class="wx-days">{days_html}</div>{badges}{tip}<div class="src">{src}</div></div>')


# ----------------------------------------------------------------------------
# YAPAY ZEKÂ (GEMINI) VE YEDEK ŞABLON
# ----------------------------------------------------------------------------
SYSTEM_ROLE = (
    "Sen Burdur'da köy kahvesinde çiftçilerle sohbet eden, samimi ve güvenilir bir ziraat mühendisisin. "
    "Çiftçiyi asla suçlamaz, emeğini ve kazancını korursun. Kısa, sade, günlük konuşma diliyle, "
    "teknik terim kullanmadan, doğrudan eyleme dönüştürülebilir tavsiye verirsin. Kararın çiftçide kaldığını hissettirirsin."
)


def build_prompt(p, r, ad, wlines):
    rejim = "gece (indirimli) sulama" if p["night"] else "gündüz sulama"
    hava = "\n".join(f"- {x}" for x in wlines) if wlines else "- Don ya da yağmur uyarısı yok."
    return f"""Aşağıdaki hesaplanmış sonuçlara göre iki çıktı üret. Rakamları değiştirme, uydurma.

Çiftçi: {ad}. {p['cows']} sağmal inek, günlük inek başı {p['milk']} L süt, {p['area']} dönüm tarla, kuyu/pompa derinliği {p['depth']} m, {rejim}.
Sonuçlar (mısırın %40'ı yerine sorgum-sudan otu ve fiğ ekilirse):
- Sezonluk fatura kazancı: {fmt(r['elec_saving'])} TL
- Sezonluk kurtarılan su: {fmt(r['water_saved'])} ton (yaklaşık {fmt(r['water_saved'] / TANKER_TON)} traktör tankeri)
- Süt verimi: kayıp yok, günlük {fmt(r['milk_day'])} litre aynen devam
Hava uyarıları:
{hava}

Çıktı formatı (başlıkları aynen kullan):
[SMS]
{ad} diye hitap eden, 3-4 kısa cümlelik WhatsApp mesajı. Varsa hava uyarısını da söyle. En fazla 1-2 emoji.
[TEKNIK]
Kooperatif mühendisi için 1 paragraflık teknik karar notu (su, enerji, rasyon dengesi, riskler)."""


def mock_advice(p, r, ad, warnings):
    msg = (f"{ad} selam! {p['cows']} ineğin için bu sezon {p['area']} dönümde mısırın %40'ı yerine sorgum-fiğ "
           f"karışımı ekersen, ineklerinin sütü hiç düşmez. Kuyunun faturası tam {fmt(r['elec_saving'])} TL daha az gelir.")
    for wr in warnings:
        msg += " " + wr["short"]
    rejim = "gece indirimli tarife" if p["night"] else "standart gündüz tarifesi"
    note = (f"{p['cows']} sağmal inek ve {p['area']} dönüm için modelde silajlık mısır payı %40 azaltılıp sorgum-sudan otu "
            f"ve fiğe kaydırıldığında dönüm başı sulama suyu {fmt(r['a_per_da'])} m³'ten {fmt(r['b_per_da'])} m³'e düşmektedir. "
            f"{p['depth']} m derinlik ve %{int(p['eff'] * 100)} pompa verimiyle sezonluk pompa enerjisi {fmt(r['e_a'])} kWh'ten "
            f"{fmt(r['e_b'])} kWh'e inmekte ({rejim}) ve elektrik gideri %{fmt(r['elec_pct'], 1)} azalmaktadır. Enerji ve protein "
            f"ihtiyacı konsantre yem dengelemesiyle tam karşılanmakta, ek yem maliyeti sezonluk {fmt(r['extra_feed_cost'])} TL, "
            f"net kazanç {fmt(r['net_benefit'])} TL'dir. Sorgum-sudan otu verimi ve fiğ ekim zamanı pilot parselde doğrulanmalıdır.")
    return msg, note


def gemini_advice(api_key, model_name, p, r, ad, wlines):
    genai.configure(api_key=api_key)
    try:
        fallback = str(st.secrets.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")).strip()
    except Exception:
        fallback = "gemini-3.5-flash-lite"
    candidates = [model_name] + ([fallback] if fallback and fallback != model_name else [])
    resp, last_err = None, None
    for name in candidates:
        try:
            model = genai.GenerativeModel(name, system_instruction=SYSTEM_ROLE)
            resp = model.generate_content(build_prompt(p, r, ad, wlines))
            break
        except Exception as exc:
            last_err = exc
    if resp is None:
        raise last_err
    text = (resp.text or "").strip()
    m_sms = re.search(r"\[SMS\](.*?)(\[TEKNIK\]|$)", text, re.S)
    m_tek = re.search(r"\[TEKNIK\](.*)$", text, re.S)
    if not m_sms or not m_tek:
        raise ValueError("Model çıktısı beklenen formatta değil.")
    return m_sms.group(1).strip(), m_tek.group(1).strip()


def build_report(p, r, ad, msg, note, source, warnings):
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    rejim = "Gece (indirimli)" if p["night"] else "Gündüz"
    hava = "\n".join(f"- {w['text']}" for w in warnings) or "- Don ya da yağmur uyarısı yok."
    return f"""AGRO-DAIRY AI | KARAR RAPORU
Burdur Havzası Su, Enerji ve Rasyon Karar Destek Platformu
Tarih: {now}  |  Metin kaynağı: {source}
{'=' * 64}

ÇİFTÇİ: {ad}
Sağmal inek: {p['cows']} | Günlük süt: {p['milk']} L/inek | Tarla: {p['area']} dönüm
Pompa derinliği: {p['depth']} m | Sulama zamanı: {rejim}

SONUÇLAR (sezonluk)
- Faturadan kazanç: {fmt(r['elec_saving'])} TL (%{fmt(r['elec_pct'], 1)}); ek yem maliyeti {fmt(r['extra_feed_cost'])} TL; net {fmt(r['net_benefit'])} TL
- Kurtarılan su: {fmt(r['water_saved'])} ton (≈ {fmt(r['water_saved'] / TANKER_TON)} traktör tankeri)
- Kurtarılan elektrik: {fmt(r['kwh_saved'])} kWh
- Su: {fmt(r['water_a'])} m³ -> {fmt(r['water_b'])} m³ | Elektrik: {fmt(r['cost_a'])} TL -> {fmt(r['cost_b'])} TL
- Süt verimi: kayıp yok, günlük {fmt(r['milk_day'])} L

HAVA UYARILARI
{hava}

ÇİFTÇİ MESAJI
{msg}

TEKNİK KARAR NOTU
{note}

Not: Sonuçlar sentetik veriler ve varsayımlarla üretilmiş karar destek çıktısıdır.
Nihai ekim ve sulama kararı çiftçiye aittir.
"""


def copy_button(text):
    safe = json.dumps(text).replace("</", "<\\/")
    page = """
<button id="b" onclick="cp()" style="width:100%;height:70px;font-size:22px;font-weight:800;border:0;
border-radius:18px;background:#2e7d32;color:#fff;cursor:pointer;font-family:sans-serif;">📋 Mesajı Kopyala</button>
<script>
const t = __TEXT__;
function done(){const b=document.getElementById('b');b.innerText='✅ Kopyalandı!';
  setTimeout(function(){b.innerText='📋 Mesajı Kopyala';},2000);}
function fb(){const a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();
  try{document.execCommand('copy');done();}catch(e){}document.body.removeChild(a);}
function cp(){if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(done).catch(fb);}else{fb();}}
</script>"""
    components.html(page.replace("__TEXT__", safe), height=80)


# ----------------------------------------------------------------------------
# AYARLAR MENÜSÜ (kooperatif/yetkili için; çiftçinin görmesi gerekmez)
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ayarlar")
    with st.expander("Hesap varsayımları"):
        price = st.number_input("Tarımsal elektrik fiyatı (TL/kWh)", 0.5, 20.0, 4.5, 0.1)
        night_disc = st.slider("Gece tarifesi indirimi (%)", 0, 50, 20)
        eff = st.slider("Pompa verimi", 0.40, 0.85, 0.65, 0.01)
        water_red = st.slider("Alternatif karışımla su azalışı (%)", 20, 45, 35)
        season_months = st.slider("Sulama sezonu (ay)", 3, 8, 5)
        rounds = st.slider("Sezonda sulama turu sayısı", 5, 40, 15)
        bw = st.number_input("İnek canlı ağırlığı (kg)", 450, 750, 600, 10)
        conc_price = st.number_input("Kesif yem fiyatı (TL/kg)", 5.0, 40.0, 13.0, 0.5)

    try:
        SERVER_KEY = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
        SERVER_MODEL = str(st.secrets.get("GEMINI_MODEL", "gemini-3.8-flash")).strip()
    except Exception:
        SERVER_KEY, SERVER_MODEL = "", "gemini-3.8-flash"

    if SERVER_KEY:
        api_key, model_name = SERVER_KEY, SERVER_MODEL
        st.caption("🤖 Yapay zekâ modu aktif (Gemini).")
    else:
        with st.expander("🤖 Gemini ayarı"):
            api_key = st.text_input("Gemini API Key", type="password",
                                    help="Boş bırakılırsa hazır şablon mesaj kullanılır.")
            model_name = st.text_input("Model adı", value="gemini-3.8-flash")
            if not GENAI_OK:
                st.caption("google-generativeai kurulu değil; hazır şablon kullanılacak.")

MAX_AI_CALLS = 5

# ----------------------------------------------------------------------------
# ORTAK YARDIMCILAR: KÖY SEÇİMİ, GİRİŞLER, PARAMETRELER, GEMINI
# ----------------------------------------------------------------------------
st.markdown(
    """<style>
.big.power {border-left-color: #f9a825;}
.big.power .num {color: #8a6100;}
.big.co2 {border-left-color: #6d4c41;}
.big.co2 .num {color: #5d4037;}
.report {background: #fffdf5; border: 2px solid #e4dcc0; border-radius: 16px; padding: 18px 20px;
         font-size: 1.15rem; line-height: 1.65; color: #2b2b2b;}
</style>""",
    unsafe_allow_html=True,
)

VILLAGE_DEPTHS = {
    "Kocapınar (Ortalama 160 m)": 160,
    "Burdur Merkez / Çendik (Ortalama 150 m)": 150,
    "Kozluca (Ortalama 180 m)": 180,
    "Büğdüz (Ortalama 170 m)": 170,
    "Karakent / Yeşilova Çevresi (Ortalama 140 m)": 140,
    "Diğer / Havza Geneli (Ortalama 180 m)": 180,
}
POOL_M3 = 2500.0       # olimpik havuz ≈ 2.500 m³
CO2_KG_PER_KWH = 0.44  # kg CO2e / kWh
NIGHT_HOURS = {22, 23, 0, 1, 2, 3, 4, 5}


def farm_inputs(prefix, coop):
    """Çiftlik girdileri. coop=True ise tipik çiftlik için nötr dille sorar."""
    ad = "Ali Dayı"
    if not coop:
        ad = st.text_input("Sana nasıl hitap edelim?", value="Ali Dayı", key=f"{prefix}_ad")
    c1, c2 = st.columns(2)
    with c1:
        cows = st.number_input("Sağmal İnek Sayın Kaç?" if not coop else "Tipik çiftlikte sağmal inek sayısı",
                               min_value=5, max_value=200, value=30, step=1, key=f"{prefix}_cows")
    with c2:
        area = st.number_input("Kaba Yem / Mısır Ektiğin Tarla Kaç Dönüm?" if not coop
                               else "Tipik çiftlikte kaba yem alanı (dönüm)",
                               min_value=1, max_value=2000, value=20, step=1, key=f"{prefix}_area")
    milk = st.number_input("Bir inek günde ortalama kaç litre süt veriyor?" if not coop
                           else "İnek başı günlük süt verimi (litre)",
                           min_value=10.0, max_value=45.0, value=24.0, step=1.0, key=f"{prefix}_milk")
    village = st.selectbox("Bulunduğunuz Köy / Bölge", options=list(VILLAGE_DEPTHS.keys()),
                           index=len(VILLAGE_DEPTHS) - 1, key=f"{prefix}_village")
    depth = VILLAGE_DEPTHS[village]
    manual = st.checkbox("Kuyu derinliğimi tam biliyorum (Manuel gir)", key=f"{prefix}_manual")
    if manual:
        depth = st.number_input("Kuyunun Boru / Pompa Derinliği Kaç Metre?", min_value=50, max_value=250,
                                value=int(depth), step=5, key=f"{prefix}_depth")
        st.caption("✍️ Kendi girdiğiniz kuyu derinliği hesapta kullanılıyor.")
    else:
        st.caption(f"💡 Seçilen bölgeye göre tahmini kuyu derinliği otomatik ayarlandı ({depth} m).")
    timing = None
    if not coop:
        timing = st.radio("Sulama Zamanı", ["☀️ Gündüz Suluyorum", "🌙 Gece Suluyorum (İndirimli)"],
                          horizontal=True, key=f"{prefix}_timing")
    return {"ad": ad, "cows": cows, "area": area, "milk": milk, "depth": depth, "village": village,
            "night": bool(timing and timing.startswith("🌙"))}


def make_params(fi, night):
    return {
        "cows": int(fi["cows"]), "milk": float(fi["milk"]), "area": int(fi["area"]), "depth": int(fi["depth"]),
        "night": night, "price": float(price), "night_disc": float(night_disc), "eff": float(eff),
        "water_red": float(water_red), "season_months": int(season_months), "bw": float(bw),
        "conc_price": float(conc_price), "rounds": int(rounds),
    }


def gemini_text(system_role, prompt):
    """Genel amaçlı Gemini çağrısı (ana model, olmazsa yedek model)."""
    genai.configure(api_key=api_key)
    try:
        fallback = str(st.secrets.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")).strip()
    except Exception:
        fallback = "gemini-3.5-flash-lite"
    candidates = [model_name] + ([fallback] if fallback and fallback != model_name else [])
    last_err = None
    for name in candidates:
        try:
            model = genai.GenerativeModel(name, system_instruction=system_role)
            return (model.generate_content(prompt).text or "").strip(), name
        except Exception as exc:
            last_err = exc
    raise last_err


def can_use_ai():
    return bool(api_key) and GENAI_OK


# ----------------------------------------------------------------------------
# 👨‍🌾 ÇİFTÇİ GÖRÜNÜMÜ
# ----------------------------------------------------------------------------
def farmer_view():
    weather_slot = st.container()
    st.markdown('<div class="sec-title">📝 Çiftliğini Anlat</div>', unsafe_allow_html=True)
    fi = farm_inputs("f", coop=False)
    ad = fi["ad"]
    params = make_params(fi, fi["night"])
    res = run_engine(params)
    weather = get_weather()
    warnings = build_warnings(weather, res["round_cost"])
    wlines = [w["text"] for w in warnings]

    with weather_slot:
        st.markdown(weather_html(weather, warnings, params, res), unsafe_allow_html=True)

    st.markdown('<div class="sec-title">📊 Senin İçin Hesapladık</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="big"><div class="lbl">💰 Fatura Tasarrufun</div>'
        f'<div class="num">{fmt(res["elec_saving"])} TL</div>'
        f'<div class="sub">Cebinde Kalacak (sezonluk, kuyu elektriği %{fmt(res["elec_pct"])} azalıyor). '
        f'Ek yem gideri düşülürse net: {fmt(res["net_benefit"])} TL</div></div>',
        unsafe_allow_html=True)
    st.markdown(
        f'<div class="big water"><div class="lbl">💧 Kurtarılan Yeraltı Suyu</div>'
        f'<div class="num">{fmt(res["water_saved"])} Ton Su</div>'
        f'<div class="sub">Yaklaşık {fmt(res["water_saved"] / TANKER_TON)} traktör tankeri su yerinde kalıyor</div></div>',
        unsafe_allow_html=True)
    if res["milk_change"] == 0:
        st.markdown(
            f'<div class="big milk"><div class="lbl">🥛 Süt Verimi</div><div class="num">%0 Kayıp</div>'
            f'<div class="sub">{fmt(params["milk"])} L/inek/gün korunuyor (toplam {fmt(res["milk_day"])} L/gün)</div></div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="big milk"><div class="lbl">🥛 Süt Verimi</div>'
            f'<div class="num">%{fmt(abs(res["milk_change"]), 1)} düşebilir</div>'
            f'<div class="sub">Kooperatif mühendisiyle yem planını gözden geçirin</div></div>',
            unsafe_allow_html=True)
    st.caption("Rakamlar örnek Burdur verileriyle hesaplanmış tahmindir. Ekim ve sulama kararı her zaman sizdedir.")

    sig = hashlib.md5((repr(sorted(params.items())) + ad + model_name + str(bool(api_key)) + "|".join(wlines)).encode()).hexdigest()
    mock_msg, mock_note = mock_advice(params, res, ad, warnings)
    st.session_state.setdefault("advice", None)

    st.markdown('<div class="sec-title">💬 Sana Özel WhatsApp Mesajı</div>', unsafe_allow_html=True)
    if st.button("✨ Mesajı Yapay Zekâ ile Yaz", type="primary", key="f_ai"):
        calls = st.session_state.get("ai_calls", 0)
        if can_use_ai() and calls >= MAX_AI_CALLS:
            st.info("Bu oturumdaki yapay zekâ hakkı doldu. Hazır şablon mesaj gösteriliyor.")
            st.session_state["advice"] = (sig, mock_msg, mock_note, "Hazır şablon")
        elif can_use_ai():
            st.session_state["ai_calls"] = calls + 1
            try:
                with st.spinner("Ziraat mühendisi mesajı yazıyor..."):
                    g_msg, g_note = gemini_advice(api_key, model_name, params, res, ad, wlines)
                st.session_state["advice"] = (sig, g_msg, g_note, f"Gemini ({model_name})")
            except Exception as exc:
                st.warning(f"Yapay zekâya şu an ulaşılamadı, hazır şablon kullanılıyor. Ayrıntı: {exc}")
                st.session_state["advice"] = (sig, mock_msg, mock_note, "Hazır şablon")
        else:
            st.info("Yapay zekâ anahtarı olmadığı için hazır şablon mesaj gösteriliyor.")
            st.session_state["advice"] = (sig, mock_msg, mock_note, "Hazır şablon")

    adv = st.session_state["advice"]
    if adv and adv[0] == sig:
        _, msg_text, tech_note, source = adv
    else:
        msg_text, tech_note, source = mock_msg, mock_note, "Hazır şablon"

    now_t = datetime.datetime.now().strftime("%H:%M")
    st.markdown(
        f'<div class="phone"><div class="hdr">💬 Burdur Sulama Kooperatifi</div>'
        f'<div class="bubble">{html.escape(msg_text)}<span class="time">{now_t} ✓✓</span></div></div>',
        unsafe_allow_html=True)
    st.write("")
    b1, b2 = st.columns(2)
    with b1:
        copy_button(msg_text)
    with b2:
        st.link_button("🟢 WhatsApp ile Paylaş", "https://wa.me/?text=" + urllib.parse.quote(msg_text),
                       use_container_width=True)

    st.write("")
    report = build_report(params, res, ad, msg_text, tech_note, source, warnings)
    st.download_button("📄 Raporu İndir (.txt)", data=report.encode("utf-8"),
                       file_name="agro_dairy_karar_raporu.txt", mime="text/plain", key="f_dl")
    st.caption("Bölgesel etkiyi görmek için sayfanın en üstünden Kooperatif / Birlik Paneli'ni seçin.")


# ----------------------------------------------------------------------------
# 🏢 KOOPERATİF / BİRLİK PANELİ (BÖLGESEL ETKİ)
# ----------------------------------------------------------------------------
def hourly_profile(e_round, n_farms, night_share):
    out = []
    for h in range(24):
        if h in NIGHT_HOURS:
            out.append(e_round * n_farms * night_share / 8.0)
        else:
            out.append(e_round * n_farms * (1 - night_share) / 16.0)
    return out


def coop_mock_report(fi, res, n, share, t):
    return (
        f"Burdur Havzası'nda sistemi kullanan {fmt(n)} çiftlik için yapılan değerlendirmede, silajlık mısır payının %40 "
        f"azaltılıp sorgum-sudan otu ve fiğe kaydırılması halinde sezonluk yeraltı suyu çekiminin yaklaşık "
        f"{fmt(t['water'])} m³ ({fmt(t['pools'], 1)} olimpik havuz eşdeğeri) azalacağı öngörülmektedir. Pompa elektriği "
        f"{fmt(t['kwh'])} kWh düşmekte, çiftliklerin %{fmt(share * 100)}'inin gece (22:00-06:00) sulamasına geçmesiyle birlikte "
        f"toplam elektrik gideri {fmt(t['tl'])} TL azalmaktadır. Bu, yaklaşık {fmt(t['co2'], 1)} tCO2e salım azalımına karşılık gelir. "
        f"Rasyon dengesi sayesinde inek başı süt veriminde kayıp öngörülmemekte, ek konsantre yem maliyeti toplam "
        f"{fmt(t['feed'])} TL olarak hesaplanmıştır. Gündüz pik pompa yükü {fmt(t['peak_cur'])} kW'tan {fmt(t['peak_opt'])} kW'a "
        f"inmektedir. Sonuçlar sentetik veriler ve varsayımlara dayanmaktadır; pilot uygulamada fatura ve sayaç verisiyle "
        f"doğrulanması ve nihai ekim kararının üreticiye bırakılması önerilir."
    )


def coop_view():
    st.markdown('<div class="sec-title">📝 Tipik Çiftlik ve Bölge Bilgisi</div>', unsafe_allow_html=True)
    fi = farm_inputs("c", coop=True)
    n = int(st.number_input("Bu Köyde / Havzada Sistemi Kullanan Çiftlik Sayısı", min_value=1, max_value=5000,
                            value=50, step=1, key="c_n"))
    share = st.slider("Gece (22:00-06:00) sulamasına geçen çiftlik oranı (%)", 0, 100, 70, key="c_share") / 100.0

    params = make_params(fi, False)
    res = run_engine(params)

    # çiftlik başı karma tarifeyle maliyet, sonra çiftlik sayısıyla çarpım
    cost_b_farm = res["e_b"] * price * (1 - night_disc / 100.0 * share)
    saving_farm = res["cost_a"] - cost_b_farm
    e_round_a, e_round_b = res["e_a"] / max(1, rounds), res["e_b"] / max(1, rounds)
    cur = hourly_profile(e_round_a, n, 0.10)
    opt = hourly_profile(e_round_b, n, share)
    day_idx = [h for h in range(24) if h not in NIGHT_HOURS]
    peak_cur, peak_opt = max(cur[h] for h in day_idx), max(opt[h] for h in day_idx)
    kwh_tot = res["kwh_saved"] * n
    t = {
        "water": res["water_saved"] * n, "kwh": kwh_tot, "tl": saving_farm * n,
        "co2": kwh_tot * CO2_KG_PER_KWH / 1000.0, "feed": res["extra_feed_cost"] * n,
        "pools": res["water_saved"] * n / POOL_M3, "peak_cur": peak_cur, "peak_opt": peak_opt,
    }

    st.markdown(f'<div class="sec-title">🌍 {fmt(n)} Çiftliğin Toplam Bölgesel Etkisi (sezonluk)</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div class="big water"><div class="lbl">💧 Toplam Korunan Akifer Suyu</div>'
        f'<div class="num">{fmt(t["water"])} m³</div>'
        f'<div class="sub">≈ {fmt(t["pools"], 1)} olimpik havuz ≈ {fmt(t["water"] / TANKER_TON)} traktör tankeri</div></div>',
        unsafe_allow_html=True)
    st.markdown(
        f'<div class="big power"><div class="lbl">⚡ Şebekeden Silinen Toplam Elektrik Faturası</div>'
        f'<div class="num">{fmt(t["tl"])} TL</div>'
        f'<div class="sub">{fmt(t["kwh"])} kWh daha az elektrik (net: ek yem düşülünce {fmt(t["tl"] - t["feed"])} TL)</div></div>',
        unsafe_allow_html=True)
    st.markdown(
        f'<div class="big co2"><div class="lbl">🌱 Tahmini Karbon Azalımı</div>'
        f'<div class="num">{fmt(t["co2"], 1)} tCO2e</div>'
        f'<div class="sub">Kurtarılan elektrik × {CO2_KG_PER_KWH} kg CO2e/kWh / 1000</div></div>',
        unsafe_allow_html=True)
    st.caption(f"Süt verimi: tipik çiftlikte {fmt(params['milk'])} L/inek/gün korunuyor "
               f"(toplam {fmt(res['milk_day'] * n)} L/gün, %0 kayıp). Rakamlar sentetik veri ve varsayımlarla hesaplanmıştır.")

    st.markdown('<div class="sec-title">📈 Grafikler</div>', unsafe_allow_html=True)
    labels = ["Mevcut Durum", "Agro-Dairy AI"]
    fig_w = go.Figure(go.Bar(x=labels, y=[res["water_a"] * n, res["water_b"] * n],
                             marker_color=["#b45309", "#2e7d32"],
                             text=[f"{fmt(res['water_a'] * n)} m³", f"{fmt(res['water_b'] * n)} m³"],
                             textposition="outside"))
    fig_w.update_layout(title="Sezonluk Toplam Su Tüketimi (m³)", yaxis_title="m³", height=420,
                        margin=dict(t=60, b=20), showlegend=False, font=dict(size=16),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_w, use_container_width=True)

    hours = [f"{h:02d}:00" for h in range(24)]
    fig_h = go.Figure()
    fig_h.add_trace(go.Bar(x=hours, y=cur, name="Mevcut Durum", marker_color="#b45309"))
    fig_h.add_trace(go.Bar(x=hours, y=opt, name="Agro-Dairy AI (gece kaydırmalı)", marker_color="#2e7d32"))
    fig_h.update_layout(title="Sulama Gününde Saatlik Pompa Yükü (kW) - Trafo Yükü", barmode="group",
                        yaxis_title="kW (ortalama)", height=460, margin=dict(t=60, b=20),
                        legend=dict(orientation="h", y=-0.2), font=dict(size=15),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_h, use_container_width=True)
    red = (1 - peak_opt / peak_cur) * 100 if peak_cur else 0.0
    m1, m2, m3 = st.columns(3)
    m1.metric("Gündüz pik yük (şimdi)", f"{fmt(peak_cur)} kW")
    m2.metric("Gündüz pik yük (öneri)", f"{fmt(peak_opt)} kW")
    m3.metric("Gündüz yükü azalışı", f"%{fmt(red)}")
    st.caption("Saatlik yük modeli: sulama gününde tüm çiftliklerin bir sulama turunu aynı gün yaptığı varsayılır; "
               "mevcut durumda çiftliklerin %10'u, öneride seçtiğiniz oranı gece sular. Sentetik bir senaryodur.")

    st.markdown('<div class="sec-title">🏛️ Kooperatif Teknik Karar Özeti</div>', unsafe_allow_html=True)
    sig = hashlib.md5((repr(sorted(params.items())) + str(n) + str(share) + model_name + str(bool(api_key))).encode()).hexdigest()
    mock_text = coop_mock_report(fi, res, n, share, t)
    st.session_state.setdefault("coop_advice", None)
    if st.button("✨ Resmi Raporu Yapay Zekâ ile Yaz", type="primary", key="c_ai"):
        calls = st.session_state.get("ai_calls", 0)
        if can_use_ai() and calls >= MAX_AI_CALLS:
            st.info("Bu oturumdaki yapay zekâ hakkı doldu. Kural tabanlı rapor gösteriliyor.")
            st.session_state["coop_advice"] = (sig, mock_text, "Kural tabanlı şablon")
        elif can_use_ai():
            st.session_state["ai_calls"] = calls + 1
            prompt = (
                "Aşağıdaki hesaplanmış bölgesel sonuçlara göre kooperatif yönetim kurulu için TEK PARAGRAFLIK resmi bir "
                "'Teknik Karar Özeti' yaz. Rakamları aynen kullan, uydurma. Varsayımları ve doğrulama ihtiyacını belirt. "
                "Nihai ekim kararının üreticide kaldığını vurgula.\n"
                f"- Sistemi kullanan çiftlik sayısı: {fmt(n)}; tipik çiftlik: {params['cows']} inek, {params['area']} dönüm, "
                f"{params['depth']} m derinlik\n"
                f"- Sezonluk korunan su: {fmt(t['water'])} m³ ({fmt(t['pools'], 1)} olimpik havuz)\n"
                f"- Azalan elektrik: {fmt(t['kwh'])} kWh; fatura azalışı: {fmt(t['tl'])} TL; ek yem maliyeti: {fmt(t['feed'])} TL\n"
                f"- Karbon azalımı: {fmt(t['co2'], 1)} tCO2e (0,44 kg CO2e/kWh)\n"
                f"- Gece sulamasına geçen çiftlik oranı: %{fmt(share * 100)}; gündüz pik yük {fmt(peak_cur)} kW -> {fmt(peak_opt)} kW\n"
                "- Süt verimi kaybı: %0 (rasyon dengesi modeli)")
            try:
                with st.spinner("Rapor hazırlanıyor..."):
                    text, used = gemini_text(
                        "Sen Burdur Damızlık Sığır Yetiştiricileri Birliği ve Sulama Kooperatifi uzmanısın. "
                        "Resmi, net, sayısal ve dürüst bir kurum diliyle yazarsın.", prompt)
                st.session_state["coop_advice"] = (sig, text, f"Gemini ({used})")
            except Exception as exc:
                st.warning(f"Yapay zekâya şu an ulaşılamadı, kural tabanlı rapor kullanılıyor. Ayrıntı: {exc}")
                st.session_state["coop_advice"] = (sig, mock_text, "Kural tabanlı şablon")
        else:
            st.info("Yapay zekâ anahtarı olmadığı için kural tabanlı rapor gösteriliyor.")
            st.session_state["coop_advice"] = (sig, mock_text, "Kural tabanlı şablon")

    cadv = st.session_state["coop_advice"]
    if cadv and cadv[0] == sig:
        _, report_text, rsource = cadv
    else:
        report_text, rsource = mock_text, "Kural tabanlı şablon"
    st.markdown(f'<div class="report">{html.escape(report_text)}</div>', unsafe_allow_html=True)
    st.caption(f"Metin kaynağı: {rsource}")

    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    full = (f"AGRO-DAIRY AI | KOOPERATİF BÖLGESEL ETKİ RAPORU\nTarih: {now} | Kaynak: {rsource}\n{'=' * 60}\n\n"
            f"Çiftlik sayısı: {fmt(n)} | Gece sulama oranı: %{fmt(share * 100)}\n"
            f"Tipik çiftlik: {params['cows']} inek, {params['area']} dönüm, {params['depth']} m, {fmt(params['milk'])} L/inek/gün\n\n"
            f"Korunan su: {fmt(t['water'])} m³ ({fmt(t['pools'], 1)} havuz, {fmt(t['water'] / TANKER_TON)} tanker)\n"
            f"Azalan elektrik: {fmt(t['kwh'])} kWh | Fatura azalışı: {fmt(t['tl'])} TL | Ek yem: {fmt(t['feed'])} TL\n"
            f"Karbon azalımı: {fmt(t['co2'], 1)} tCO2e\n"
            f"Gündüz pik yük: {fmt(peak_cur)} kW -> {fmt(peak_opt)} kW\n\n"
            f"TEKNİK KARAR ÖZETİ\n{report_text}\n\n"
            "Not: Sonuçlar sentetik veri ve varsayımlarla üretilmiş karar destek çıktısıdır.\n")
    st.write("")
    st.download_button("📄 Kooperatif Raporunu İndir (.txt)", data=full.encode("utf-8"),
                       file_name="agro_dairy_kooperatif_raporu.txt", mime="text/plain", key="c_dl")

    with st.expander("🔧 Tipik çiftlik hesap ayrıntıları"):
        st.dataframe(pd.DataFrame({
            "Gösterge": ["Su (m³/sezon)", "Pompa elektriği (kWh/sezon)", "Elektrik faturası (TL/sezon)"],
            "Mevcut Durum": [fmt(res["water_a"]), fmt(res["e_a"]), fmt(res["cost_a"])],
            "Agro-Dairy AI": [fmt(res["water_b"]), fmt(res["e_b"]), fmt(cost_b_farm)],
        }), use_container_width=True, hide_index=True)
        st.caption("Pompa enerjisi: E (kWh) = (Su m³ × Derinlik m × 9,81) / (3600 × Pompa verimi). "
                   "Katsayılar ve fiyatlar sentetik varsayımdır, saha verisiyle doğrulanmalıdır.")


# ----------------------------------------------------------------------------
# SAYFA BAŞI VE MOD SEÇİMİ
# ----------------------------------------------------------------------------
st.markdown(
    '<div class="hero"><div class="h1">🌾 Agro-Dairy AI</div>'
    '<div class="h2">Burdur Havzası su, elektrik ve süt hesabı. Sütünüz aynı kalsın, faturanız ve suyunuz azalsın.</div></div>',
    unsafe_allow_html=True,
)
MODE_FARMER = "👨‍🌾 Çiftçi Görünümü (Sade Mobil)"
MODE_COOP = "🏢 Kooperatif / Birlik Paneli (Bölgesel Etki)"
mode = st.radio("Kullanıcı Modu", [MODE_FARMER, MODE_COOP], horizontal=True, key="mode")

if mode == MODE_FARMER:
    farmer_view()
else:
    coop_view()
