"""
TürkFin AI — Temettü Modülü
Kaynak 1: yfinance (BIST .IS suffix)
Kaynak 2: temettuhisseleri.com (scraper)
"""

import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional
from functools import lru_cache
from datetime import datetime, timedelta
import json
import os


# ── Yfinance: Geçmiş Temettü ──────────────────────────────────────────────────
def get_temettu_gecmis(sembol: str) -> List[Dict]:
    """
    Yfinance üzerinden BIST hissesinin temettü geçmişini döner.
    Örnek çıktı: [{"tarih": "2024-05-15", "tutar": 3.5, "verim_yuzde": None}]
    """
    try:
        ticker = yf.Ticker(f"{sembol.upper()}.IS")
        divs = ticker.dividends
        if divs is None or divs.empty:
            return []

        # Güncel fiyat (verim hesabı için)
        try:
            info = ticker.fast_info
            guncel_fiyat = info.last_price
        except:
            guncel_fiyat = None

        sonuclar = []
        for tarih, tutar in divs.items():
            tutar_f = round(float(tutar), 4)
            verim = round(tutar_f / guncel_fiyat * 100, 2) if guncel_fiyat else None
            sonuclar.append({
                "tarih": str(tarih)[:10],
                "tutar": tutar_f,
                "verim_yuzde": verim,
            })

        return sorted(sonuclar, key=lambda x: x["tarih"], reverse=True)[:20]
    except Exception as e:
        return []


def get_temettu_ozet(sembol: str) -> Dict:
    """Kart ve detay sayfası için özet temettü bilgisi"""
    gecmis = get_temettu_gecmis(sembol)
    if not gecmis:
        return {
            "son_temettu": "Veri yok",
            "toplam_5y": None,
            "ortalama_verim": None,
            "odeme_sayisi": 0,
            "gecmis": [],
        }

    son = gecmis[0]
    son_5y = [t for t in gecmis if t["tarih"] >= str(datetime.now().year - 5)]
    toplam = round(sum(t["tutar"] for t in son_5y), 2)
    verimler = [t["verim_yuzde"] for t in gecmis if t["verim_yuzde"]]
    ort_verim = round(sum(verimler) / len(verimler), 2) if verimler else None

    return {
        "son_temettu": f"{son['tarih']} — {son['tutar']} TL",
        "son_tutar": son["tutar"],
        "son_tarih": son["tarih"],
        "toplam_5y": toplam,
        "ortalama_verim": ort_verim,
        "odeme_sayisi": len(gecmis),
        "gecmis": gecmis[:10],
    }


# ── temettuhisseleri.com: Yaklaşan Takvim ────────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}


import time

_CACHE = {
    "ts": 0,
    "data": None
}

CACHE_TTL = 60 * 60 * 24 * 15  # 15 gün


def _fetch_dashboard_data() -> Dict:
    """Backend API'den verileri çeker ve 15 günlük cache kullanır."""
    now = time.time()

    if _CACHE["data"] and now - _CACHE["ts"] < CACHE_TTL:
        return _CACHE["data"]

    try:
        res = requests.get(
            "https://temettuhisseleri.com/backend/getdashboard.php",
            headers=_HEADERS,
            timeout=15,
        )
        data = res.json()
        _CACHE["data"] = data
        _CACHE["ts"] = now
        return data
    except Exception as e:
        print(f"API hatası: {e}")
        return _CACHE["data"] if _CACHE["data"] else {}


def get_yaklasan_temettular() -> List[Dict]:
    """
    temettuhisseleri.com backend API'sinden yaklaşan temettü tarihlerini çeker.
    """
    data = _fetch_dashboard_data()
    if not data or "futuredividends" not in data:
        return []

    sonuclar = []
    for item in data["futuredividends"]:
        tarih = f"{item['year']}-{item['month']:02d}-{item['day']:02d}"
        sonuclar.append({
            "hisse": item["ticker"],
            "Temettü Tarihi": tarih,
            "Temettü": f"{item['amount']} TL"
        })

    # Tarihe göre sırala
    return sorted(sonuclar, key=lambda x: x["Temettü Tarihi"])[:20]


def get_ana_ekran_verileri() -> Dict:
    """
    Ana ekran için temettü şampiyonları ve yaklaşan tarihleri döndürür.
    Bu veriler 15 günde bir güncellenir.
    """
    sampiyonlar = get_temettu_sampiyonlari(limit=10, period="5y")
    tarihler = get_yaklasan_temettular()
    
    return {
        "sampiyonlar": sampiyonlar,
        "tarihler": tarihler,
        "son_guncelleme": datetime.fromtimestamp(_CACHE["ts"]).strftime("%Y-%m-%d %H:%M") if _CACHE["ts"] else "Henüz güncellenmedi"
    }


