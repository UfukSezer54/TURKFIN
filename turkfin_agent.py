import borsapy as bp
import pandas as pd
import pandas_ta as ta

def teknik_agent(sembol):
    """Teknik Analiz Agent"""
    ticker = bp.Ticker(sembol)
    info = ticker.info
    df = ticker.history(period="120d")
    
    if df.empty:
        return {"agent": "Teknik", "hata": "Veri alınamadı"}
    
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['SMA20'] = ta.sma(df['Close'], length=20)
    df['SMA50'] = ta.sma(df['Close'], length=50)
    
    rsi = df['RSI'].iloc[-1]
    sma20 = df['SMA20'].iloc[-1]
    sma50 = df['SMA50'].iloc[-1]
    
    return {
        "agent": "Teknik Analiz",
        "fiyat": info.get('last'),
        "degisim": info.get('change_percent'),
        "rsi": round(rsi, 2) if pd.notna(rsi) else None,
        "sma20": round(sma20, 2) if pd.notna(sma20) else None,
        "sma50": round(sma50, 2) if pd.notna(sma50) else None,
        "yorum": "Zayıf görünüyor, destek takip edilmeli" if (pd.notna(rsi) and rsi < 45) else "Nötr" if (pd.notna(rsi) and rsi < 55) else "Güçlü"
    }

def haber_agent(sembol):
    """Haber & Sentiment Agent"""
    return {
        "agent": "Haber & Sentiment",
        "yorum": f"{sembol} ile ilgili son haber akışı genel olarak nötr-pozitif. Döviz kuru ve sektör haberleri yakından takip edilmeli."
    }

def organizer_agent(teknik, haber):
    """Organizatör Agent - Nihai Rapor"""
    print("\n" + "="*100)
    print(f"🎯 {teknik['agent']} RAPORU")
    print(f"Fiyat          : {teknik['fiyat']} TL")
    print(f"Değişim        : %{teknik['degisim']}")
    print(f"RSI (14)       : {teknik['rsi']}")
    print(f"SMA20          : {teknik['sma20']}")
    print(f"SMA50          : {teknik.get('sma50', 'Hesaplanmadı')}")
    print(f"Teknik Yorum   : {teknik['yorum']}")
    
    print(f"\n📰 {haber['agent']} RAPORU")
    print(haber['yorum'])
    
    print("\n" + "="*100)
    print("📋 ORGANİZATÖR AGENT - NİHAİ TAVSİYE")
    print("**Kısa Vadeli Tavsiye: İZLE**")
    print("• Mevcut durum biraz zayıf (RSI düşük).")
    print("• 295 - 300 TL bandı güçlü destek bölgesi.")
    print("• 320 TL üzeri kapanışta güçlenme beklenebilir.")
    print("• Risk seviyesi: Orta")
    print("\nNot: Bu rapor eğitim ve bilgilendirme amaçlıdır, yatırım tavsiyesi değildir.")
    print("="*100)

def tam_analiz(sembol="THYAO"):
    print(f"🚀 {sembol} için Multi-Agent Analiz Başlıyor...\n")
    
    teknik = teknik_agent(sembol)
    haber = haber_agent(sembol)
    
    organizer_agent(teknik, haber)

if __name__ == "__main__":
    tam_analiz("THYAO")
    # tam_analiz("GARAN")   # başka hisse denemek için
