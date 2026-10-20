# -*- coding: utf-8 -*-
# Kurulum:
#   pip install streamlit plotly pandas google-generativeai
# Çalıştırma:
#   streamlit run app.py

import html
import hashlib
import re
import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import google.generativeai as genai
    GENAI_OK = True
except Exception:  # kütüphane yoksa sistem yine çalışır
    genai = None
    GENAI_OK = False

# ----------------------------------------------------------------------------
# SAYFA AYARLARI VE TEMA
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Agro-Dairy AI | Burdur Havzası",
    page_icon="🌾",
    layout="wide",
)

CSS = """
<style>
.block-container {padding-top: 1.5rem;}
.hero {background: linear-gradient(135deg, #14532d 0%, #2e7d32 55%, #65a30d 100%);
       padding: 22px 28px; border-radius: 16px; color: #fff; margin-bottom: 18px;}
.hero h1 {color: #fff; font-size: 1.7rem; margin: 0 0 6px 0;}
.hero p {color: #ecfccb; margin: 0; font-size: 0.95rem;}
.kpi {background: #f7fbf3; border: 1px solid #d9ead3; border-left: 6px solid #2e7d32;
      border-radius: 12px; padding: 14px 18px;}
.kpi .t {color: #4b5d4a; font-size: 0.82rem; font-weight: 600;}
.kpi .v {color: #14532d; font-size: 1.7rem; font-weight: 800; line-height: 1.2;}
.kpi .s {color: #65806a; font-size: 0.8rem;}
.phone {background: #e5ddd5; border-radius: 16px; padding: 18px; max-width: 520px;
        border: 1px solid #cfc7bd;}
.phone .hdr {background: #075e54; color: #fff; padding: 8px 14px; border-radius: 10px;
             font-size: 0.85rem; margin-bottom: 12px;}
.bubble {background: #dcf8c6; color: #111; padding: 10px 14px; border-radius: 10px 0 10px 10px;
         box-shadow: 0 1px 1px rgba(0,0,0,.15); font-size: 0.95rem; line-height: 1.45;
         margin-left: 40px;}
.bubble .time {display: block; text-align: right; color: #667781; font-size: 0.7rem; margin-top: 4px;}
.note {background: #fffbea; border-left: 5px solid #f59e0b; padding: 12px 16px;
       border-radius: 8px; color: #333;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# SABİT KATSAYILAR (SENTETİK BURDUR VERİSİ - KENAR ÇUBUĞUNDAN DEĞİŞTİRİLEBİLİR)
# ----------------------------------------------------------------------------
G = 9.81                      # yerçekimi (m/s²)
SEASON_MONTHS_DEFAULT = 5     # Mayıs-Eylül sulama sezonu
# Senaryo A alan payları (mevcut durum)
MIX_A = {"Silajlık mısır": 0.60, "Yonca": 0.40}
# Senaryo B: mısır payı %40 azaltılır, boşalan pay sorgum-sudan ve fiğe verilir
CORN_CUT = 0.40
freed = MIX_A["Silajlık mısır"] * CORN_CUT
MIX_B = {
    "Silajlık mısır": MIX_A["Silajlık mısır"] * (1 - CORN_CUT),
    "Yonca": MIX_A["Yonca"],
    "Sorgum-sudan otu": freed * 2 / 3,
    "Fiğ": freed * 1 / 3,
}
# Dönüm başı sezonluk su ihtiyacı (m³/dönüm) - sadece Senaryo A bazı için
WATER_PER_DA = {"Silajlık mısır": 620.0, "Yonca": 780.0}
# Yem besin değerleri: (NEL MJ/kg KM, HP kesri)
FEEDS = {
    "Silajlık mısır": (6.6, 0.080),
    "Yonca": (5.6, 0.180),
    "Sorgum-sudan otu": (5.4, 0.095),
    "Fiğ": (5.5, 0.170),
    "Konsantre yem": (7.4, 0.180),
}


def fmt(x, nd=0):
    """Türkçe sayı biçimi: 12.345,6"""
    s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ----------------------------------------------------------------------------
# KATMAN 1: KARAR VE OPTİMİZASYON MOTORU
# ----------------------------------------------------------------------------
def pump_energy_kwh(volume_m3, depth_m, eff):
    """E (kWh) = (V * H * g) / (3600 * eta)"""
    return (volume_m3 * depth_m * G) / (3600.0 * eff)


def ration_balance(shares, cows_milk, bw):
    """Bir ineğin günlük NEL ve HP dengesi. Gerekirse konsantre ile dengeler."""
    dmi = 0.025 * bw + 0.10 * cows_milk              # kuru madde alımı (kg/gün)
    forage_dm = dmi * 0.55
    conc_dm = dmi * 0.45
    nel = sum(forage_dm * sh * FEEDS[k][0] for k, sh in shares.items())
    cp = sum(forage_dm * sh * FEEDS[k][1] * 1000 for k, sh in shares.items())
    nel += conc_dm * FEEDS["Konsantre yem"][0]
    cp += conc_dm * FEEDS["Konsantre yem"][1] * 1000
    req_nel = 0.335 * bw ** 0.75 + 3.14 * cows_milk   # MJ/gün
    req_cp = 4.0 * bw ** 0.75 + 80.0 * cows_milk      # g/gün
    # açık varsa ek konsantre ile kapat
    need_kg = max(
        0.0,
        (req_nel - nel) / FEEDS["Konsantre yem"][0],
        (req_cp - cp) / (FEEDS["Konsantre yem"][1] * 1000),
    )
    nel_f = nel + need_kg * FEEDS["Konsantre yem"][0]
    cp_f = cp + need_kg * FEEDS["Konsantre yem"][1] * 1000
    return {
        "dmi": dmi, "req_nel": req_nel, "req_cp": req_cp,
        "nel_raw": nel, "cp_raw": cp,
        "extra_conc_kg": need_kg, "nel_final": nel_f, "cp_final": cp_f,
        "nel_cov": nel_f / req_nel * 100, "cp_cov": cp_f / req_cp * 100,
    }


def run_engine(p):
    months = p["season_months"]
    season_days = months * 30

    # --- Su tüketimi ---
    a_per_da = sum(WATER_PER_DA[k] * sh for k, sh in MIX_A.items())
    b_per_da = a_per_da * (1 - p["water_red"] / 100.0)
    water_a = a_per_da * p["area"]
    water_b = b_per_da * p["area"]
    water_saved = water_a - water_b

    # --- Pompa enerjisi ---
    e_a = pump_energy_kwh(water_a, p["depth"], p["eff"])
    e_b = pump_energy_kwh(water_b, p["depth"], p["eff"])
    kwh_saved = e_a - e_b

    # --- Maliyet (A: mevcut gündüz tarifesi, B: seçilen rejim) ---
    price_a = p["price"]
    price_b = p["price"] * (1 - p["night_disc"] / 100.0) if p["night"] else p["price"]
    cost_a = e_a * price_a
    cost_b = e_b * price_b
    elec_saving = cost_a - cost_b
    elec_pct = elec_saving / cost_a * 100 if cost_a else 0.0

    # --- Zootekni ---
    zA = ration_balance(MIX_A, p["milk"], p["bw"])
    zB = ration_balance(MIX_B, p["milk"], p["bw"])
    extra_kg_day = max(0.0, zB["extra_conc_kg"] - zA["extra_conc_kg"])
    extra_feed_cost = extra_kg_day * p["cows"] * season_days * p["conc_price"]
    net_benefit = elec_saving - extra_feed_cost

    milk_month = p["cows"] * p["milk"] * 30
    milk_season = p["cows"] * p["milk"] * season_days
    milk_change_pct = 0.0 if (zB["nel_cov"] >= 99.99 and zB["cp_cov"] >= 99.99) else \
        -(100 - min(zB["nel_cov"], zB["cp_cov"]))

    return {
        "months": months, "season_days": season_days,
        "a_per_da": a_per_da, "b_per_da": b_per_da,
        "water_a": water_a, "water_b": water_b, "water_saved": water_saved,
        "water_saved_month": water_saved / months,
        "e_a": e_a, "e_b": e_b, "kwh_saved": kwh_saved, "kwh_saved_month": kwh_saved / months,
        "price_a": price_a, "price_b": price_b,
        "cost_a": cost_a, "cost_b": cost_b,
        "cost_a_month": cost_a / months, "cost_b_month": cost_b / months,
        "elec_saving": elec_saving, "elec_saving_month": elec_saving / months,
        "elec_pct": elec_pct,
        "zA": zA, "zB": zB, "extra_kg_day": extra_kg_day,
        "extra_feed_cost": extra_feed_cost, "net_benefit": net_benefit,
        "milk_month": milk_month, "milk_season": milk_season,
        "milk_change_pct": milk_change_pct,
    }


# ----------------------------------------------------------------------------
# KATMAN 2: DOĞAL DİL ÇIKTISI (GEMINI + YEREL YEDEK)
# ----------------------------------------------------------------------------
SYSTEM_ROLE = (
    "Sen Burdur Damızlık Sığır Yetiştiricileri Birliği ve Sulama Kooperatifi uzmanısın. "
    "Çiftçiyi suçlamayan, onun kazancını ve emeğini koruyan, samimi, net ve doğrudan "
    "eyleme dönüştürülebilir bir dille konuşursun."
)


def build_prompt(p, r):
    rejim = "gece (indirimli) tarife" if p["night"] else "gündüz (standart) tarife"
    return f"""Aşağıdaki hesaplanmış sonuçlara göre iki çıktı üret. Rakamları değiştirme, uydurma.

