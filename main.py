import matplotlib
matplotlib.use('Agg') # Grafik donmasını önler

from fastapi import FastAPI, UploadFile, File, HTTPException
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

# .env dosyasını yükle (Lokal çalışma için)
load_dotenv()

app = FastAPI(title="Ultimate İstatistik Sistemi", docs_url="/docs")

# ==========================================================
# 🔑 GEMINI API AYARLARI
# ==========================================================
GEMINI_KEY = os.getenv("AIzaSyDWhaJaJJ0a_pYBlYCtfT7lqpzotJ2Yffo")

if GEMINI_KEY:
    genai.configure(api_key=GEMAIzaSyDWhaJaJJ0a_pYBlYCtfT7lqpzotJ2YffoINI_KEY)
# ==========================================================

# --- TASARIM: MODERN ARAYÜZ (HTML/CSS/JS) ---
html_content = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Akıllı İstatistik Asistanı</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            margin: 0;
            display: flex;
            justify_content: center;
            align-items: center;
            color: #333;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
            width: 90%;
            transition: transform 0.3s;
        }
        .container:hover { transform: translateY(-5px); }
        h1 { color: #4a4a4a; margin-bottom: 10px; }
        p { color: #666; font-size: 0.9em; margin-bottom: 30px; }
        
        .upload-box {
            border: 2px dashed #667eea;
            border-radius: 10px;
            padding: 30px;
            cursor: pointer;
            transition: background 0.3s;
            position: relative;
        }
        .upload-box:hover { background: #f0f4ff; }
        .upload-box input {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            opacity: 0;
            cursor: pointer;
        }
        .icon { font-size: 40px; color: #667eea; margin-bottom: 10px; }
        
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 20px;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            transition: 0.3s;
        }
        .btn:hover { background: #764ba2; transform: scale(1.05); }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        
        #status { margin-top: 20px; font-weight: bold; height: 20px; }
        .success { color: #2ecc71; }
        .error { color: #e74c3c; }
        .loader {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            vertical-align: middle;
            margin-right: 10px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>

    <div class="container">
        <h1>📊 İstatistik Asistanı</h1>
        <p>Excel dosyanı yükle, yapay zeka analiz etsin ve raporunu PDF olarak hazırlasın.</p>
        
        <div class="upload-box">
            <div class="icon">📂</div>
            <div id="file-label">Dosyayı buraya sürükle veya tıkla</div>
            <input type="file" id="fileInput" accept=".xlsx, .xls">
        </div>

        <button class="btn" onclick="uploadFile()" id="uploadBtn">Analizi Başlat</button>
        
        <div id="status"></div>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const fileLabel = document.getElementById('file-label');
        
        fileInput.addEventListener('change', () => {
            if(fileInput.files.length > 0) {
                fileLabel.innerText = "Seçilen: " + fileInput.files[0].name;
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
            btn.innerHTML = '<div class="loader"></div> Analiz Yapılıyor...';
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
                    
                    status.innerHTML = "<span class='success'>✔ Rapor Hazır! İndiriliyor...</span>";
                    btn.innerHTML = "Tekrar Analiz Et";
                } else {
                    status.innerHTML = "<span class='error'>❌ Bir hata oluştu!</span>";
                    btn.innerHTML = "Analizi Başlat";
                }
            } catch (error) {
                status.innerHTML = "<span class='error'>❌ Sunucu hatası!</span>";
                btn.innerHTML = "Analizi Başlat";
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

def read_simple_data(contents):
    df = pd.read_excel(io.BytesIO(contents))
    df.columns = [c.lower() for c in df.columns]
    return df

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

def get_methodology_explanation(logs, stats_res):
    if not os.getenv("GEMINI_API_KEY"):
        return "Yapay Zeka Anahtari girilmedigi icin otomatik yorum yapilamadi."

    prompt = f"""
    Sen uzman bir istatistikçisin. Bir öğrencinin tez projesi için analiz yapıyorsun.
    Aşağıdaki analiz sonuçlarına bakarak, teze konulacak formatta akademik bir yorum paragrafı yaz.
    
    Yapılan İşlemler: {logs}
    İstatistiksel Sonuç: {stats_res}
    
    Lütfen sadece sonucu yorumla, başlık atma.
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Yapay zeka yorumu alinirken hata olustu: {str(e)}"

@app.post("/analyze/smart-auto")
async def smart_auto_analysis(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        df.columns = [c.lower() for c in df.columns]
        stats_res, logs = decide_and_analyze(df)
        if stats_res is None: return {"Hata": "Veri uygun degil"}
        methodology_text = get_methodology_explanation(logs, stats_res)
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
        pdf = PDFReport()
        pdf.add_page()
        pdf.chapter_title("1. Istatistiksel Bulgular")
        pdf.chapter_body(f"Test: {stats_res['test']}\nP-Degeri: {round(stats_res['p'], 5)}")
        pdf.chapter_title("2. Metodoloji (Akilli Karar)")
        pdf.add_insight_box(methodology_text)
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