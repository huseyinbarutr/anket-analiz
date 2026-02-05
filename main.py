import matplotlib
matplotlib.use('Agg') # Grafik donmasını önler

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, HTMLResponse, FileResponse
import pandas as pd
import io
import pingouin as pg
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import tempfile
import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

app = FastAPI(title="Ultimate İstatistik Sistemi (Full + FailSafe)", docs_url="/docs")

# ==========================================================
# 🔑 GEMINI API AYARLARI
# ==========================================================
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_KEY:
    genai.configure(api_key=GOOGLE_KEY)

# ==========================================================
# 🎨 TASARIM: MODERN ARAYÜZ (HTML)
# ==========================================================

@app.get("/", response_class=HTMLResponse)
async def main_page():
    return FileResponse("templates/index.html")

# ==========================================================
# 🛠️ YARDIMCI FONKSİYONLAR
# ==========================================================
def tr_fix(text):
    if not isinstance(text, str): return str(text)
    mapping = {'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'}
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return text

def read_file(contents):
    df = pd.read_excel(io.BytesIO(contents))
    df.columns = [str(c).lower().strip() for c in df.columns]
    return df

class PDFReport(FPDF):
    def header(self):
        self.set_fill_color(41, 128, 185) 
        self.rect(0, 0, 210, 20, 'F') 
        self.set_font('Arial', 'B', 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 5, tr_fix('ANALIZ RAPORU'), align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(10)
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(41, 128, 185)
        self.cell(0, 10, tr_fix(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, tr_fix(body))
        self.ln()

# ==========================================================
# 🔙 GERİ GETİRİLEN FONKSİYONLAR (Testler ve Grafikler)
# ==========================================================

@app.post("/analyze/simple-report")
async def analyze_simple_report(file: UploadFile = File(...)):
    """Veri setinin temel istatistiklerini (Ortalama, Medyan, SS) verir."""
    try:
        df = read_file(await file.read())
        desc = df.describe().to_dict()
        return {"ozet": desc}
    except Exception as e: return {"Hata": str(e)}

@app.post("/analyze/independent-t-test")
async def analyze_independent_t_test(file: UploadFile = File(...)):
    """Otomatik Bağımsız Örneklem T-Testi (2 Grup bulup karşılaştırır)"""
    try:
        df = read_file(await file.read())
        # Otomatik grup sütunu bul (2 benzersiz değeri olan string sütun)
        cat_cols = [c for c in df.columns if df[c].dtype == 'O' and df[c].nunique() == 2]
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        
        if not cat_cols or not num_cols:
            return {"Hata": "Veride 2 kategorili bir grup sütunu (örn: Cinsiyet) ve sayısal bir sütun bulunamadı."}
        
        grp_col = cat_cols[0] # İlk bulduğu grup sütununu al
        target_col = num_cols[0] # İlk bulduğu sayısal sütunu al
        
        g1 = df[df[grp_col] == df[grp_col].unique()[0]][target_col]
        g2 = df[df[grp_col] == df[grp_col].unique()[1]][target_col]
        
        res = stats.ttest_ind(g1, g2)
        return {
            "Test": "Bagimsiz Orneklem T-Testi",
            "Grup_Degiskeni": grp_col,
            "Bagimli_Degisken": target_col,
            "T-Degeri": float(res.statistic),
            "P-Degeri": float(res.pvalue),
            "Sonuc": "Anlamli Fark Var!" if res.pvalue < 0.05 else "Anlamli Fark Yok."
        }
    except Exception as e: return {"Hata": str(e)}

@app.post("/graph/pie-chart")
async def graph_pie_chart(file: UploadFile = File(...)):
    """Verideki ilk kategorik sütunu bulup Pasta Grafiği çizer"""
    try:
        df = read_file(await file.read())
        cat_cols = [c for c in df.columns if df[c].dtype == 'O']
        if not cat_cols: return {"Hata": "Kategorik sütun yok"}
        
        plt.figure(figsize=(8,8))
        df[cat_cols[0]].value_counts().plot.pie(autopct='%1.1f%%', startangle=90, cmap='Pastel1')
        plt.title(f"Dagilim: {cat_cols[0]}")
        plt.ylabel("")
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', bbox_inches='tight')
        img_buf.seek(0); plt.close()
        return Response(content=img_buf.getvalue(), media_type="image/png")
    except Exception as e: return {"Hata": str(e)}

@app.post("/graph/bar-chart")
async def graph_bar_chart(file: UploadFile = File(...)):
    """Sütun Grafiği"""
    try:
        df = read_file(await file.read())
        cat_cols = [c for c in df.columns if df[c].dtype == 'O']
        if not cat_cols: return {"Hata": "Kategorik sütun yok"}
        
        plt.figure(figsize=(10,6))
        sns.countplot(y=cat_cols[0], data=df, palette="viridis")
        plt.title(f"Sayilar: {cat_cols[0]}")
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', bbox_inches='tight')
        img_buf.seek(0); plt.close()
        return Response(content=img_buf.getvalue(), media_type="image/png")
    except Exception as e: return {"Hata": str(e)}

@app.post("/graph/simple-boxplot")
async def graph_simple_boxplot(file: UploadFile = File(...)):
    """Kutu Grafiği (Boxplot)"""
    try:
        df = read_file(await file.read())
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols: return {"Hata": "Sayisal sütun yok"}

        plt.figure(figsize=(8,6))
        sns.boxplot(y=df[num_cols[0]], palette="Set2")
        plt.title(f"Dagilim: {num_cols[0]}")
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', bbox_inches='tight')
        img_buf.seek(0); plt.close()
        return Response(content=img_buf.getvalue(), media_type="image/png")
    except Exception as e: return {"Hata": str(e)}

# ==========================================================
# 🧠 SMART AUTO (Yapay Zeka Bölümü) - TÜM TESTLERİ YAPAR
# ==========================================================

def run_all_tests(df):
    """Tüm istatistiksel testleri çalıştırır ve sonuçları döndürür"""
    results = {}
    cols = df.columns
    has_pre_post = 'on_test' in cols and 'son_test' in cols
    has_group = 'grup' in cols
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    
    # 1. TANIMLAYICI İSTATİSTİKLER
    desc_stats = {}
    for col in num_cols:
        desc_stats[col] = {
            "N": int(df[col].count()),
            "Ortalama": round(df[col].mean(), 3),
            "Std Sapma": round(df[col].std(), 3),
            "Min": round(df[col].min(), 3),
            "Max": round(df[col].max(), 3),
            "Medyan": round(df[col].median(), 3)
        }
    results["tanimlayici"] = desc_stats
    
    # 2. NORMALLİK TESTLERİ
    normality = {}
    for col in num_cols:
        try:
            stat, p = stats.shapiro(df[col].dropna())
            normality[col] = {"Shapiro-W": round(stat, 4), "p": round(p, 4), "Normal": "Evet" if p > 0.05 else "Hayir"}
        except: pass
    results["normallik"] = normality
    
    # 3. T-TESTLERİ
    if has_pre_post:
        # Paired T-Test
        try:
            paired_res = pg.ttest(df['on_test'], df['son_test'], paired=True)
            results["paired_ttest"] = {
                "T": round(paired_res['T'].values[0], 4),
                "p": round(paired_res['p-val'].values[0], 5),
                "Cohen-d": round(paired_res['cohen-d'].values[0], 4),
                "Sonuc": "Anlamli" if paired_res['p-val'].values[0] < 0.05 else "Anlamli Degil"
            }
        except: pass
        
        # Wilcoxon (non-parametric)
        try:
            wilc_res = pg.wilcoxon(df['on_test'], df['son_test'])
            results["wilcoxon"] = {
                "W": round(wilc_res['W-val'].values[0], 4),
                "p": round(wilc_res['p-val'].values[0], 5),
                "Sonuc": "Anlamli" if wilc_res['p-val'].values[0] < 0.05 else "Anlamli Degil"
            }
        except: pass
    
    # 4. GRUPLAR ARASI T-TEST
    if has_group and len(df['grup'].unique()) == 2:
        groups = df['grup'].unique()
        for col in num_cols:
            try:
                g1 = df[df['grup'] == groups[0]][col]
                g2 = df[df['grup'] == groups[1]][col]
                ind_res = pg.ttest(g1, g2, paired=False)
                results[f"independent_ttest_{col}"] = {
                    "Gruplar": f"{groups[0]} vs {groups[1]}",
                    "Degisken": col,
                    "T": round(ind_res['T'].values[0], 4),
                    "p": round(ind_res['p-val'].values[0], 5),
                    "Cohen-d": round(ind_res['cohen-d'].values[0], 4),
                    "Sonuc": "Anlamli" if ind_res['p-val'].values[0] < 0.05 else "Anlamli Degil"
                }
            except: pass
    
    # 5. MIXED ANOVA
    if has_group and has_pre_post:
        try:
            df_copy = df.copy()
            df_copy['id'] = range(len(df_copy))
            df_long = pd.melt(df_copy, id_vars=['id', 'grup'], value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            aov = pg.mixed_anova(dv='puan', within='zaman', between='grup', subject='id', data=df_long)
            results["mixed_anova"] = {
                "Zaman_F": round(aov[aov['Source'] == 'zaman']['F'].values[0], 4),
                "Zaman_p": round(aov[aov['Source'] == 'zaman']['p-unc'].values[0], 5),
                "Grup_F": round(aov[aov['Source'] == 'grup']['F'].values[0], 4),
                "Grup_p": round(aov[aov['Source'] == 'grup']['p-unc'].values[0], 5),
                "Etkilesim_F": round(aov[aov['Source'] == 'Interaction']['F'].values[0], 4),
                "Etkilesim_p": round(aov[aov['Source'] == 'Interaction']['p-unc'].values[0], 5)
            }
        except: pass
    
    # 6. KORELASYON
    if len(num_cols) >= 2:
        try:
            corr_matrix = df[num_cols].corr()
            results["korelasyon"] = corr_matrix.round(4).to_dict()
        except: pass
    
    return results

def get_ai_interpretation(all_results):
    """AI ile tüm sonuçları yorumla"""
    if not os.getenv("GOOGLE_API_KEY"):
        return "Yapay Zeka Anahtari girilmedigi icin otomatik yorum yapilamadi."
    prompt = f"""Sen bir istatistik uzmanısın. Aşağıdaki analiz sonuçlarını Türkçe olarak akademik bir dille yorumla. 
Her test için ayrı ayrı yorum yap ve sonuçların ne anlama geldiğini açıkla.
Sonuçlar: {all_results}
Lütfen 3-4 paragraf halinde kapsamlı bir yorum yaz."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_str = str(e).lower()
        if "429" in str(e) or "quota" in error_str or "exceeded" in error_str:
            return "Yapay Zeka API kotasi doldu. Lutfen birkaç dakika bekleyip tekrar deneyin veya API anahtarinizi yükseltin."
        return f"AI Hatasi: {e}"

@app.post("/analyze/smart-auto")
async def smart_auto_analysis(file: UploadFile = File(...)):
    try:
        df = read_file(await file.read())
        
        # Tüm testleri çalıştır
        all_results = run_all_tests(df)
        
        # AI yorumu al
        ai_interpretation = get_ai_interpretation(all_results)
        
        # Grafikler
        img_files = []
        
        # Grafik 1: Boxplot (grup varsa gruplu)
        plt.figure(figsize=(10, 6))
        sns.set_theme(style="whitegrid")
        if 'grup' in df.columns and 'on_test' in df.columns:
            df_long = pd.melt(df, id_vars=['grup'], value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            sns.boxplot(data=df_long, x='zaman', y='puan', hue='grup', palette='Set2')
            plt.title('Gruplara Gore On-Test ve Son-Test Dagilimi')
        elif 'on_test' in df.columns:
            df_long = pd.melt(df, value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            sns.boxplot(data=df_long, x='zaman', y='puan', palette='Set2')
            plt.title('On-Test ve Son-Test Dagilimi')
        img1 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        plt.savefig(img1.name, bbox_inches='tight', dpi=100); plt.close()
        img_files.append(img1.name)
        
        # Grafik 2: Line Plot (değişim grafiği)
        if 'grup' in df.columns and 'on_test' in df.columns:
            plt.figure(figsize=(10, 6))
            df_long = pd.melt(df, id_vars=['grup'], value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            sns.pointplot(data=df_long, x='zaman', y='puan', hue='grup', markers=['o', 's'], linestyles=['-', '--'])
            plt.title('Gruplarin Zaman Icerisindeki Degisimi')
            img2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            plt.savefig(img2.name, bbox_inches='tight', dpi=100); plt.close()
            img_files.append(img2.name)
        
        # PDF OLUŞTUR
        pdf = PDFReport()
        pdf.add_page()
        
        # 1. Tanımlayıcı İstatistikler
        pdf.chapter_title("1. Tanimlayici Istatistikler")
        if "tanimlayici" in all_results:
            for col, vals in all_results["tanimlayici"].items():
                text = f"{col}: N={vals['N']}, Ort={vals['Ortalama']}, SS={vals['Std Sapma']}, Min={vals['Min']}, Max={vals['Max']}"
                pdf.chapter_body(text)
        
        # 2. Normallik Testleri
        pdf.chapter_title("2. Normallik Testleri (Shapiro-Wilk)")
        if "normallik" in all_results:
            for col, vals in all_results["normallik"].items():
                text = f"{col}: W={vals['Shapiro-W']}, p={vals['p']} -> {vals['Normal']}"
                pdf.chapter_body(text)
        
        # 3. Paired T-Test
        if "paired_ttest" in all_results:
            pdf.chapter_title("3. Eslestirilmis T-Testi (Paired T-Test)")
            r = all_results["paired_ttest"]
            pdf.chapter_body(f"t={r['T']}, p={r['p']}, Cohen's d={r['Cohen-d']}\nSonuc: {r['Sonuc']}")
        
        # 4. Wilcoxon Testi
        if "wilcoxon" in all_results:
            pdf.chapter_title("4. Wilcoxon Testi (Non-Parametrik)")
            r = all_results["wilcoxon"]
            pdf.chapter_body(f"W={r['W']}, p={r['p']}\nSonuc: {r['Sonuc']}")
        
        # 5. Bağımsız T-Testler
        ind_tests = [k for k in all_results.keys() if k.startswith("independent_ttest")]
        if ind_tests:
            pdf.chapter_title("5. Bagimsiz Orneklem T-Testleri")
            for test_key in ind_tests:
                r = all_results[test_key]
                pdf.chapter_body(f"{r['Degisken']} ({r['Gruplar']}): t={r['T']}, p={r['p']}, d={r['Cohen-d']} -> {r['Sonuc']}")
        
        # 6. Mixed ANOVA
        if "mixed_anova" in all_results:
            pdf.chapter_title("6. Karma Desen ANOVA (Mixed ANOVA)")
            r = all_results["mixed_anova"]
            pdf.chapter_body(f"Zaman Etkisi: F={r['Zaman_F']}, p={r['Zaman_p']}")
            pdf.chapter_body(f"Grup Etkisi: F={r['Grup_F']}, p={r['Grup_p']}")
            pdf.chapter_body(f"Etkilesim: F={r['Etkilesim_F']}, p={r['Etkilesim_p']}")
        
        # 7. AI Yorumu
        pdf.add_page()
        pdf.chapter_title("7. Yapay Zeka Yorumu")
        pdf.set_fill_color(240, 240, 240)
        pdf.multi_cell(0, 6, tr_fix(ai_interpretation), fill=True)
        pdf.ln()
        
        # 8. Görseller
        pdf.add_page()
        pdf.chapter_title("8. Gorseller")
        for img_path in img_files:
            pdf.image(img_path, w=160)
            pdf.ln(5)
        
        pdf_bytes = bytes(pdf.output())
        
        # Temizlik
        for img_path in img_files:
            try: os.unlink(img_path)
            except: pass
        
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=kapsamli_analiz_raporu.pdf"})
    except Exception as e: return {"Sistem Hatası": str(e)}

@app.get("/demo/smart-test")
async def demo_smart():
    """Test için örnek veri indirir"""
    data = {'grup': ['A']*5+['B']*5, 'on_test': [40,42,38,45,41, 40,43,39,44,42], 'son_test': [85,88,90,82,86, 45,48,42,46,44]}
    df = pd.DataFrame(data)
    output = io.BytesIO(); df.to_excel(output, index=False); output.seek(0)
    return await smart_auto_analysis(UploadFile(filename="demo.xlsx", file=output))