Girdiler: {p['cows']} sağmal inek, inek başı {p['milk']} L/gün süt, {p['area']} dönüm kaba yem alanı,
kuyu seviyesi {p['depth']} m, sulama rejimi: {rejim}.

Sonuçlar (Senaryo B: silajlık mısır payı %40 azaltılıp sorgum-sudan otu ve fiğ eklendi):
- Aylık kurtarılan su: {fmt(r['water_saved_month'])} ton; sezonluk: {fmt(r['water_saved'])} ton
- Aylık kurtarılan elektrik: {fmt(r['kwh_saved_month'])} kWh; sezonluk: {fmt(r['kwh_saved'])} kWh
- Aylık fatura indirimi: {fmt(r['elec_saving_month'])} TL; sezonluk: {fmt(r['elec_saving'])} TL (%{fmt(r['elec_pct'],1)})
- Korunan süt: aylık {fmt(r['milk_month'])} L, sezonluk {fmt(r['milk_season'])} L (verim kaybı %0)
- Rasyon dengesi için ek konsantre maliyeti (sezonluk): {fmt(r['extra_feed_cost'])} TL

Çıktı formatı (başlıkları aynen kullan):
[SMS]
Çiftçinin telefonuna gidecek 1-2 cümlelik WhatsApp/SMS taslağı. Nihai kararın çiftçide kaldığını hissettir.
[TEKNIK]
Kooperatif yetkilisi/mühendis için 1 paragraflık Teknik Karar Notu (su, enerji, rasyon dengesi, riskler)."""


def mock_advice(p, r):
    sms = (
        f"Merhaba, {p['area']} dönümlük kaba yem alanınızda mısır payını azaltıp sorgum-sudan otu ve fiğ "
        f"eklerseniz sezonda yaklaşık {fmt(r['water_saved'])} ton su ve {fmt(r['elec_saving'])} TL "
        f"elektrik faturası kurtarırsınız; ineklerinizin sütü ise aynı kalır. "
        f"Karar sizin, isterseniz kooperatifimiz ekim planını birlikte çıkarsın."
    )
    rejim = "gece indirimli tarifeye geçiş" if p["night"] else "standart gündüz tarifesi"
    note = (
        f"{p['cows']} sağmal inek ve {p['area']} dönüm alan için yapılan modelde, silajlık mısır payı %40 azaltılıp "
        f"yerine sorgum-sudan otu ve fiğ konulduğunda dönüm başı sulama suyu yaklaşık "
        f"{fmt(r['a_per_da'])} m³'ten {fmt(r['b_per_da'])} m³'e düşmektedir. {p['depth']} m kuyu seviyesi ve "
        f"%{int(p['eff']*100)} pompa verimiyle sezonluk pompa enerjisi {fmt(r['e_a'])} kWh'ten {fmt(r['e_b'])} kWh'e "
        f"inerken ({rejim} dahil) elektrik gideri %{fmt(r['elec_pct'],1)} azalmaktadır. Rasyon tarafında NEL ve ham protein "
        f"ihtiyacı konsantre yem dengelemesiyle %100 karşılanmakta, bunun sezonluk ek maliyeti {fmt(r['extra_feed_cost'])} TL "
        f"olup net kazanç {fmt(r['net_benefit'])} TL'dir. Sorgum-sudan otunda ilk dönem verim ve biçim zamanlaması ile "
        f"fiğ ekim tarihi saha koşullarında doğrulanmalı, pilot parsel ile başlanması önerilir."
    )
    return sms, note


def gemini_advice(api_key, model_name, p, r):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name, system_instruction=SYSTEM_ROLE)
    resp = model.generate_content(build_prompt(p, r))
    text = (resp.text or "").strip()
    m_sms = re.search(r"\[SMS\](.*?)(\[TEKNIK\]|$)", text, re.S)
    m_tek = re.search(r"\[TEKNIK\](.*)$", text, re.S)
    if not m_sms or not m_tek:
        raise ValueError("Model çıktısı beklenen formatta değil.")
    return m_sms.group(1).strip(), m_tek.group(1).strip()


def build_report(p, r, sms, note, source):
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    rejim = "Gece (indirimli)" if p["night"] else "Gündüz / standart"
    return f"""AGRO-DAIRY AI | KARAR RAPORU
