"""
TürkFin AI — Teknik Analiz Motoru v4.3
Düzeltmeler:
1. tz_localize(None) → tz_convert(None)  [timezone crash fix]
2. Duplicate timestamp deduplication      [LightweightCharts crash fix]
3. Series timestamps candle listesiyle eşleşiyor [indikatör görünmeme fix]
4. Ichimoku kolon adı tespiti düzeltildi
5. Hacim renk bilgisi eklendi
6. borsapy fallback: yfinance boş/bozuk dönünce borsapy.Ticker.history() kullanılır
   (GMSTR, GLDTR, ZPX30, ALTIN gibi ETF/BYF hisseleri için kritik)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import borsapy as bp
import pandas as pd
import pandas_ta as ta
import yfinance as yf

INTERVAL_MAP = {
    "5m": ("60d", "5m", None, "5 Dak."),
    "15m": ("60d", "15m", None, "15 Dak."),
    "30m": ("120d", "30m", None, "30 Dak."),
    "45m": ("120d", "15m", "45min", "45 Dak."),
    "1h": ("730d", "1h", None, "1 Saat"),
    "2h": ("730d", "1h", "2h", "2 Saat"),
    "4h": ("730d", "1h", "4h", "4 Saat"),
    "1d": ("3y", "1d", None, "Günlük"),
    "1wk": ("5y", "1wk", None, "Haftalık"),
    "1mo": ("max", "1mo", None, "Aylık"),
}

# borsapy fallback için interval → (period, interval) eşleşmesi
# yfinance period formatları borsapy'de desteklenmeyebilir, bu yüzden ayrı tablo
_BORSAPY_INTERVAL_MAP = {
    "5m": ("1mo", "5m"),
    "15m": ("3mo", "15m"),
    "30m": ("3mo", "30m"),
    "45m": ("3mo", "30m"),  # borsapy 45m yok, 30m kullan sonra resample
    "1h": ("6mo", "1h"),
    "2h": ("6mo", "1h"),  # borsapy 2h yok, 1h kullan sonra resample
    "4h": ("6mo", "1h"),  # borsapy 4h yok, 1h kullan sonra resample
    "1d": ("max", "1d"),
    "1wk": ("max", "1wk"),
    "1mo": ("max", "1mo"),
}
DEFAULT_INTERVAL = "1d"
PERIOD_MAP = INTERVAL_MAP
VARSAYILAN_PERIOD = DEFAULT_INTERVAL
INTRADAY_INTERVALS = {"5m", "15m", "30m", "45m", "1h", "2h", "4h"}


@dataclass
class TeknikSonuc:
    sembol: str
    fiyat: Optional[float]
    degisim: Optional[float]
    hacim: Optional[int]
    acilis: Optional[float]
    yuksek: Optional[float]
    dusuk: Optional[float]
    onceki_kapanis: Optional[float]
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_yuzde: Optional[float] = None
    bb_genislik: Optional[float] = None
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    ema20: Optional[float] = None
    hacim_ort20: Optional[float] = None
    hacim_oran: Optional[float] = None
    destek: Optional[float] = None
    direnc: Optional[float] = None
    supertrend: Optional[float] = None
    ichimoku_kijun: Optional[float] = None
    skor: int = 50
    tavsiye: str = "🟡 İZLE"
    sinyaller: List[str] = field(default_factory=list)
    df: Optional[pd.DataFrame] = None
    interval: str = DEFAULT_INTERVAL
    hata: Optional[str] = None


def _is_bad_yf_data(df: pd.DataFrame) -> bool:
    """yfinance'den gelen verinin bozuk/yetersiz olup olmadığını kontrol eder.

    Bozuk sayma kriterleri:
    - DataFrame boş
    - Sadece 1 satır var (anlamsız grafik)
    - Tüm Volume değerleri 0
    - Volume>0 olan satır oranı < %30  (GMSTR 1wk: 8/262, 1mo: 131/219 gibi)
    - Son 10 satırın tamamında Volume=0  (en son veri donmuş)
    - Close değerleri tekdüze (değişim yok) ve satır sayısı > 5
    """
    if df is None or df.empty:
        return True
    if len(df) <= 1:
        return True
    if "Volume" in df.columns:
        vol = df["Volume"]
        # Tümü sıfır
        if (vol == 0).all():
            return True
        # Gerçek (Volume>0) satır oranı %30'un altındaysa sahte veri
        real_ratio = (vol > 0).sum() / len(vol)
        if real_ratio < 0.30:
            return True
        # Son 10 satırın tamamı Volume=0 ise en güncel veri donmuş demektir
        tail_n = min(10, len(vol))
        if (vol.iloc[-tail_n:] == 0).all():
            return True
    # Close tamamen aynı ve 5'ten fazla satır varsa bozuk
    if len(df) > 5 and df["Close"].nunique() <= 1:
        return True
    return False


def _fetch_borsapy(sembol: str, interval: str, resample_rule) -> pd.DataFrame:
    """borsapy.Ticker.history() ile veri çeker. Timezone'u kaldırır."""
    try:
        bp_period, bp_interval = _BORSAPY_INTERVAL_MAP.get(interval, ("max", "1d"))
        t = bp.Ticker(sembol)
        df = t.history(period=bp_period, interval=bp_interval)
        if df is None or df.empty:
            return pd.DataFrame()
        # Timezone'u kaldır (DatetimeTZDtype → DatetimeIndex)
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
        df.columns = [c.capitalize() for c in df.columns]
        # Gerekirse resample (45m, 2h, 4h için)
        if resample_rule:
            df = (
                df.resample(resample_rule)
                .agg(
                    {
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last",
                        "Volume": "sum",
                    }
                )
                .dropna(subset=["Close"])
            )
        print(f"borsapy fallback [{sembol}|{interval}]: {len(df)} satır")
        return df
    except Exception as e:
        print(f"borsapy fallback [{sembol}|{interval}]: {e}")
        return pd.DataFrame()


