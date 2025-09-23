from flask import Flask, request, send_file, render_template_string, session, redirect, url_for
import pandas as pd
import tempfile
import os

import io
from flask import Response

app = Flask(__name__)
app.secret_key = 'change_this_secret_key'

# Dummy HTML template with placeholders
HTML_TEMPLATE = '''
<div class="product">
  <h2>{{title}}</h2>
  <img src="{{image_url}}" alt="{{title}}" style="max-width:200px;"/>
  <p><strong>Price:</strong> ${{price}}</p>
  <p><strong>Description:</strong> {{description}}</p>
</div>
'''

@app.route('/')
def index():
    html_preview = session.get('generated_html', None)
    code_block = ''
    download_block = ''
    clear_block = ''
    product_count = 0
    if html_preview:
        # Count products by counting <div class="product">
        product_count = html_preview.count('<div class="product"')
        code_block = f'''
<div class="product-count">Total products: <b>{product_count}</b></div>
<h3 style="margin-top:32px;">All HTML Code</h3>
<div class="code-block" style="max-height:400px;overflow:auto; position:relative;">
  <button class="btn copy-btn sticky-copy" onclick="copyCode()">Copy HTML Code</button>
  <pre id="htmlCode" class="code-area">{html_preview.replace('<','&lt;').replace('>','&gt;')}</pre>
</div>
'''
        download_block = '''<a href="/download" class="btn">Download All HTML</a>'''
        clear_block = '''<a href="/clear" class="btn btn-clear">Clear HTML</a>'''
    return f'''
<html>
<head>
<title>Product HTML Generator</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(120deg,#e0eafc,#cfdef3); margin:0; padding:0; }}
    .container {{ max-width: 800px; margin: 40px auto; background: #fff; border-radius: 16px; box-shadow: 0 4px 24px #b0c4de; padding: 40px 36px 36px 36px; transition: box-shadow 0.3s; }}
    h1 {{ color: #2c3e50; font-size:2.2em; letter-spacing:1px; }}
    .btn {{ display:inline-block; background:#3498db; color:#fff; padding:10px 18px; border-radius:5px; text-decoration:none; margin-top:10px; border:none; cursor:pointer; font-size:1em; transition: background 0.2s, box-shadow 0.2s; box-shadow:0 2px 8px #cce; }}
    .btn:hover {{ background:#217dbb; box-shadow:0 4px 16px #aac; }}
    .btn-clear {{ background:#e74c3c; margin-left:10px; }}
    .btn-clear:hover {{ background:#c0392b; }}
    input[type=file] {{ margin-bottom: 12px; }}
    .code-block {{ background:#222; border-radius:8px; margin:18px 0 10px 0; padding:18px 12px 12px 12px; position:relative; box-shadow:0 2px 8px #b0c4de; transition: box-shadow 0.3s; }}
    .product-count {{ color:#555; margin-bottom:18px; }}
    .code-area {{ color:#fff; background:transparent; border:none; width:100%; min-height:180px; font-family: 'Fira Mono', 'Consolas', monospace; font-size:15px; outline:none; resize:vertical; white-space:pre-wrap; word-break:break-all; }}
    .copy-btn {{ background:#27ae60; }}
    .copy-btn:hover {{ background:#219150; }}
    .sticky-copy {{
        position: sticky;
        top: 12px;
        float: right;
        z-index: 2;
        margin-bottom: 8px;
    }}
    @media (max-width: 600px) {{ .container {{ padding: 10px; }} }}
</style>
<script>
function copyCode() {{
    var code = document.getElementById('htmlCode').innerText;
    var textarea = document.createElement('textarea');
    textarea.value = code.replace(/&lt;/g, '<').replace(/&gt;/g, '>');
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    alert('HTML code copied to clipboard!');
}}
</script>
</head>
<body>
<div class="container">
<h1>Product HTML Generator</h1>
<a href="/download-sample" class="btn">Download Sample CSV</a><br><br>
<form action="/generate" method="post" enctype="multipart/form-data" style="margin-bottom:24px;">
  <input type="file" name="file" accept=".xlsx,.xls,.csv" required />
  <button type="submit" class="btn">Generate HTML</button>
</form>
{code_block}
{download_block}
{clear_block}
</div>
</body>
</html>
'''
@app.route('/clear')
def clear():
    session.pop('generated_html', None)
    return redirect(url_for('index'))

@app.route('/download-sample')
def download_sample():
    sample_csv = (
        'title,price,description,image_url\n'
        'Product 1,10,First product,https://via.placeholder.com/200\n'
        'Product 2,20,Second product,https://via.placeholder.com/200\n'
        'Product 3,30,Third product,https://via.placeholder.com/200\n'
    )
    return Response(
        sample_csv,
        mimetype='text/csv',
        headers={"Content-disposition": "attachment; filename=sample_products.csv"}
    )

@app.route('/generate', methods=['POST'])
def generate():
    file = request.files['file']
    filename = file.filename.lower()
    if filename.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, engine='openpyxl')
    html_blocks = []
    for _, row in df.iterrows():
        html = HTML_TEMPLATE
        for col in df.columns:
            html = html.replace(f'{{{{{col}}}}}', str(row[col]))
        html_blocks.append(html)
    combined_html = '\n'.join(html_blocks)
    session['generated_html'] = combined_html
    return redirect(url_for('index'))

@app.route('/download')
def download():
    html = session.get('generated_html', None)
    if not html:
        return redirect(url_for('index'))
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    tmp.write(html.encode('utf-8'))
    tmp.close()
    return send_file(tmp.name, as_attachment=True, download_name='products.html')

if __name__ == '__main__':
    app.run(debug=True)