Burdur Havzası Su, Enerji ve Rasyon Karar Destek Platformu
Tarih: {now}  |  Metin kaynağı: {source}
{'=' * 70}

GİRDİLER
- Sağmal inek sayısı: {p['cows']}
- Hedef süt verimi: {p['milk']} L/inek/gün
- Kaba yem alanı: {p['area']} dönüm
- Kuyu seviyesi: {p['depth']} m
- Sulama rejimi: {rejim}
- Sulama sezonu: {r['months']} ay

SENARYO KARŞILAŞTIRMASI (sezonluk)
- Su tüketimi: A = {fmt(r['water_a'])} m³ | B = {fmt(r['water_b'])} m³
- Pompa enerjisi: A = {fmt(r['e_a'])} kWh | B = {fmt(r['e_b'])} kWh
- Elektrik faturası: A = {fmt(r['cost_a'])} TL | B = {fmt(r['cost_b'])} TL

TASARRUF
- Kurtarılan su: aylık {fmt(r['water_saved_month'])} ton | sezonluk {fmt(r['water_saved'])} ton
- Kurtarılan elektrik: aylık {fmt(r['kwh_saved_month'])} kWh | sezonluk {fmt(r['kwh_saved'])} kWh
- Fatura indirimi: aylık {fmt(r['elec_saving_month'])} TL | sezonluk {fmt(r['elec_saving'])} TL (%{fmt(r['elec_pct'],1)})
- Ek konsantre yem maliyeti (sezonluk): {fmt(r['extra_feed_cost'])} TL
- Net kazanç (sezonluk): {fmt(r['net_benefit'])} TL
- Korunan süt: aylık {fmt(r['milk_month'])} L | sezonluk {fmt(r['milk_season'])} L
- İnek başı süt verimi değişimi: %{fmt(abs(r['milk_change_pct']),1)} (sabit)