def _fetch(sembol, yf_period, yf_interval, resample_rule, interval="1d"):
    # Önce yfinance'i dene
    try:
        df = yf.download(
            f"{sembol}.IS",
            period=yf_period,
            interval=yf_interval,
            progress=False,
            auto_adjust=True,
        )
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            df.columns = [c.capitalize() for c in df.columns]
            if resample_rule:
                df = (
                    df.resample(resample_rule)
                    .agg(
                        {
                            "Open": "first",
                            "High": "max",
                            "Low": "min",
                            "Close": "last",
                            "Volume": "sum",
                        }
                    )
                    .dropna(subset=["Close"])
                )
            # Veri kalitesini kontrol et; bozuksa borsapy'ye geç
            if not _is_bad_yf_data(df):
                return df
            print(
                f"yfinance [{sembol}|{yf_interval}]: bozuk/yetersiz veri, borsapy fallback"
            )
    except Exception as e:
        print(f"yfinance [{sembol}|{yf_interval}]: {e}")

    # borsapy fallback
    return _fetch_borsapy(sembol, interval, resample_rule)


def _skor(sonuc):
    s = 50
    sig = []
    if sonuc.rsi is not None:
        if sonuc.rsi < 30:
            s += 20
            sig.append("✅ RSI aşırı satım (<30)")
        elif sonuc.rsi < 45:
            s += 10
            sig.append("📊 RSI zayıf bölge (30-45)")
        elif sonuc.rsi < 60:
            sig.append("➡️ RSI nötr (45-60)")
        elif sonuc.rsi < 70:
            s -= 10
            sig.append("⚠️ RSI güçlü bölge (60-70)")
        else:
            s -= 20
            sig.append("🔴 RSI aşırı alım (>70)")
    if sonuc.macd is not None and sonuc.macd_signal is not None:
        if sonuc.macd > sonuc.macd_signal:
            s += 15
            sig.append("✅ MACD sinyal üzerinde")
        else:
            s -= 15
            sig.append("🔴 MACD sinyal altında")
        if sonuc.macd_hist and sonuc.macd_hist > 0:
            s += 5
            sig.append("✅ MACD histogramı pozitif")
        elif sonuc.macd_hist:
            s -= 5
            sig.append("⚠️ MACD histogramı negatif")
    if sonuc.bb_yuzde is not None:
        if sonuc.bb_yuzde < 20:
            s += 15
            sig.append("✅ Bollinger alt banda yakın")
        elif sonuc.bb_yuzde > 80:
            s -= 15
            sig.append("🔴 Bollinger üst banda yakın")
        else:
            sig.append(f"➡️ Bollinger orta bölge (%{sonuc.bb_yuzde:.0f})")
    if sonuc.fiyat and sonuc.sma20:
        if sonuc.fiyat > sonuc.sma20:
            s += 8
            sig.append("✅ Fiyat SMA20 üzerinde")
        else:
            s -= 8
            sig.append("⚠️ Fiyat SMA20 altında")
    if sonuc.sma20 and sonuc.sma50:
        if sonuc.sma20 > sonuc.sma50:
            s += 10
            sig.append("✅ SMA20>SMA50 (Altın Kesişim)")
        else:
            s -= 10
            sig.append("⚠️ SMA20<SMA50 (Ölüm Kesişim)")
    if sonuc.fiyat and sonuc.sma200:
        if sonuc.fiyat > sonuc.sma200:
            s += 8
            sig.append("✅ Fiyat SMA200 üzerinde")
        else:
            s -= 8
            sig.append("🔴 Fiyat SMA200 altında")
    if sonuc.supertrend and sonuc.fiyat:
        if sonuc.fiyat > sonuc.supertrend:
            s += 10
            sig.append("✅ Fiyat SuperTrend üzerinde (yükseliş)")
        else:
            s -= 10
            sig.append("🔴 Fiyat SuperTrend altında (düşüş)")
    s = max(0, min(100, s))
    return s, ("🟢 AL" if s >= 65 else "🔴 SAT" if s <= 40 else "🟡 İZLE"), sig


