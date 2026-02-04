import pandas as pd

# Rastgele veriler (Ön test düşük, Son test yüksek olsun ki fark çıksın)
data = {
    'on_test': [45, 50, 42, 55, 60, 48, 52, 49, 58, 40, 44, 51, 53, 47, 56],
    'son_test': [75, 80, 78, 82, 85, 79, 81, 80, 88, 70, 76, 83, 85, 77, 84]
}

# DataFrame oluştur ve Excel'e kaydet
df = pd.DataFrame(data)
df.to_excel("deneme_verisi.xlsx", index=False)

print("Tamamdır! 'deneme_verisi.xlsx' adında bir dosya oluşturuldu.")