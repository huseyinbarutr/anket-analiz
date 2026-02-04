import pandas as pd

# Senaryo: Deney grubu uçuyor (Eğitim işe yaradı), Kontrol grubu yerinde sayıyor.
data = {
    'grup': ['Deney']*5 + ['Kontrol']*5,
    'on_test': [40, 42, 38, 45, 41, 40, 43, 39, 44, 42],  # Başlangıçta herkes benzer
    'son_test': [85, 88, 90, 82, 86, 45, 48, 42, 46, 44]  # Deney arttı, Kontrol aynı kaldı
}

df = pd.DataFrame(data)
df.to_excel("pro_veri.xlsx", index=False)
print("pro_veri.xlsx oluşturuldu!")