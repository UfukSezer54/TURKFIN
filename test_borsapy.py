import borsapy as bp

print("✅ Borsapy başarıyla çalışıyor!\n")

hisse = bp.Ticker("THYAO")

print("=== Genel Bilgiler ===")
print(f"Sembol: {hisse.info.get('symbol')}")
print(f"Son Fiyat: {hisse.info.get('last')}")
print(f"Açılış: {hisse.info.get('open')}")
print(f"Yüksek: {hisse.info.get('high')}")
print(f"Düşük: {hisse.info.get('low')}")
print(f"Değişim: {hisse.info.get('change')}")
print(f"Değişim (%): {hisse.info.get('change_percent')}")

print("\n=== Son 5 Günlük Fiyat Tablosu ===")
print(hisse.history(period="5d"))

print("\n=== Temel Bilgiler (Daha Fazla) ===")
print(hisse.info)
