"""
TürkFin AI — Fon Modülü v4
Kaynak: TEFAS API (tefas.gov.tr/api/funds)
"""

import time
from typing import Any, Dict, List, Optional

import requests

_TEFAS_BASE = "https://www.tefas.gov.tr/api/funds"
_HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://www.tefas.gov.tr/",
    "User-Agent": "Mozilla/5.0",
}
_CACHE: Dict[str, Any] = {}
_CACHE_TTL = 300  # 5 dakika

FON_TIPLERI = {
    "YAT": "Yatırım Fonu",
    "EMK": "Emeklilik Fonu",
    "BYF": "Borsa Yatırım Fonu",
}

FON_PERIYOTLARI = [
    ("getiri1a", "1A", 1),
    ("getiri3a", "3A", 3),
    ("getiri6a", "6A", 6),
    ("getiri1y", "1Y", 12),
    ("getiriyb", "YB", 0),  # yılbaşından beri (periyod yok)
    ("getiri3y", "3Y", 36),
    ("getiri5y", "5Y", 60),
]


# ---------------------------------------------------------------------------
# İç yardımcılar
# ---------------------------------------------------------------------------


def _post(endpoint: str, body: Dict) -> List[Dict]:
    """TEFAS API'ye POST atar; resultList listesini döner, hata varsa [] döner."""
    url = f"{_TEFAS_BASE}/{endpoint}"
    try:
        resp = requests.post(url, json=body, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("resultList") or []
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"[fon._post] {endpoint} hatası: {e}")
        return []


def _cache_get(key: str) -> Optional[Any]:
    """TTL'li cache'den değer okur; süresi geçmişse None döner."""
    entry = _CACHE.get(key)
    if entry is None:
        return None
    value, ts = entry
    if time.time() - ts > _CACHE_TTL:
        del _CACHE[key]
        return None
    return value


def _cache_set(key: str, val: Any) -> None:
    """Değeri TTL ile birlikte cache'e yazar."""
    _CACHE[key] = (val, time.time())


# ---------------------------------------------------------------------------
# Genel Fon Listesi
# ---------------------------------------------------------------------------


