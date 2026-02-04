from mangum import Mangum
import matplotlib
matplotlib.use('Agg') # Grafik donmasını önler

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
import pandas as pd
import io
import pingouin as pg
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import tempfile
import os
import openai 

app = FastAPI(title="Ultimate İstatistik Sistemi (Full + FailSafe)")

# ==========================================================
# 🔑 API ANAHTARI (Hatalı olsa bile sistem çalışır)
# ==========================================================
API_KEY = "sk-proj-..." # Kendi kodun buraya
# ==========================================================

try:
    client = openai.OpenAI(api_key=API_KEY)
except:
    client = None

# --- YARDIMCI: Karakter Düzeltici ---
def tr_fix(text):
    if not isinstance(text, str): return str(text)
    mapping = {'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'}
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return text

# --- YARDIMCI: Veri Okuma ---
def read_simple_data(contents):
    df = pd.read_excel(io.BytesIO(contents))
    df.columns = [c.lower() for c in df.columns]
    return df

# --- PDF TASARIM ---
class PDFReport(FPDF):
    def header(self):
        self.set_fill_color(41, 128, 185) 
        self.rect(0, 0, 210, 20, 'F') 
        self.set_font('Arial', 'B', 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 5, tr_fix('AKILLI ANALIZ RAPORU'), align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Sayfa {self.page_no()}', align='C')
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(41, 128, 185)
        self.cell(0, 10, tr_fix(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(41, 128, 185)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, tr_fix(body))
        self.ln()
    def add_insight_box(self, text):
        self.set_fill_color(240, 240, 240)
        self.set_text_color(0, 0, 0)
        self.set_font('Arial', 'I', 10)
        self.multi_cell(0, 6, tr_fix(text), fill=True, border=0)
        self.ln()

# --- MANTIK MOTORU (KARAR MEKANİZMASI) ---
def decide_and_analyze(df):
    logs = []
    stats_result = {}
    cols = df.columns
    has_pre_post = 'on_test' in cols and 'son_test' in cols
    has_group = 'grup' in cols
    
    logs.append("1. Veri seti tarandi.")
    
    if has_group and has_pre_post:
        logs.append("2. Karma Desen (Grup + Zaman) tespit edildi.")
        logs.append("3. Karar: 'Mixed ANOVA' testi secildi.")
        
        diff = df['son_test'] - df['on_test']
        is_normal = stats.shapiro(diff).pvalue > 0.05
        if is_normal: logs.append("4. Veri normal dagiliyor (Parametrik).")
        else: logs.append("4. Veri normal degil ama ANOVA uygulandi.")

        df['id'] = range(len(df))
        df_long = pd.melt(df, id_vars=['id', 'grup'], value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
        try:
            aov = pg.mixed_anova(dv='puan', within='zaman', between='grup', subject='id', data=df_long)
            p_val = aov.iloc[0]['p-unc']
            test_name = "Mixed ANOVA"
        except:
            p_val = 0.99; test_name = "Hata"
            
    elif has_pre_post:
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
        p_val = res['p-val'].values[0]
    else:
        return None, ["Veri yapisi uygun degil."]

    return {"p": p_val, "test": test_name}, logs

# --- HATA KORUMALI YORUMCU ---
def get_methodology_explanation(logs, stats_res):
    prompt = f"Loglar: {logs}. Sonuc: {stats_res}. Akademik yorumla."
    # AI Denemesi
    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except: pass 
    
    # Manuel Mod (Yedek)
    fallback = "OTOMATIK SISTEM RAPORU (Manuel Mod):\n\n"
    for item in logs: fallback += f"- {item}\n"
    fallback += f"\nSONUC: {stats_res['test']} (p={round(stats_res['p'], 5)})"
    return fallback

# ==========================================
# 1. GRAFİK ENDPOINTLERİ (ESKİLER GERİ GELDİ)
# ==========================================

@app.post("/graph/pie-chart")
async def pie_chart(file: UploadFile = File(...)):
    try:
        df = read_simple_data(await file.read())
        if 'grup' not in df.columns: return {"Hata": "Grup sutunu yok"}
        plt.figure(figsize=(6,6))
        df['grup'].value_counts().plot.pie(autopct='%1.1f%%')
        plt.title('Katilimci Dagilimi')
        buf = io.BytesIO(); plt.savefig(buf, format='png'); buf.seek(0); plt.close()
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e: return {"Hata": str(e)}

@app.post("/graph/bar-chart")
async def bar_chart(file: UploadFile = File(...)):
    try:
        df = read_simple_data(await file.read())
        df_long = pd.melt(df, id_vars=['grup'] if 'grup' in df.columns else [], value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
        plt.figure(figsize=(8,6))
        sns.barplot(data=df_long, x='zaman', y='puan', hue='grup' if 'grup' in df.columns else None)
        plt.title('Ortalamalar')
        buf = io.BytesIO(); plt.savefig(buf, format='png'); buf.seek(0); plt.close()
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e: return {"Hata": str(e)}

@app.post("/graph/simple-boxplot")
async def simple_boxplot(file: UploadFile = File(...)):
    try:
        df = read_simple_data(await file.read())
        plt.figure(figsize=(8,6))
        plt.boxplot([df['on_test'], df['son_test']], labels=['On', 'Son'])
        buf = io.BytesIO(); plt.savefig(buf, format='png'); buf.seek(0); plt.close()
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e: return {"Hata": str(e)}

# ==========================================
# 2. ANALİZ ENDPOINTLERİ (JSON ÇIKTI)
# ==========================================

@app.post("/analyze/simple-report")
async def analyze_simple(file: UploadFile = File(...)):
    """Basit T-Testi (JSON)"""
    try:
        df = read_simple_data(await file.read())
        res = pg.ttest(df['on_test'], df['son_test'], paired=True)
        return {"test": "Paired T-Test", "p_value": res['p-val'].values[0]}
    except Exception as e: return {"Hata": str(e)}

@app.post("/analyze/independent-t-test")
async def independent_t_test(file: UploadFile = File(...)):
    """Bağımsız T-Testi (JSON)"""
    try:
        df = read_simple_data(await file.read())
        grps = df['grup'].unique()
        if len(grps) != 2: return {"Hata": "2 Grup lazim"}
        g1 = df[df['grup']==grps[0]]['son_test']
        g2 = df[df['grup']==grps[1]]['son_test']
        res = pg.ttest(g1, g2)
        return {"test": "Independent T-Test", "p_value": res['p-val'].values[0], "yorum": "Fark Var" if res['p-val'].values[0]<0.05 else "Fark Yok"}
    except Exception as e: return {"Hata": str(e)}

# ==========================================
# 3. MEGA ENDPOINT (PDF + SMART AUTO)
# ==========================================

@app.post("/analyze/smart-auto")
async def smart_auto_analysis(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        df.columns = [c.lower() for c in df.columns]

        stats_res, logs = decide_and_analyze(df)
        if stats_res is None: return {"Hata": "Veri uygun degil"}
        
        # Hata korumalı metin
        methodology_text = get_methodology_explanation(logs, stats_res)

        # Grafik
        plt.figure(figsize=(10, 6))
        sns.set_theme(style="whitegrid")
        if 'grup' in df.columns:
            df_long = pd.melt(df, id_vars=['grup'], value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            sns.pointplot(data=df_long, x='zaman', y='puan', hue='grup', capsize=.1)
        else:
            df_long = pd.melt(df, value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            sns.boxplot(data=df_long, x='zaman', y='puan', palette="Set2")
            
        img_temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        plt.savefig(img_temp.name, bbox_inches='tight'); plt.close()

        # PDF
        pdf = PDFReport()
        pdf.add_page()
        pdf.chapter_title("1. Istatistiksel Bulgular")
        pdf.chapter_body(f"Test: {stats_res['test']}\nP-Degeri: {round(stats_res['p'], 5)}")
        pdf.chapter_title("2. Metodoloji (Akilli Karar)")
        pdf.add_insight_box(methodology_text) # Hata vermez!
        pdf.chapter_title("3. Gorsel")
        pdf.image(img_temp.name, w=160)
        
        pdf_bytes = bytes(pdf.output())
        img_temp.close(); os.unlink(img_temp.name)

        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=akilli_rapor.pdf"})

    except Exception as e: return {"Sistem Hatası": str(e)}

# --- DEMO ---
@app.get("/demo/smart-test")
async def demo_smart():
    data = {'grup': ['A']*5+['B']*5, 'on_test': [40,42,38,45,41, 40,43,39,44,42], 'son_test': [85,88,90,82,86, 45,48,42,46,44]}
    df = pd.DataFrame(data)
    output = io.BytesIO(); df.to_excel(output, index=False); output.seek(0)
    return await smart_auto_analysis(UploadFile(filename="demo.xlsx", file=output))
handler = Mangum(app)