ÇİFTÇİ MESAJI (SMS / WhatsApp)
{sms}

TEKNİK KARAR NOTU
{note}

Not: Sonuçlar sentetik Burdur çiftlik verileri ve kenar çubuğundaki varsayımlarla
üretilmiş karar destek çıktısıdır. Nihai ekim ve sulama kararı çiftçiye aittir.
"""


# ----------------------------------------------------------------------------
# KENAR ÇUBUĞU
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("🌾 Çiftlik Parametreleri")
    cows = st.slider("Sağmal İnek Sayısı", 5, 200, 30)
    milk = st.number_input("Hedeflenen İnek Başına Günlük Süt Verimi (Litre)",
                           min_value=10.0, max_value=45.0, value=24.0, step=0.5)
    area = st.number_input("Kaba Yem Ekim Alanı (Dönüm / Dekar)",
                           min_value=1, max_value=2000, value=20, step=1)
    depth = st.slider("Derin Kuyu Statik/Dinamik Su Seviyesi (Metre)", 50, 250, 180)
    regime = st.radio("Sulama Rejimi Seçimi",
                      ["Gündüz / Standart Tarife", "Gece (İndirimli) Tarife"])

    with st.expander("⚙️ Gelişmiş Varsayımlar"):
        price = st.number_input("Tarımsal elektrik birim fiyatı (TL/kWh)", 0.5, 20.0, 4.5, 0.1)
        night_disc = st.slider("Gece tarifesi indirimi (%)", 0, 50, 20)
        eff = st.slider("Pompa verimi", 0.40, 0.85, 0.65, 0.01)
        water_red = st.slider("Alternatif karışım su azalışı (%)", 20, 45, 35)
        season_months = st.slider("Sulama sezonu (ay)", 3, 8, SEASON_MONTHS_DEFAULT)
        bw = st.number_input("İnek canlı ağırlığı (kg)", 450, 750, 600, 10)
        conc_price = st.number_input("Konsantre yem fiyatı (TL/kg)", 5.0, 40.0, 13.0, 0.5)

    st.divider()
    # API anahtarı sunucu tarafında (st.secrets) tutulur; kullanıcı görmez ve girmez.
    try:
        SERVER_KEY = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
        SERVER_MODEL = str(st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")).strip()
    except Exception:
        SERVER_KEY, SERVER_MODEL = "", "gemini-2.5-flash"

    if SERVER_KEY:
        api_key, model_name = SERVER_KEY, SERVER_MODEL
        st.caption("🤖 Yapay zekâ modu aktif (Gemini).")
    else:
        # Yerel geliştirme: secrets yoksa anahtar elle girilebilir.
        st.subheader("🤖 Gemini (İsteğe Bağlı)")
        api_key = st.text_input("Google Gemini API Key", type="password",
                                help="Boş bırakılırsa yerel yedek (mock) tavsiye metni üretilir.")
        model_name = st.text_input("Model adı", value="gemini-2.5-flash")
        if not GENAI_OK:
            st.caption("google-generativeai kurulu değil; yerel yedek mod kullanılacak.")

MAX_AI_CALLS = 5  # oturum başına Gemini çağrı sınırı (kota/abuse koruması)

params = {
    "cows": int(cows), "milk": float(milk), "area": int(area), "depth": int(depth),
    "night": regime.startswith("Gece"), "price": float(price), "night_disc": float(night_disc),
    "eff": float(eff), "water_red": float(water_red), "season_months": int(season_months),
    "bw": float(bw), "conc_price": float(conc_price),
}
res = run_engine(params)

# ----------------------------------------------------------------------------
# BAŞLIK
# ----------------------------------------------------------------------------
st.markdown(
    """<div class="hero">
    <h1>Agro-Dairy AI | Burdur Havzası Su, Enerji ve Rasyon Karar Destek Platformu</h1>
    <p>Süt verimini koruyarak yeraltı suyunu ve kuyu elektriğini azaltan, kooperatif üzerinden
    SMS/WhatsApp ile çalışan karar destek sistemi. Nihai karar her zaman çiftçidedir.</p></div>""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# TAVSİYE METNİ (session_state ile)