def get_hisse_temettu_sayfasi(sembol: str) -> Dict:
    """
    temettuhisseleri.com/{sembol.lower()} sayfasından
    hisse özelinde temettü verisi çekmeyi dener.
    Site JS-rendered olduğundan server-side kısımları parse eder.
    """
    try:
        url = f"https://temettuhisseleri.com/hisse/{sembol.lower()}/"
        res = requests.get(url, headers=_HEADERS, timeout=12)
        soup = BeautifulSoup(res.text, "html.parser")

        # Sayfa başlığından hisse adını al
        baslik = soup.find("h1")
        sirket_adi = baslik.get_text(strip=True) if baslik else sembol

        # Olası JSON-LD verisini dene
        import json
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if data:
                    return {"kaynak": "json-ld", "data": data, "sirket": sirket_adi}
            except:
                pass

        return {"kaynak": "html", "sirket": sirket_adi, "not": "Veri JS ile yükleniyor"}
    except Exception as e:
        return {"hata": str(e)}
def get_temettu_sampiyonlari(limit: int = 10, period: str = "5y") -> List[Dict]:
    """
    temettuhisseleri.com backend API'sinden temettü şampiyonlarını çeker.
    
    Args:
        limit: Dönecek hisse sayısı
        period: 'year', '5y', veya '10y' - hangi dönem için şampiyonlar
    """
    data = _fetch_dashboard_data()
    if not data:
        return []

    champions_key = f"champions_{period}"
    if champions_key not in data:
        champions_key = "champions_5y"  # Varsayılan
    
    if champions_key not in data:
        return []

    sonuclar = []
    for item in data[champions_key]:
        toplam = float(item["totaldividend"])
        # API verim yüzdesi sağlamıyor, toplam temettüyü kullanıyoruz
        sonuclar.append({
            "sembol": item["ticker"],
            "verim": toplam,  # Toplam temettü verim olarak kullanılıyor
            "toplam_5y": toplam,
            "son_temettu": f"{period} dönemi: {toplam} TL"
        })

    return sonuclar[:limit]


# ── Temettü Takip Listesi ─────────────────────────────────────────────────────
_TAKIP_LISTE_DOSYA = "temettu_takip_listesi.json"

def _get_takip_listesi_dosya() -> str:
    """Takip listesi dosya yolunu döndürür."""
    return os.path.join(os.path.dirname(__file__), _TAKIP_LISTE_DOSYA)

def get_temettu_takip_listesi() -> List[str]:
    """Temettü takip listesini döndürür."""
    dosya = _get_takip_listesi_dosya()
    if not os.path.exists(dosya):
        return []
    try:
        with open(dosya, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("hisseler", [])
    except:
        return []

def ekle_takip_listesi(sembol: str) -> bool:
    """Takip listesine hisse ekler."""
    sembol = sembol.upper()
    liste = get_temettu_takip_listesi()
    if sembol in liste:
        return False
    liste.append(sembol)
    try:
        dosya = _get_takip_listesi_dosya()
        with open(dosya, 'w', encoding='utf-8') as f:
            json.dump({"hisseler": liste}, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def cikar_takip_listesi(sembol: str) -> bool:
    """Takip listesinden hisse çıkarır."""
    sembol = sembol.upper()
    liste = get_temettu_takip_listesi()
    if sembol not in liste:
        return False
    liste.remove(sembol)
    try:
        dosya = _get_takip_listesi_dosya()
        with open(dosya, 'w', encoding='utf-8') as f:
            json.dump({"hisseler": liste}, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


def get_temettu_ucuzluk_skoru(sembol: str) -> Optional[str]:
    """Hisse için temettü ucuzluk skorunu döndürür."""
    data = _fetch_dashboard_data()
    if not data or "cheapdividendstocks" not in data:
        return None
    
    for item in data["cheapdividendstocks"]:
        if item["ticker"].upper() == sembol.upper():
            return "Listede"  # API sadece ticker veriyor, listede olduğunu gösteriyoruz
    return None


def get_amorti_suresi(sembol: str) -> Optional[str]:
    """Hisse için amorti süresini döndürür."""
    data = _fetch_dashboard_data()
    if not data or "amortistocks" not in data:
        return None
    
    for item in data["amortistocks"]:
        if item["ticker"].upper() == sembol.upper():
            return "Listede"  # API sadece ticker veriyor, listede olduğunu gösteriyoruz
    return None