def _info_val(info: dict, *keys):
    for k in keys:
        v = info.get(k)
        if v is not None and v != "" and not (isinstance(v, float) and pd.isna(v)):
            return v
    return None


def _fill_live_from_df(sonuc: TeknikSonuc, df: pd.DataFrame) -> None:
    """borsapy canlı fiyat vermezse Yahoo mum verisinden doldur."""
    if df is None or df.empty:
        return
    last, prev = df.iloc[-1], df.iloc[-2] if len(df) >= 2 else None
    close = float(last["Close"])
    if sonuc.fiyat is None:
        sonuc.fiyat = round(close, 2)
    if sonuc.degisim is None and prev is not None:
        pclose = float(prev["Close"])
        if pclose:
            sonuc.degisim = round((close - pclose) / pclose * 100, 2)
    if sonuc.hacim is None and "Volume" in last and pd.notna(last["Volume"]):
        try:
            sonuc.hacim = int(float(last["Volume"]))
        except (TypeError, ValueError):
            pass
    if sonuc.acilis is None and pd.notna(last.get("Open")):
        sonuc.acilis = round(float(last["Open"]), 2)
    if sonuc.yuksek is None and pd.notna(last.get("High")):
        sonuc.yuksek = round(float(last["High"]), 2)
    if sonuc.dusuk is None and pd.notna(last.get("Low")):
        sonuc.dusuk = round(float(last["Low"]), 2)
    if (
        sonuc.onceki_kapanis is None
        and prev is not None
        and pd.notna(prev.get("Close"))
    ):
        sonuc.onceki_kapanis = round(float(prev["Close"]), 2)


