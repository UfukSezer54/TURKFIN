import borsapy as bp
import pandas as pd

print("🔄 Popüler BIST Hisseleri Yükleniyor...\n")

# Popüler semboller (hızlı test için)
semboller = ["THYAO", "GARAN", "AKBNK", "BIMAS", "EREGL", "FROTO", "KCHOL", "TUPRS", "ISCTR", "SISE","ZPX30","ASELS","ALTINS1","GMSTRF","GLDTRF","MGROS","VESTL","PETKM","ARCLK","FENER","KRDMD"]  # İstediğiniz sembolleri ekleyebilirsiniz

data = []

for sembol in semboller:
    try:
        ticker = bp.Ticker(sembol)
        info = ticker.info
        data.append({
            'Sembol': sembol,
            'Şirket Adı': info.get('description', 'Bilinmiyor'),
            'Son Fiyat': info.get('last'),
            'Değişim %': info.get('change_percent'),
            'Hacim': info.get('volume'),
            'Yüksek': info.get('high'),
            'Düşük': info.get('low')
        })
        print(f"✅ {sembol} yüklendi")
    except:
        print(f"❌ {sembol} yüklenemedi")

df = pd.DataFrame(data)
df = df.sort_values(by='Değişim %', ascending=False, na_position='last')

print("\n" + "="*90)
print("📊 POPÜLER HİSSELER TABLOSU")
print(df.round(2).to_string(index=False))

print(f"\n✅ {len(df)} hisse başarıyla listelendi.")
print("\nBu yöntem daha stabil. İleride cache (önbellek) sistemi ekleyeceğiz.")