def get_fon_listesi(fon_tipi: str = "YAT") -> List[Dict]:
    """
    TEFAS fonGetiriBazliBilgiGetir endpoint'inden tüm fon listesini çeker.

    Returns:
        List[Dict] — her dict: kod, unvan, tur, getiri1a, getiri3a, getiri6a,
                               getiri1y, getiriyb, getiri3y, getiri5y, risk, tefas_durum
        Hata durumunda: [{"hata": "..."}]
    """
    cache_key = f"fon_listesi_{fon_tipi}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    body = {
        "dil": "TR",
        "fonTipi": fon_tipi,
        "kurucuKodu": None,
        "islem": 1,
        "donemGetiri1a": "1",
        "donemGetiri3a": "1",
        "donemGetiri6a": "1",
        "donemGetiri1y": "1",
        "donemGetiriyb": "1",
        "donemGetiri3y": "1",
        "donemGetiri5y": "1",
        "basTarih": None,
        "bitTarih": None,
        "calismaTipi": 2,
        "getiriOrani": "1",
    }

    raw = _post("fonGetiriBazliBilgiGetir", body)
    if not raw:
        return [{"hata": "fonGetiriBazliBilgiGetir endpoint'inden veri alınamadı."}]

    sonuc: List[Dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue

        # fonTurAciklama None-safe işleme
        tur_raw = item.get("fonTurAciklama")
        tur = str(tur_raw).strip() if tur_raw is not None else ""

        def _safe_float(val) -> Optional[float]:
            try:
                return float(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        sonuc.append(
            {
                "kod": item.get("fonKodu"),
                "unvan": item.get("fonUnvan"),
                "tur": tur,
                "getiri1a": _safe_float(item.get("getiri1a")),
                "getiri3a": _safe_float(item.get("getiri3a")),
                "getiri6a": _safe_float(item.get("getiri6a")),
                "getiri1y": _safe_float(item.get("getiri1y")),
                "getiriyb": _safe_float(item.get("getiriyb")),
                "getiri3y": _safe_float(item.get("getiri3y")),
                "getiri5y": _safe_float(item.get("getiri5y")),
                "risk": item.get("riskDegeri"),
                "tefas_durum": item.get("tefasDurum"),
            }
        )

    _cache_set(cache_key, sonuc)
    return sonuc


# ---------------------------------------------------------------------------
# Tek Fon Detay
# ---------------------------------------------------------------------------


def get_fon_detay(fon_kodu: str) -> Dict:
    """
    TEFAS fonBilgiGetir endpoint'inden tek fon detayını çeker.

    Returns:
        Dict — kod, unvan, son_fiyat, gunluk_getiri, port_buyukluk, kategori,
                derece, sayi, yatirimci, pazar_payi, hata
    """
    fon_kodu = (fon_kodu or "").strip().upper()
    if not fon_kodu:
        return {"hata": "Fon kodu boş olamaz."}

    cache_key = f"fon_detay_{fon_kodu}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    raw = _post("fonBilgiGetir", {"fonKodu": fon_kodu})

    if not raw:
        result = {
            "kod": fon_kodu,
            "unvan": None,
            "son_fiyat": None,
            "gunluk_getiri": None,
            "port_buyukluk": None,
            "kategori": None,
            "derece": None,
            "sayi": None,
            "yatirimci": None,
            "pazar_payi": None,
            "hata": f"'{fon_kodu}' için veri alınamadı.",
        }
        return result

    item = raw[0] if isinstance(raw[0], dict) else {}

    def _safe_float(val) -> Optional[float]:
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    result = {
        "kod": item.get("fonKodu", fon_kodu),
        "unvan": item.get("fonUnvan"),
        "son_fiyat": _safe_float(item.get("sonFiyat")),
        "gunluk_getiri": _safe_float(item.get("gunlukGetiri")),
        "port_buyukluk": _safe_float(item.get("portBuyukluk")),
        "kategori": item.get("fonKategori"),
        "derece": item.get("kategoriDerece"),
        "sayi": item.get("kategoriFonSay"),
        "yatirimci": item.get("yatirimciSayi"),
        "pazar_payi": _safe_float(item.get("pazarPayi")),
        "hata": None,
    }

    _cache_set(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Tek Fon Fiyat Geçmişi
# ---------------------------------------------------------------------------


def get_fon_fiyat_gecmis(fon_kodu: str, periyod: int = 12) -> List[Dict]:
    """
    TEFAS fonFiyatBilgiGetir endpoint'inden fiyat geçmişini çeker.

    Args:
        fon_kodu: Fon kodu (örn. 'YAC')
        periyod:  1=1ay, 3=3ay, 6=6ay, 12=1yil, 36=3yil, 60=5yil

    Returns:
        List[Dict] — Lightweight Charts formatında, tarihe göre sıralı,
                     duplicate temizlenmiş: [{"time": "YYYY-MM-DD", "value": float}, ...]
        Hata durumunda: [{"hata": "..."}]
    """
    fon_kodu = (fon_kodu or "").strip().upper()
    if not fon_kodu:
        return [{"hata": "Fon kodu boş olamaz."}]

    cache_key = f"fon_fiyat_{fon_kodu}_{periyod}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    raw = _post(
        "fonFiyatBilgiGetir", {"fonKodu": fon_kodu, "dil": "TR", "periyod": periyod}
    )

    if not raw:
        return [
            {"hata": f"'{fon_kodu}' için fiyat geçmişi alınamadı (periyod={periyod})."}
        ]

    sonuc: List[Dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue

        tarih_raw = item.get("tarih")
        fiyat_raw = item.get("fiyat")

        if tarih_raw is None or fiyat_raw is None:
            continue

        # Tarih formatı "YYYY-MM-DDT..." veya "YYYY-MM-DD" olabilir
        tarih_str = str(tarih_raw)[:10]

        try:
            fiyat = float(fiyat_raw)
        except (ValueError, TypeError):
            continue

        sonuc.append({"time": tarih_str, "value": round(fiyat, 6)})

    # Tarihe göre sırala, duplicate temizle
    sonuc.sort(key=lambda x: x["time"])
    seen: set = set()
    temiz: List[Dict] = []
    for p in sonuc:
        if p["time"] not in seen:
            seen.add(p["time"])
            temiz.append(p)

    _cache_set(cache_key, temiz)
    return temiz
