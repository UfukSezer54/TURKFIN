import borsapy as bp
from crewai import Agent, Task, Crew
import pandas as pd
import pandas_ta as ta
import os

# LLM için Groq veya Grok kullanacağız (ücretsiz tier'lar var)
# Şimdilik basit tutmak için yerel yorum yapacağız, sonra LLM bağlayacağız.

def teknik_analiz(sembol):
    ticker = bp.Ticker(sembol)
    df = ticker.history(period="120d")
    
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['SMA20'] = ta.sma(df['Close'], length=20)
    
    rsi = df['RSI'].iloc[-1]
    return {
        "sembol": sembol,
        "fiyat": ticker.info.get('last'),
        "degisim": ticker.info.get('change_percent'),
        "rsi": round(rsi, 2) if pd.notna(rsi) else None,
        "yorum": "Zayıf görünüyor, destek takip edilmeli." if rsi < 45 else "Nötr / Güçlü"
    }

# Basit Multi-Agent Simülasyonu (şimdilik tek dosya)
def tam_analiz_raporu(sembol="THYAO"):
    print(f"🤖 {sembol} için Multi-Agent Analiz Başlıyor...\n")
    
    veri = teknik_analiz(sembol)
    
    print("=== 📊 TEKNİK AGENT RAPORU ===")
    print(f"Fiyat     : {veri['fiyat']} TL")
    print(f"Değişim   : %{veri['degisim']}")
    print(f"RSI       : {veri['rsi']}")
    print(f"Teknik Görünüm: {veri['yorum']}\n")
    
    print("=== 📰 HABER & SENTIMENT AGENT (Simüle) ===")
    print("• Son haber akışı nötr-pozitif kabul ediliyor.")
    print("• Sosyal medyada orta düzeyde olumlu yorum var.\n")
    
    print("=== 🎯 ORGANIZER AGENT - NİHAİ TAVSİYE ===")
    print(f"THYAO için **Kısa Vadeli:** İZLE")
    print("Destek seviyesi: 295 - 300 TL")
    print("Direnç seviyesi: 320 TL")
    print("Risk seviyesi: Orta")
    print("\nNot: Bu rapor sadece eğitim amaçlıdır, yatırım tavsiyesi değildir.")
    print("="*80)

if __name__ == "__main__":
    tam_analiz_raporu("THYAO")
    # tam_analiz_raporu("GARAN")   # başka hisse denemek için
