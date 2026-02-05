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
# 🧠 SMART AUTO (Yapay Zeka Bölümü)
# ==========================================================
def decide_and_analyze(df):
    logs = []
    cols = df.columns
    has_pre_post = 'on_test' in cols and 'son_test' in cols
    has_group = 'grup' in cols
    logs.append("1. Veri seti tarandi.")
    
    # 1. Senaryo: Mixed ANOVA (Grup + Zaman)
    if has_group and has_pre_post:
        logs.append("2. Karma Desen (Grup + Zaman) tespit edildi.")
        logs.append("3. Karar: 'Mixed ANOVA' testi secildi.")
        try:
            df['id'] = range(len(df))
            df_long = pd.melt(df, id_vars=['id', 'grup'], value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            aov = pg.mixed_anova(dv='puan', within='zaman', between='grup', subject='id', data=df_long)
            return {"p": aov.iloc[0]['p-unc'], "test": "Mixed ANOVA"}, logs
        except: pass

    # 2. Senaryo: T-Testi (Sadece Zaman)
    if has_pre_post:
        logs.append("2. Sadece Zaman degisimi (On-Son) tespit edildi.")
        diff = df['son_test'] - df['on_test']
        if stats.shapiro(diff).pvalue > 0.05:
            logs.append("3. Veri Normal. Karar: 'Paired T-Test'.")
            res = pg.ttest(df['on_test'], df['son_test'], paired=True)
            test_name = "Paired T-Test"
        else:
            logs.append("3. Veri Normal Degil. Karar: 'Wilcoxon'.")
            res = pg.wilcoxon(df['on_test'], df['son_test'])
            test_name = "Wilcoxon"
        return {"p": res['p-val'].values[0], "test": test_name}, logs
    
    return None, ["Veri yapisi Smart Auto icin uygun degil. Lutfen Manuel Testleri kullanin."]

def get_methodology_explanation(logs, stats_res):
    if not os.getenv("GOOGLE_API_KEY"):
        return "Yapay Zeka Anahtari girilmedigi icin otomatik yorum yapilamadi."
    prompt = f"Sen bir istatistikçisin. Analiz Logları: {logs}. Sonuç: {stats_res}. Buna göre 1 paragraf akademik yorum yaz."
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"AI Hatasi: {e}"

@app.post("/analyze/smart-auto")
async def smart_auto_analysis(file: UploadFile = File(...)):
    try:
        df = read_file(await file.read())
        stats_res, logs = decide_and_analyze(df)
        if stats_res is None: return {"Hata": "Veri yapısı uygun değil"}
        
        methodology_text = get_methodology_explanation(logs, stats_res)
        
        # Grafik
        plt.figure(figsize=(10, 6))
        sns.set_theme(style="whitegrid")
        if 'grup' in df.columns and 'on_test' in df.columns:
            df_long = pd.melt(df, id_vars=['grup'], value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            sns.pointplot(data=df_long, x='zaman', y='puan', hue='grup')
        elif 'on_test' in df.columns:
            df_long = pd.melt(df, value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            sns.boxplot(data=df_long, x='zaman', y='puan')
        
        img_temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        plt.savefig(img_temp.name, bbox_inches='tight'); plt.close()
        
        # PDF
        pdf = PDFReport()
        pdf.add_page()
        pdf.chapter_title("1. Bulgular")
        pdf.chapter_body(f"Test: {stats_res['test']}\nP-Degeri: {round(stats_res['p'], 5)}")
        pdf.chapter_title("2. Akademik Yorum (AI)")
        pdf.set_fill_color(240, 240, 240); pdf.multi_cell(0, 6, tr_fix(methodology_text), fill=True); pdf.ln()
        pdf.chapter_title("3. Gorsel")
        pdf.image(img_temp.name, w=160)
        
        pdf_bytes = bytes(pdf.output())
        img_temp.close(); os.unlink(img_temp.name)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=akilli_rapor.pdf"})
    except Exception as e: return {"Sistem Hatası": str(e)}

@app.get("/demo/smart-test")
async def demo_smart():
    """Test için örnek veri indirir"""
    data = {'grup': ['A']*5+['B']*5, 'on_test': [40,42,38,45,41, 40,43,39,44,42], 'son_test': [85,88,90,82,86, 45,48,42,46,44]}
    df = pd.DataFrame(data)
    output = io.BytesIO(); df.to_excel(output, index=False); output.seek(0)
    return await smart_auto_analysis(UploadFile(filename="demo.xlsx", file=output))