# ----------------------------------------------------------------------------
sig = hashlib.md5((repr(sorted(params.items())) + model_name + str(bool(api_key))).encode()).hexdigest()
mock_sms, mock_note = mock_advice(params, res)

if "advice" not in st.session_state:
    st.session_state["advice"] = None

top_l, top_r = st.columns([3, 1])
with top_r:
    gen_clicked = st.button("✨ Yapay Zekâ ile Tavsiye Üret", use_container_width=True)

if gen_clicked:
    calls = st.session_state.get("ai_calls", 0)
    if api_key and GENAI_OK and calls >= MAX_AI_CALLS:
        st.info(f"Bu oturum için yapay zekâ çağrı sınırına ulaşıldı ({MAX_AI_CALLS}). "
                "Yerel yedek tavsiye metni gösteriliyor.")
        st.session_state["advice"] = (sig, mock_sms, mock_note, "Yerel yedek (mock)")
    elif api_key and GENAI_OK:
        st.session_state["ai_calls"] = calls + 1
        try:
            with st.spinner("Gemini tavsiye metnini hazırlıyor..."):
                g_sms, g_note = gemini_advice(api_key, model_name, params, res)
            st.session_state["advice"] = (sig, g_sms, g_note, f"Gemini ({model_name})")
        except Exception as exc:
            st.warning(f"Gemini çağrısı başarısız oldu, yerel yedek metin kullanılıyor. Ayrıntı: {exc}")
            st.session_state["advice"] = (sig, mock_sms, mock_note, "Yerel yedek (mock)")
    else:
        st.info("API anahtarı girilmediği için yerel yedek (mock) tavsiye üretildi.")
        st.session_state["advice"] = (sig, mock_sms, mock_note, "Yerel yedek (mock)")