def teknik_analiz(sembol, interval=DEFAULT_INTERVAL):
    sembol = sembol.upper().strip()
    yf_period, yf_interval, resample_rule, _ = INTERVAL_MAP.get(
        interval, INTERVAL_MAP[DEFAULT_INTERVAL]
    )
    try:
        info = bp.Ticker(sembol).info or {}
        sonuc = TeknikSonuc(
            sembol=sembol,
            interval=interval,
            fiyat=_info_val(
                info, "last", "Last", "close", "Close", "regularMarketPrice"
            ),
            degisim=_info_val(
                info, "change_percent", "changePercent", "regularMarketChangePercent"
            ),
            hacim=_info_val(info, "volume", "Volume", "regularMarketVolume"),
            acilis=_info_val(info, "open", "Open", "regularMarketOpen"),
            yuksek=_info_val(info, "high", "High", "regularMarketDayHigh"),
            dusuk=_info_val(info, "low", "Low", "regularMarketDayLow"),
            onceki_kapanis=_info_val(
                info, "prev_close", "previousClose", "regularMarketPreviousClose"
            ),
        )
    except Exception:
        sonuc = TeknikSonuc(
            sembol=sembol,
            interval=interval,
            fiyat=None,
            degisim=None,
            hacim=None,
            acilis=None,
            yuksek=None,
            dusuk=None,
            onceki_kapanis=None,
        )

    df = _fetch(sembol, yf_period, yf_interval, resample_rule, interval)
    if df.empty:
        sonuc.hata = "Tarihsel veri alınamadı"
        return sonuc
    _fill_live_from_df(sonuc, df)
    n = len(df)

    df["RSI"] = ta.rsi(df["Close"], length=14)
    m = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    if m is not None:
        df = pd.concat([df, m], axis=1)
    b = ta.bbands(df["Close"], length=20, std=2)
    if b is not None:
        df = pd.concat([df, b], axis=1)

    df["SMA_20"] = ta.sma(df["Close"], length=min(20, n - 1))
    df["EMA_20"] = ta.ema(df["Close"], length=min(20, n - 1))
    if n >= 50:
        df["SMA_50"] = ta.sma(df["Close"], length=50)
    if n >= 200:
        df["SMA_200"] = ta.sma(df["Close"], length=200)

    # SuperTrend
    try:
        st = ta.supertrend(df["High"], df["Low"], df["Close"], length=10, multiplier=3)
        if st is not None:
            df = pd.concat([df, st], axis=1)
    except:
        pass

    # Ichimoku
    try:
        ich, _ = ta.ichimoku(df["High"], df["Low"], df["Close"])
        if ich is not None:
            df = pd.concat([df, ich], axis=1)
    except:
        pass

    df["VOL_MA20"] = df["Volume"].rolling(min(20, n - 1)).mean()

    last = df.iloc[-1]

    def safe(col, dec=2):
        v = last.get(col)
        return round(float(v), dec) if v is not None and pd.notna(v) else None

    sonuc.rsi = safe("RSI")
    sonuc.macd = safe("MACD_12_26_9")
    sonuc.macd_signal = safe("MACDs_12_26_9")
    sonuc.macd_hist = safe("MACDh_12_26_9")

    bbl = [c for c in df.columns if c.startswith("BBL")]
    bbm = [c for c in df.columns if c.startswith("BBM")]
    bbu = [c for c in df.columns if c.startswith("BBU")]
    if bbl:
        sonuc.bb_lower = safe(bbl[0])
        sonuc.bb_middle = safe(bbm[0])
        sonuc.bb_upper = safe(bbu[0])
        if sonuc.bb_upper and sonuc.bb_lower and sonuc.fiyat is not None:
            r = sonuc.bb_upper - sonuc.bb_lower
            if r > 0:
                sonuc.bb_yuzde = round((sonuc.fiyat - sonuc.bb_lower) / r * 100, 1)
                sonuc.bb_genislik = (
                    round(r / sonuc.bb_middle * 100, 2) if sonuc.bb_middle else None
                )

    sonuc.sma20 = safe("SMA_20")
    sonuc.ema20 = safe("EMA_20")
    sonuc.sma50 = safe("SMA_50") if "SMA_50" in df.columns else None
    sonuc.sma200 = safe("SMA_200") if "SMA_200" in df.columns else None

    st_col = [
        c
        for c in df.columns
        if c.startswith("SUPERT_")
        and not c.startswith("SUPERTd_")
        and not c.startswith("SUPERTl_")
        and not c.startswith("SUPERTs_")
    ]
    if st_col:
        sonuc.supertrend = safe(st_col[0])

    # Ichimoku Kijun-sen (IKS_ prefix)
    ich_col = [c for c in df.columns if c.startswith("IKS_")]
    if ich_col:
        sonuc.ichimoku_kijun = safe(ich_col[0])

    vm = safe("VOL_MA20", 0)
    if vm and sonuc.hacim:
        sonuc.hacim_ort20 = vm
        sonuc.hacim_oran = round(sonuc.hacim / vm, 2)
    recent = df.tail(20)
    sonuc.destek = round(float(recent["Low"].min()), 2)
    sonuc.direnc = round(float(recent["High"].max()), 2)
    sonuc.skor, sonuc.tavsiye, sonuc.sinyaller = _skor(sonuc)
    sonuc.df = df
    return sonuc


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# df_to_chart_json — 3 kritik düzeltme
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def df_to_chart_json(df, interval="1d") -> Dict[str, Any]:
    df = df.dropna(subset=["Close"])
    is_intra = interval in INTRADAY_INTERVALS

    # ── DÜZELTİLMİŞ: tz_localize(None) → tz_convert(None) ────────────────────
    # tz_localize(None) timezone-aware datetime'da TypeError fırlatır.
    # tz_convert(None) UTC'ye çevirip timezone bilgisini kaldırır.
    def ts(idx):
        dt = pd.to_datetime(idx)
        if getattr(dt, "tzinfo", None) is not None:
            dt = dt.tz_convert(None)  # ← kritik düzeltme
        return int(dt.timestamp()) if is_intra else dt.strftime("%Y-%m-%d")

    # ── DÜZELTİLMİŞ: Duplicate timestamp deduplication ───────────────────────
    # LightweightCharts aynı time değerine sahip iki nokta görürse
    # tüm seriyi sessizce çizer veya crash yapar.
    seen = set()
    clean_rows = []
    for idx, row in df.iterrows():
        o = row.get("Open")
        h = row.get("High")
        l = row.get("Low")
        c = row.get("Close")
        if any(pd.isna(x) for x in [o, h, l, c]):
            continue
        t = ts(idx)
        if t in seen:
            continue  # ← duplicate'i atla
        seen.add(t)
        clean_rows.append((t, row))

    candles = [
        {
            "time": t,
            "open": round(float(r["Open"]), 4),
            "high": round(float(r["High"]), 4),
            "low": round(float(r["Low"]), 4),
            "close": round(float(r["Close"]), 4),
        }
        for t, r in clean_rows
    ]

    vol_col = [c for c in df.columns if c.lower() == "volume"]
    volume = []
    for t, r in clean_rows:
        if not vol_col:
            continue
        v = r.get(vol_col[0])
        if v is None or pd.isna(v):
            continue
        try:
            raw = str(v).strip().split(".")[0]
            volume.append({"time": t, "value": int(raw) if raw.isdigit() else 0})
        except Exception:
            volume.append({"time": t, "value": 0})

    try:
        df["ichi_tenkan"] = (
            df["High"].rolling(9).max() + df["Low"].rolling(9).min()
        ) / 2
        df["ichi_kijun"] = (
            df["High"].rolling(26).max() + df["Low"].rolling(26).min()
        ) / 2
        df["ichi_spanA"] = ((df["ichi_tenkan"] + df["ichi_kijun"]) / 2).shift(26)
        df["ichi_spanB"] = (
            (df["High"].rolling(52).max() + df["Low"].rolling(52).min()) / 2
        ).shift(26)
        for c in ("ichi_tenkan", "ichi_kijun", "ichi_spanA", "ichi_spanB"):
            df[c] = df[c].bfill()
    except Exception as e:
        print("Ichimoku hesaplama hatası:", e)

    result = {"candles": candles, "volume": volume, "interval": interval}

    # ── DÜZELTİLMİŞ: Series extraction — candle ile aynı timestamp listesi ──
    # Önceki kod df.items() ile TÜM satırları tarıyordu, atlanmış
    # (NaN/duplicate) satırların zamanları da seriye giriyordu.
    # Bu timestamps uyuşmazlığı indikatörlerin görünmemesine yol açıyordu.
    valid_times = {t for t, _ in clean_rows}  # sadece geçerli zaman damgaları

    def series(col):
        """Sadece candle listesiyle eşleşen timestamp'leri döner."""
        if col not in df.columns:
            return []
        out = []
        for idx, row in df.iterrows():
            t = ts(idx)
            if t not in valid_times:
                continue
            v = row.get(col)
            if v is None or pd.isna(v):
                continue
            out.append({"time": t, "value": round(float(v), 4)})
        return out

    def series_by_prefix(prefix):
        """Prefix ile başlayan ilk kolonu bulup series() ile döner."""
        col = [c for c in df.columns if c.startswith(prefix)]
        return series(col[0]) if col else []

    # Standart indikatörler
    result["RSI"] = series("RSI")
    result["SMA_20"] = series("SMA_20")
    result["SMA_50"] = series("SMA_50") if "SMA_50" in df.columns else []
    result["SMA_200"] = series("SMA_200") if "SMA_200" in df.columns else []
    result["EMA_20"] = series("EMA_20")

    # MACD — kesin kolon adları ile
    macd_col = [c for c in df.columns if c.startswith("MACD_12")]
    macds_col = [c for c in df.columns if c.startswith("MACDs_12")]
    macdh_col = [c for c in df.columns if c.startswith("MACDh_12")]
    result["MACD_12_26_9"] = series(macd_col[0]) if macd_col else []
    result["MACDs_12_26_9"] = series(macds_col[0]) if macds_col else []
    result["MACDh_12_26_9"] = series(macdh_col[0]) if macdh_col else []

    # Bollinger Bands
    bbl = [c for c in df.columns if c.startswith("BBL")]
    bbm = [c for c in df.columns if c.startswith("BBM")]
    bbu = [c for c in df.columns if c.startswith("BBU")]
    if bbl:
        result["BB_lower"] = series(bbl[0])
        result["BB_middle"] = series(bbm[0])
        result["BB_upper"] = series(bbu[0])

    # SuperTrend — sadece ana değer kolonu (d/l/s değil)
    st_col = [
        c
        for c in df.columns
        if c.startswith("SUPERT_")
        and not any(c.startswith(x) for x in ["SUPERTd_", "SUPERTl_", "SUPERTs_"])
    ]
    if st_col:
        result["SUPERTREND"] = series(st_col[0])

    result["ichi_tenkan"] = series("ichi_tenkan")
    result["ichi_kijun"] = series("ichi_kijun")
    result["ichi_spanA"] = series("ichi_spanA")
    result["ichi_spanB"] = series("ichi_spanB")

    return result
