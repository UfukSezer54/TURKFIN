"""
TürkFin AI — Kripto Para Modülü v4
Veri: BTCTurk API (TRY bazlı, HMAC-SHA256 auth)
"""
import hmac, hashlib, base64, time, requests, math
import pandas as pd
import pandas_ta as ta
from typing import Dict, List, Optional, Tuple

# ── BTCTurk API Kimlik Bilgileri ─────────────────────────────────────────
_PUBLIC_KEY  = "4122b122-111f-46fb-810f-dc3064649eee"
_PRIVATE_KEY = "tBH6YCT8us2ywXL7tMcQoUktKiEU1SuR"
_API_BASE    = "https://api.btcturk.com"
_GRAPH_BASE  = "https://graph.btcturk.com"

# ── Desteklenen Kripto → Pair eşlemesi (BTCTurk TRY çiftleri) ────────────
KRIPTO_MAP: Dict[str, str] = {
    "BTC":   "BTCTRY",
    "ETH":   "ETHTRY",
    "BNB":   "BNBTRY",
    "SOL":   "SOLTRY",
    "XRP":   "XRPTRY",
    "ADA":   "ADATRY",
    "AVAX":  "AVAXTRY",
    "DOGE":  "DOGETRY",
    "LINK":  "LINKTRY",
    "DOT":   "DOTTRY",
    "MATIC": "MATICTRY",
    "ATOM":  "ATOMTRY",
    "LTC":   "LTCTRY",
    "UNI":   "UNITRY",
    "TRX":   "TRXTRY",
    "NEAR":  "NEARTRY",
    "TON":   "TONTRY",
    "PEPE":  "PEPETRY",
    "WIF":   "WIFTRY",
    "ARB":   "ARBTRY",
    "OP":    "OPTRY",
    "SUI":   "SUITRY",
}

PAIR_TO_SEM = {v: k for k, v in KRIPTO_MAP.items()}

def desteklenen_mi(sembol: str) -> bool:
    return sembol.upper() in KRIPTO_MAP

