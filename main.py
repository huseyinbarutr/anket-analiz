import matplotlib
matplotlib.use('Agg') # Grafik donmasını önler

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, HTMLResponse
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

app = FastAPI(title="Ultimate İstatistik Sistemi", docs_url="/docs")

# ==========================================================
# 🔑 GOOGLE API AYARLARI (İsim Güncellendi)
# ==========================================================
# Kod artık Render'dan "GOOGLE_API_KEY" ismini arayacak
API_KEY = os.getenv("GOOGLE_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

# ==========================================================
# 🎨 TASARIM: MODERN ARAYÜZ + OTOMATİK İNDİRME
# ==========================================================
html_content = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Akıllı İstatistik Asistanı</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background: #f0f2f5; margin: 0; padding: 0; display: flex; flex-direction: column; align-items: center; min-height: 100vh; }
        
        .header { background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%); width: 100%; padding: 40px 0; text-align: center; color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 30px; }
        .header h1 { margin: 0; font-size: 2.2rem; }
        .header p { opacity: 0.9; margin-top: 10px; }

        .main-box { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center; max-width: 500px; width: 90%; margin-bottom: 40px; }
        
        .upload-area { border: 2px dashed #6c5ce7; border-radius: 15px; padding: 30px; cursor: pointer; transition: 0.3s; position: relative; background: #fafafa; }
        .upload-area:hover { background: #f0f0ff; border-color: #5641e5; }
        .upload-area input { position: absolute; width: 100%; height: 100%; top: 0; left: 0; opacity: 0; cursor: pointer; }
        .icon-big { font-size: 50px; color: #6c5ce7; margin-bottom: 10px; }
        
        .btn-start { background: #6c5ce7; color: white; border: none; padding: 15px 40px; border-radius: 50px; font-size: 18px; font-weight: 600; cursor: pointer; margin-top: 20px; box-shadow: 0 5px 15px rgba(108, 92, 231, 0.4); transition: 0.3s; width: 100%; }
        .btn-start:hover { transform: scale(1.02); background: #5641e5; }
        .btn-start:disabled { background: #ccc; cursor: not-allowed; }

        .tools-title { color: #555; font-size: 1.2rem; margin-bottom: 20px; font-weight: 600; }
        .tools-container { display: flex; gap: 15px; flex-wrap: wrap; justify-content: center; max-width: 800px; }
        .tool-card { background: white; padding: 15px 25px; border-radius: 10px; text-decoration: none; color: #333; font-weight: 500; box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: 0.2s; display: flex; align-items: center; gap: 10px; }
        .tool-card:hover { transform: translateY(-3px); box-shadow: 0 5px 10px rgba(0,0,0,0.1); color: #6c5ce7; }

        #status { margin-top: 20px; font-weight: bold; min-height: 25px; }
        .success { color: #00b894; }
        .error { color: #d63031; }
        .loader { border: 3px solid #f3f3f3; border-top: 3px solid #6c5ce7; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; display: inline-block; vertical-align: middle; margin-right: 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>

    <div class="header">
        <h1>🚀 Akıllı İstatistik Asistanı</h1>
        <p>Yapay Zeka Destekli Analiz & Raporlama</p>
    </div>

    <div class="main-box">
        <div class="upload-area">
            <div class="icon-big">📂</div>
            <div id="file-label">Excel dosyanı buraya bırak veya tıkla</div>
            <input type="file" id="fileInput" accept=".xlsx, .xls">
        </div>

        <button class="btn-start" onclick="uploadFile()" id="uploadBtn">Analizi Başlat & İndir</button>
        <div id="status"></div>
    </div>

    <div class="tools-title">Diğer Manuel Araçlar</div>
    <div class="tools-container">
        <a href="/docs#/default/graph_pie_chart_graph_pie_chart_post" class="tool-card">🥧 Pasta Grafiği</a>
        <a href="/docs#/default/graph_bar_chart_graph_bar_chart_post" class="tool-card">📊 Sütun Grafiği</a>
        <a href="/docs#/default/analyze_independent_t_test_analyze_independent_t_test_post" class="tool-card">🧪 T-Testi</a>
        <a href="/docs" class="tool-card">⚙️ Tüm Testler</a>
    </div>

    <div style="margin-top: 40px; color: #999; font-size: 0.8rem;">Sistem Durumu: 🟢 Hazır | Versiyon: 5.0 (Google Key)</div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const fileLabel = document.getElementById('file-label');
        
        fileInput.addEventListener('change', () => {
            if(fileInput.files.length > 0) {
                fileLabel.innerText = "✅ Seçilen: " + fileInput.files[0].name;
                fileLabel.style.fontWeight = "bold";
                fileLabel.style.color = "#6c5ce7";
            }
        });

        async function uploadFile() {
            const file = fileInput.files[0];
            if (!file) {
                alert("Lütfen önce bir Excel dosyası seç!");
                return;
            }

            const btn = document.getElementById('uploadBtn');
            const status = document.getElementById('status');
            
            btn.disabled = true;
            btn.innerHTML = '<div class="loader"></div> Yapay Zeka Düşünüyor...';
            status.innerText = "";

            const formData = new FormData();
            formData.append("file", file);

            try {
                const response = await fetch('/analyze/smart-auto', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = "Akilli_Analiz_Raporu.pdf";
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    
                    status.innerHTML = "<span class='success'>🎉 Rapor Hazır! İndirilenlere bak.</span>";
                    btn.innerHTML = "Yeni Dosya Yükle";
                } else {
                    status.innerHTML = "<span class='error'>❌ Hata: Dosya formatını kontrol et.</span>";
                    btn.innerHTML = "Tekrar Dene";
                }
            } catch (error) {
                status.innerHTML = "<span class='error'>❌ Sunucu Hatası! Sayfayı yenile.</span>";
                console.error(error);
                btn.innerHTML = "Tekrar Dene";
            } finally {
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def main_page():
    return html_content

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

@app.post("/analyze/simple-report")
async def analyze_simple_report(file: UploadFile = File(...)):
    try:
        df = read_file(await file.read())
        desc = df.describe().to_dict()
        return {"ozet": desc}
    except Exception as e: return {"Hata": str(e)}

@app.post("/analyze/independent-t-test")
async def analyze_independent_t_test(file: UploadFile = File(...)):
    try:
        df = read_file(await file.read())
        cat_cols = [c for c in df.columns if df[c].dtype == 'O' and df[c].nunique() == 2]
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        
        if not cat_cols or not num_cols:
            return {"Hata": "Veride 2 kategorili bir grup sütunu (örn: Cinsiyet) ve sayısal bir sütun bulunamadı."}
        
        grp_col = cat_cols[0] 
        target_col = num_cols[0]
        
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

def decide_and_analyze(df):
    logs = []
    cols = df.columns
    has_pre_post = 'on_test' in cols and 'son_test' in cols
    has_group = 'grup' in cols
    logs.append("1. Veri seti tarandi.")
    
    if has_group and has_pre_post:
        logs.append("2. Karma Desen (Grup + Zaman) tespit edildi.")
        logs.append("3. Karar: 'Mixed ANOVA' testi secildi.")
        try:
            df['id'] = range(len(df))
            df_long = pd.melt(df, id_vars=['id', 'grup'], value_vars=['on_test', 'son_test'], var_name='zaman', value_name='puan')
            aov = pg.mixed_anova(dv='puan', within='zaman', between='grup', subject='id', data=df_long)
            return {"p": aov.iloc[0]['p-unc'], "test": "Mixed ANOVA"}, logs
        except: pass

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
    # DÜZELTME BURADA YAPILDI: ARTIK GOOGLE_API_KEY ARAYACAK
    if not os.getenv("GOOGLE_API_KEY"):
        return "Yapay Zeka Anahtari (GOOGLE_API_KEY) girilmedigi icin otomatik yorum yapilamadi."
    
    prompt = f"Sen bir istatistikçisin. Analiz Logları: {logs}. Sonuç: {stats_res}. Buna göre 1 paragraf akademik yorum yaz."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
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
    data = {'grup': ['A']*5+['B']*5, 'on_test': [40,42,38,45,41, 40,43,39,44,42], 'son_test': [85,88,90,82,86, 45,48,42,46,44]}
    df = pd.DataFrame(data)
    output = io.BytesIO(); df.to_excel(output, index=False); output.seek(0)
    return await smart_auto_analysis(UploadFile(filename="demo.xlsx", file=output))