adv = st.session_state["advice"]
if adv and adv[0] == sig:
    _, sms_text, tech_note, source = adv
else:
    sms_text, tech_note, source = mock_sms, mock_note, "Yerel yedek (mock)"

# ----------------------------------------------------------------------------
# METRİK KARTLARI
# ----------------------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("💧 Kurtarılan Yeraltı Suyu (sezonluk)", f"{fmt(res['water_saved'])} m³",
          delta=f"-%{fmt(params['water_red'])} su çekimi", delta_color="normal")
c2.metric("⚡ Elektrik Faturası Tasarrufu (sezonluk)", f"{fmt(res['elec_saving'])} TL",
          delta=f"-%{fmt(res['elec_pct'],1)} fatura", delta_color="normal")
c3.metric("🥛 İnek Süt Verimi Değişimi", "%0 Sabit",
          delta=f"{params['milk']} L/inek/gün korunuyor", delta_color="off")

k1, k2, k3, k4 = st.columns(4)
for col, title, val, sub in [
    (k1, "Aylık Su Tasarrufu", f"{fmt(res['water_saved_month'])} ton", "ay başına"),
    (k2, "Kurtarılan Elektrik", f"{fmt(res['kwh_saved'])} kWh", f"aylık {fmt(res['kwh_saved_month'])} kWh"),
    (k3, "Korunan Süt (sezon)", f"{fmt(res['milk_season'])} L", f"aylık {fmt(res['milk_month'])} L"),
    (k4, "Net Kazanç (sezon)", f"{fmt(res['net_benefit'])} TL", "ek yem maliyeti düşüldükten sonra"),
]:
    col.markdown(f'<div class="kpi"><div class="t">{title}</div><div class="v">{val}</div>'
                 f'<div class="s">{sub}</div></div>', unsafe_allow_html=True)

st.write("")

# ----------------------------------------------------------------------------
# SEKMELER
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Karşılaştırma", "💬 Mesaj & Teknik Not", "🐄 Zootekni Doğrulaması", "📋 Varsayımlar"]
)

with tab1:
    g1, g2 = st.columns(2)
    colors = ["#b45309", "#2e7d32"]
    labels = ["Mevcut Durum", "Agro-Dairy AI"]

    fig_w = go.Figure(go.Bar(
        x=labels, y=[res["water_a"], res["water_b"]], marker_color=colors,
        text=[f"{fmt(res['water_a'])} m³", f"{fmt(res['water_b'])} m³"], textposition="outside"))
    fig_w.update_layout(title="Sezonluk Su Tüketimi (m³)", yaxis_title="m³",
                        height=420, margin=dict(t=60, b=20), showlegend=False)
    g1.plotly_chart(fig_w, use_container_width=True)

    fig_e = go.Figure(go.Bar(
        x=labels, y=[res["cost_a"], res["cost_b"]], marker_color=colors,
        text=[f"{fmt(res['cost_a'])} TL", f"{fmt(res['cost_b'])} TL"], textposition="outside"))
    fig_e.update_layout(title="Sezonluk Pompa Elektrik Faturası (TL)", yaxis_title="TL",
                        height=420, margin=dict(t=60, b=20), showlegend=False)
    g2.plotly_chart(fig_e, use_container_width=True)

    summary = pd.DataFrame({
        "Gösterge": ["Su (m³/sezon)", "Pompa enerjisi (kWh/sezon)", "Birim fiyat (TL/kWh)",
                     "Elektrik faturası (TL/sezon)", "Elektrik faturası (TL/ay)"],
        "Mevcut Durum": [fmt(res["water_a"]), fmt(res["e_a"]), fmt(res["price_a"], 2),
                         fmt(res["cost_a"]), fmt(res["cost_a_month"])],
        "Agro-Dairy AI": [fmt(res["water_b"]), fmt(res["e_b"]), fmt(res["price_b"], 2),
                          fmt(res["cost_b"]), fmt(res["cost_b_month"])],
    })
    st.subheader("Kooperatif Tasarruf Analiz Tablosu")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    mix_rows = []
    for k in MIX_B:
        mix_rows.append({"Yem Bitkisi": k,
                         "Senaryo A (alan payı)": f"%{fmt(MIX_A.get(k, 0) * 100, 0)}",
                         "Senaryo B (alan payı)": f"%{fmt(MIX_B[k] * 100, 0)}"})
    st.subheader("Ekim Deseni")
    st.dataframe(pd.DataFrame(mix_rows), use_container_width=True, hide_index=True)