# ── Auth Header Üretimi ───────────────────────────────────────────────────
def _auth_headers() -> Dict[str, str]:
    stamp   = str(int(time.time() * 1000))
    message = _PUBLIC_KEY + stamp
    try:
        secret = base64.b64decode(_PRIVATE_KEY)
    except Exception:
        secret = _PRIVATE_KEY.encode("utf-8")
    sig = base64.b64encode(
        hmac.new(secret, message.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")
    return {
        "X-PCK":       _PUBLIC_KEY,
        "X-Stamp":     stamp,
        "X-Signature": sig,
        "Content-Type": "application/json",
        "Accept":      "application/json",
    }

def _get_public(url: str, params: dict = None) -> Optional[dict]:
    headers = {"Accept": "application/json", "User-Agent": "TurkFinAI/4.0"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 429:
            time.sleep(2)
            r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"BTCTurk public hata [{url}]: {e}")
        return None

def _get_auth(url: str, params: dict = None) -> Optional[dict]:
    try:
        r = requests.get(url, headers=_auth_headers(), params=params, timeout=10)
        if r.status_code == 429:
            time.sleep(2)
            r = requests.get(url, headers=_auth_headers(), params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"BTCTurk auth hata [{url}]: {e}")
        return None

# ── Tüm Ticker Verisi ─────────────────────────────────────────────────────
def get_kripto_fiyatlar(semboller: List[str] = None) -> List[Dict]:
    """BTCTurk public ticker — TRY bazlı anlık fiyatlar"""
    data = _get_public(f"{_API_BASE}/api/v2/ticker")
    if not data or not data.get("data"):
        return []

    hedef_pairs = set()
    if semboller:
        for s in semboller:
            pair = KRIPTO_MAP.get(s.upper())
            if pair:
                hedef_pairs.add(pair)
    else:
        hedef_pairs = set(KRIPTO_MAP.values())

    sonuc = []
    for item in data["data"]:
        pair = item.get("pairSymbol", "")
        if pair not in hedef_pairs:
            continue
        sem = PAIR_TO_SEM.get(pair, pair.replace("TRY", ""))
        try:
            sonuc.append({
                "sembol":        sem,
                "pair":          pair,
                "fiyat":         round(float(item.get("last", 0)), 4),
                "degisim_24h":   round(float(item.get("dailyPercent", 0)), 2),
                "hacim_24h":     round(float(item.get("volume", 0)), 2),
                "en_yuksek_24h": round(float(item.get("high", 0)), 4),
                "en_dusuk_24h":  round(float(item.get("low", 0)), 4),
                "ask":           round(float(item.get("ask", 0)), 4),
                "bid":           round(float(item.get("bid", 0)), 4),
            })
        except Exception:
            continue

    # Piyasa büyüklüğüne göre sırala (hacim proxy)
    return sorted(sonuc, key=lambda x: x["hacim_24h"], reverse=True)


# ── OHLC Verisi (BTCTurk Graph API) ──────────────────────────────────────
def get_kripto_ohlc(sembol: str, gun: int = 90) -> List[Dict]:
    pair = KRIPTO_MAP.get(sembol.upper())
    if not pair:
        return []

    now   = int(time.time())
    start = now - gun * 86400

    # BTCTurk graph API — public, auth gerekmez
    data = _get_public(
        f"{_GRAPH_BASE}/v1/ohlcdata",
        {"pair": pair, "from": start, "to": now}
    )
    if not data or not isinstance(data, list):
        # Alternatif endpoint dene
        data = _get_public(
            f"{_API_BASE}/api/v2/ohlc",
            {"pairSymbol": pair}
        )
    if not data or not isinstance(data, list):
        return []

    sonuc = []
    for row in data:
        try:
            if isinstance(row, list) and len(row) >= 6:
                ts, o, h, l, c, v = row[0], row[1], row[2], row[3], row[4], row[5]
            elif isinstance(row, dict):
                ts = row.get("time") or row.get("timestamp") or row.get("date")
                o  = row.get("open")
                h  = row.get("high")
                l  = row.get("low")
                c  = row.get("close")
                v  = row.get("volume", 0)
            else:
                continue
            if not all([ts, o, h, l, c]):
                continue
            # Timestamp ms → s dönüşümü
            ts_s = int(ts) // 1000 if int(ts) > 1e10 else int(ts)
            sonuc.append({
                "time":   ts_s,
                "open":   round(float(o), 4),
                "high":   round(float(h), 4),
                "low":    round(float(l), 4),
                "close":  round(float(c), 4),
                "volume": round(float(v), 2),
            })
        except Exception:
            continue

    return sorted(sonuc, key=lambda x: x["time"])


# ── Tek Kripto Anlık Detay ────────────────────────────────────────────────
def get_kripto_detay(sembol: str) -> Dict:
    pair = KRIPTO_MAP.get(sembol.upper())
    if not pair:
        return {"hata": f"{sembol} BTCTurk'te desteklenmiyor"}

    data = _get_public(f"{_API_BASE}/api/v2/ticker", {"pairSymbol": pair})
    if not data or not data.get("data"):
        return {"hata": "Veri alınamadı"}

    item = data["data"][0] if isinstance(data["data"], list) else data["data"]
    try:
        return {
            "sembol":        sembol.upper(),
            "pair":          pair,
            "isim":          sembol.upper(),
            "fiyat":         round(float(item.get("last", 0)), 4),
            "degisim_24h":   round(float(item.get("dailyPercent", 0)), 2),
            "hacim_24h":     round(float(item.get("volume", 0)), 2),
            "en_yuksek_24h": round(float(item.get("high", 0)), 4),
            "en_dusuk_24h":  round(float(item.get("low", 0)), 4),
            "ask":           round(float(item.get("ask", 0)), 4),
            "bid":           round(float(item.get("bid", 0)), 4),
            "hata":          None,
        }
    except Exception as e:
        return {"hata": str(e)}


# ── Kapsamlı Teknik Analiz ────────────────────────────────────────────────
def get_kripto_analiz(sembol: str, gun: int = 90) -> Dict:
    detay = get_kripto_detay(sembol)
    if detay.get("hata"):
        return detay

    ohlc = get_kripto_ohlc(sembol, gun=gun)
    if not ohlc or len(ohlc) < 20:
        detay.update({"skor": 50, "tavsiye": "🟡 İZLE", "sinyaller": [],
                      "hata": None, "rsi": None, "macd": None, "macd_signal": None})
        return detay

    df = pd.DataFrame(ohlc)
    df["datetime"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("datetime", inplace=True)

    # ── İndikatörler ─────────────────────────────────────────────────
    df["RSI"]    = ta.rsi(df["close"], length=14)
    df["SMA_20"] = ta.sma(df["close"], length=20)
    df["SMA_50"] = ta.sma(df["close"], length=min(50, len(df) - 1))
    df["SMA_200"]= ta.sma(df["close"], length=min(200, len(df) - 1))
    df["EMA_20"] = ta.ema(df["close"], length=20)

    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is not None:
        df["BB_upper"]  = bb.iloc[:, 2]
        df["BB_middle"] = bb.iloc[:, 0]
        df["BB_lower"]  = bb.iloc[:, 1]

    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd_df is not None:
        df["MACD_12_26_9"]  = macd_df.iloc[:, 0]
        df["MACDs_12_26_9"] = macd_df.iloc[:, 1]
        df["MACDh_12_26_9"] = macd_df.iloc[:, 2]

    try:
        st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3)
        if st is not None:
            df["SUPERTREND"]     = st.iloc[:, 0]
            df["SUPERTREND_DIR"] = st.iloc[:, 1]
    except Exception:
        pass

    try:
        ichimoku, _ = ta.ichimoku(df["high"], df["low"], df["close"])
        if ichimoku is not None:
            df["ICHIMOKU_TENKAN"] = ichimoku.iloc[:, 0]
            df["ICHIMOKU_KIJUN"]  = ichimoku.iloc[:, 1]
            df["ICHIMOKU_SSA"]    = ichimoku.iloc[:, 2]
            df["ICHIMOKU_SSB"]    = ichimoku.iloc[:, 3]
    except Exception:
        pass

    # ── Son satır değerleri ───────────────────────────────────────────
    last = df.iloc[-1]
    def sv(col):
        v = last.get(col)
        return round(float(v), 4) if v is not None and pd.notna(v) else None

    fiyat  = detay.get("fiyat") or 0
    rsi    = sv("RSI")
    macd   = sv("MACD_12_26_9")
    macds  = sv("MACDs_12_26_9")
    macdh  = sv("MACDh_12_26_9")
    sma20  = sv("SMA_20")
    sma50  = sv("SMA_50")
    sma200 = sv("SMA_200")
    ema20  = sv("EMA_20")
    bbu    = sv("BB_upper")
    bbm    = sv("BB_middle")
    bbl    = sv("BB_lower")
    st_val = sv("SUPERTREND")
    st_dir = sv("SUPERTREND_DIR")
    ich_t  = sv("ICHIMOKU_TENKAN")
    ich_k  = sv("ICHIMOKU_KIJUN")

    # Fibonacci (son 30 mum üzerinden)
    fib_win = df["close"].tail(30)
    fib_high = float(fib_win.max())
    fib_low  = float(fib_win.min())
    fib_diff = fib_high - fib_low
    fibs = {
        "0.0":   round(fib_high, 4),
        "0.236": round(fib_high - 0.236 * fib_diff, 4),
        "0.382": round(fib_high - 0.382 * fib_diff, 4),
        "0.5":   round(fib_high - 0.5   * fib_diff, 4),
        "0.618": round(fib_high - 0.618 * fib_diff, 4),
        "1.0":   round(fib_low, 4),
    }

    # BB yüzde pozisyonu
    bb_pct = None
    if bbu and bbl and (bbu - bbl) > 0:
        bb_pct = round((fiyat - bbl) / (bbu - bbl) * 100, 1)

    # ── Skor & Sinyal Sistemi (0-100) ────────────────────────────────
    skor = 50
    sinyaller: List[str] = []

    # RSI (±20)
    if rsi is not None:
        if rsi < 25:
            skor += 20; sinyaller.append(f"RSI {rsi:.1f} — Aşırı Satım 🟢 Güçlü AL")
        elif rsi < 35:
            skor += 12; sinyaller.append(f"RSI {rsi:.1f} — Satım Bölgesi 🟢 AL")
        elif rsi < 45:
            skor += 4
        elif rsi < 55:
            pass
        elif rsi < 65:
            skor -= 4
        elif rsi < 75:
            skor -= 12; sinyaller.append(f"RSI {rsi:.1f} — Alım Bölgesi 🔴 SAT")
        else:
            skor -= 20; sinyaller.append(f"RSI {rsi:.1f} — Aşırı Alım 🔴 Güçlü SAT")

    # MACD (±15)
    if macd is not None and macds is not None:
        if macd > macds:
            skor += 10; sinyaller.append("MACD > Sinyal — Yükseliş Momentum 🟢")
            if macd > 0: skor += 5; sinyaller.append("MACD Sıfır Üstü — Boğa Bölgesi")
        else:
            skor -= 10; sinyaller.append("MACD < Sinyal — Düşüş Momentum 🔴")
            if macd < 0: skor -= 5; sinyaller.append("MACD Sıfır Altı — Ayı Bölgesi")

    # Supertrend (±15)
    if st_dir is not None:
        if st_dir == 1:
            skor += 15; sinyaller.append("Supertrend BOĞA ⚡🟢")
        else:
            skor -= 15; sinyaller.append("Supertrend AYI ⚡🔴")

    # Hareketli Ortalamalar (±15)
    if fiyat and sma20:
        if fiyat > sma20: skor += 5; sinyaller.append(f"Fiyat > SMA20 ({sma20:,.2f} ₺) 🟢")
        else: skor -= 5; sinyaller.append(f"Fiyat < SMA20 ({sma20:,.2f} ₺) 🔴")
    if fiyat and sma50:
        if fiyat > sma50: skor += 5; sinyaller.append(f"Fiyat > SMA50 ({sma50:,.2f} ₺) 🟢")
        else: skor -= 5; sinyaller.append(f"Fiyat < SMA50 ({sma50:,.2f} ₺) 🔴")
    if fiyat and sma200:
        if fiyat > sma200: skor += 5; sinyaller.append(f"Fiyat > SMA200 — Uzun Vade Boğa 🟢")
        else: skor -= 5; sinyaller.append(f"Fiyat < SMA200 — Uzun Vade Ayı 🔴")

    # Bollinger Bands (±10)
    if bb_pct is not None:
        if bb_pct < 20:
            skor += 10; sinyaller.append(f"BB Alt Bandına Yakın (%{bb_pct}) — Aşırı Satım 🟢")
        elif bb_pct > 80:
            skor -= 10; sinyaller.append(f"BB Üst Bandına Yakın (%{bb_pct}) — Aşırı Alım 🔴")

    # Ichimoku (±10)
    if ich_t and ich_k and fiyat:
        if fiyat > ich_t and fiyat > ich_k:
            skor += 8; sinyaller.append("Fiyat Ichimoku Bulutunun Üstü — Güçlü Boğa 🌸🟢")
        elif fiyat < ich_t and fiyat < ich_k:
            skor -= 8; sinyaller.append("Fiyat Ichimoku Bulutunun Altı — Güçlü Ayı 🌸🔴")
        if ich_t > ich_k:
            skor += 2; sinyaller.append("Tenkan > Kijun — Boğa Kesişimi 🌸")
        elif ich_t < ich_k:
            skor -= 2; sinyaller.append("Tenkan < Kijun — Ayı Kesişimi 🌸")

    skor = max(0, min(100, round(skor)))

    if skor >= 70:   tavsiye = "🟢 GÜÇLÜ AL"
    elif skor >= 58: tavsiye = "🟢 AL"
    elif skor >= 45: tavsiye = "🟡 İZLE"
    elif skor >= 33: tavsiye = "🔴 SAT"
    else:            tavsiye = "🔴 GÜÇLÜ SAT"

    detay.update({
        "rsi": round(rsi, 2) if rsi else None,
        "macd": round(macd, 4) if macd else None,
        "macd_signal": round(macds, 4) if macds else None,
        "macd_hist": round(macdh, 4) if macdh else None,
        "sma20": round(sma20, 2) if sma20 else None,
        "sma50": round(sma50, 2) if sma50 else None,
        "sma200": round(sma200, 2) if sma200 else None,
        "ema20": round(ema20, 2) if ema20 else None,
        "bb_upper": round(bbu, 2) if bbu else None,
        "bb_middle": round(bbm, 2) if bbm else None,
        "bb_lower": round(bbl, 2) if bbl else None,
        "bb_pct": bb_pct,
        "supertrend": round(st_val, 2) if st_val else None,
        "supertrend_yon": "AL 🟢" if st_dir == 1 else "SAT 🔴",
        "ichimoku_tenkan": round(ich_t, 2) if ich_t else None,
        "ichimoku_kijun": round(ich_k, 2) if ich_k else None,
        "fibonacci": fibs,
        "skor": skor,
        "tavsiye": tavsiye,
        "sinyaller": sinyaller,
        "hata": None,
    })

    df.reset_index(inplace=True)
    detay["_df"] = df
    return detay