with tab2:
    left, right = st.columns([1, 1])
    with left:
        st.subheader("📱 Çiftçiye Gidecek Mesaj")
        now_t = datetime.datetime.now().strftime("%H:%M")
        st.markdown(
            f"""<div class="phone"><div class="hdr">💬 Burdur Sulama Kooperatifi</div>
            <div class="bubble">{html.escape(sms_text)}<span class="time">{now_t} ✓✓</span></div></div>""",
            unsafe_allow_html=True,
        )
        st.caption(f"Metin kaynağı: {source}")
    with right:
        st.subheader("🛠️ Teknik Karar Notu")
        st.markdown(f'<div class="note">{html.escape(tech_note)}</div>', unsafe_allow_html=True)

    st.write("")
    report = build_report(params, res, sms_text, tech_note, source)
    st.download_button("⬇️ Karar Raporunu İndir (.txt)", data=report.encode("utf-8"),
                       file_name="agro_dairy_karar_raporu.txt", mime="text/plain")

with tab3:
    zA, zB = res["zA"], res["zB"]
    st.markdown(
        f"İnek başı günlük ihtiyaç: **{fmt(zA['req_nel'],1)} MJ NEL** ve **{fmt(zA['req_cp'])} g ham protein** "
        f"(KMA ≈ {fmt(zA['dmi'],1)} kg/gün)."
    )
    zdf = pd.DataFrame({
        "Gösterge": ["NEL sağlanan (MJ/gün)", "HP sağlanan (g/gün)", "Ek konsantre (kg/inek/gün)",
                     "NEL karşılama (%)", "HP karşılama (%)"],
        "Senaryo A": [fmt(zA["nel_final"], 1), fmt(zA["cp_final"]), fmt(zA["extra_conc_kg"], 2),
                      fmt(zA["nel_cov"], 1), fmt(zA["cp_cov"], 1)],
        "Senaryo B": [fmt(zB["nel_final"], 1), fmt(zB["cp_final"]), fmt(zB["extra_conc_kg"], 2),
                      fmt(zB["nel_cov"], 1), fmt(zB["cp_cov"], 1)],
    })
    st.dataframe(zdf, use_container_width=True, hide_index=True)
    if res["milk_change_pct"] == 0:
        st.success("Rasyon dengesi sağlandı: enerji ve protein ihtiyacı tam karşılanıyor, "
                   "inek başı süt verimi kaybı %0 olarak modellendi.")
    else:
        st.warning(f"Rasyon açığı var; modellenen verim değişimi %{fmt(res['milk_change_pct'],1)}.")
    st.caption(f"Senaryo B'de dengeyi korumak için gereken ek konsantre maliyeti sezonluk "
               f"{fmt(res['extra_feed_cost'])} TL olarak net kazançtan düşülmüştür.")

with tab4:
    st.markdown(
        f"""
**Formüller**
- Pompa enerjisi: `E (kWh) = (Su Hacmi m³ × Kuyu Derinliği m × g) / (3600 × Pompa Verimi)`, g = 9,81 m/s², verim = {params['eff']}
- Senaryo A: silajlık mısır %60 + yonca %40; ortalama {fmt(res['a_per_da'])} m³/dönüm/sezon
- Senaryo B: mısır payı %40 azaltılır (sorgum-sudan otu ve fiğe kaydırılır); dönüm başı su
  %{fmt(params['water_red'])} daha az = {fmt(res['b_per_da'])} m³/dönüm/sezon (PDR hedef parametresi)
- Maliyet: A her zaman gündüz tarifesiyle, B seçilen sulama rejimiyle hesaplanır
- Zootekni: KMA = 0,025×CA + 0,10×süt; NEL ihtiyacı = 0,335×CA^0,75 + 3,14×süt (MJ);
  HP ihtiyacı = 4×CA^0,75 + 80×süt (g). Açık, konsantre yemle kapatılır.

**Önemli:** Tüm katsayılar ve fiyatlar sentetik/varsayımsal olup saha verisi ve güncel EPDK tarifesiyle
doğrulanmalıdır. Sistem karar destek amaçlıdır; nihai ekim ve sulama kararı çiftçiye aittir.
"""
    )
