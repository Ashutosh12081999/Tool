from flask import Flask, request, send_file, render_template_string, session, redirect, url_for, Response
import pandas as pd
import tempfile
import os
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = 'change_this_secret_key'

USERS_FILE = 'users.json'

TEMPLATE_DIR = 'templates/multi'
TEMPLATE_INDEX = os.path.join(TEMPLATE_DIR, 'template_index.json')
TEMPLATE_VERSION_DIR = 'templates/versions'

def get_template_list():
    if not os.path.exists(TEMPLATE_INDEX):
        return {'default': 'sample_template.html'}
    with open(TEMPLATE_INDEX, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_template_list(tlist):
    with open(TEMPLATE_INDEX, 'w', encoding='utf-8') as f:
        json.dump(tlist, f, indent=2)

def get_template_path(tname):
    return os.path.join(TEMPLATE_DIR, tname)

def load_template(tname=None):
    tlist = get_template_list()
    if tname is None:
        tname = tlist.get('selected', 'default')
    fname = tlist.get(tname, tname)
    path = get_template_path(fname)
    if not os.path.exists(path):
        return '<div class="product">\n  <h2>{{title}}</h2>\n  <img src="{{image_url}}" alt="{{title}}" style="max-width:200px;"/>\n  <p><strong>Price:</strong> ${{price}}</p>\n  <p><strong>Description:</strong> {{description}}</p>\n</div>'
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def save_template(content, tname=None):
    tlist = get_template_list()
    if tname is None:
        tname = tlist.get('selected', 'default')
    fname = tlist.get(tname, tname)
    path = get_template_path(fname)
    # Save version
    if not os.path.exists(TEMPLATE_VERSION_DIR):
        os.makedirs(TEMPLATE_VERSION_DIR)
    import datetime
    vfile = os.path.join(TEMPLATE_VERSION_DIR, f'{fname}_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.html')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            old = f.read()
        with open(vfile, 'w', encoding='utf-8') as f:
            f.write(old)
    # Save new
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def list_template_versions(tname=None):
    tlist = get_template_list()
    if tname is None:
        tname = tlist.get('selected', 'default')
    fname = tlist.get(tname, tname)
    prefix = f'{fname}_'
    if not os.path.exists(TEMPLATE_VERSION_DIR):
        return []
    return [f for f in os.listdir(TEMPLATE_VERSION_DIR) if f.startswith(prefix)]

def restore_template_version(version_file, tname=None):
    tlist = get_template_list()
    if tname is None:
        tname = tlist.get('selected', 'default')
    fname = tlist.get(tname, tname)
    path = get_template_path(fname)
    vpath = os.path.join(TEMPLATE_VERSION_DIR, version_file)
    if os.path.exists(vpath):
        with open(vpath, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

def load_users():
    if not os.path.exists(USERS_FILE):
        return {'admin': 'password123'}
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('username') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        if username in users and users[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password.'
    return f'''
    <html><head><title>Login</title>
    <style>
    body {{ font-family: Arial, sans-serif; background: #e0eafc; }}
    .login-container {{ max-width: 350px; margin: 80px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 12px #b0c4de; padding: 32px; }}
    h2 {{ color: #2c3e50; }}
    .input {{ width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #ccc; }}
    .btn {{ background: #3498db; color: #fff; border: none; padding: 10px 18px; border-radius: 5px; cursor: pointer; width: 100%; }}
    .btn:hover {{ background: #217dbb; }}
    .error {{ color: #e74c3c; margin-bottom: 10px; }}
    </style></head><body>
    <div class="login-container">
    <h2>Login</h2>
    <form method="post">
      <input class="input" type="text" name="username" placeholder="Username" required><br>
      <input class="input" type="password" name="password" placeholder="Password" required><br>
      <button class="btn" type="submit">Login</button>
    </form>
    {f'<div class="error">{error}</div>' if error else ''}
    </div></body></html>
    '''

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('generated_html', None)
    return redirect(url_for('login'))



@app.route('/')
@login_required
def index():
    html_file = session.get('generated_html_file', None)
    uploaded_file_name = session.get('uploaded_file_name', '')
    code_block = ''
    download_block = ''
    clear_block = ''
    dashboard_block = ''
    # Only one logout button, sticky top right
    logout_block = '<a href="/logout" class="btn btn-clear logout-btn">Logout</a>'
    if session.get('username') == 'admin':
        dashboard_block = '<a href="/dashboard" class="btn" style="background:#8e44ad;">Admin Dashboard</a>'
    if html_file and os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            html_preview = f.read()
        product_count = html_preview.count('<div class="product"')
        code_html = html_preview
        if product_count > 100:
            split_blocks = html_preview.split('<div class="product">')
            code_html = split_blocks[0]
            for i in range(1, 101):
                code_html += '<div class="product">' + split_blocks[i]
            code_html += '\n<!-- Only first 100 products shown in preview. Download for all. -->\n'
            code_block = f'''
<div class="product-count">Total products: <b>{product_count}</b></div>
<h3 style="margin-top:32px;">All HTML Code</h3>
<div class="code-block" style="max-height:400px;overflow:auto; position:relative;">
  <button class="btn copy-btn sticky-copy" onclick="copyCode()">Copy HTML Code</button>
  <pre id="htmlCode" class="code-area">{code_html.replace('<','&lt;').replace('>','&gt;')}</pre>
</div>
    <div style="color:#e67e22;font-size:1em;margin:8px 0 0 0;"><b>Note:</b> Only first 100 products are shown in preview. Download to see all products.</div>
'''
        download_block = '''<a href="/download" class="btn">Download All HTML (HTML)</a> <a href="/download-txt" class="btn">Download as TXT</a>'''
        clear_block = '''<a href="/clear" class="btn btn-clear">Clear HTML</a>'''
        uploaded_file_block = f'<div id="uploaded-file" style="color:#2980b9;margin-bottom:10px;font-weight:bold;">Selected: {uploaded_file_name}</div>'
    else:
        code_block = ''
        download_block = ''
        clear_block = ''
        uploaded_file_block = '<div id="uploaded-file" style="color:#2980b9;margin-bottom:10px;"></div>'
    # JS code as a raw string to avoid f-string/curly brace issues
    js_code = '''
function copyCode() {
    var code = document.getElementById('htmlCode').innerText;
    var textarea = document.createElement('textarea');
    textarea.value = code.replace(/&lt;/g, '<').replace(/&gt;/g, '>');
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    alert('HTML code copied to clipboard!');
}
window.addEventListener('DOMContentLoaded', function() {
    var dropArea = document.getElementById('drop-area');
    var fileInput = document.getElementById('file-input');
    var progressBar = document.getElementById('progress-bar-fill');
    var form = document.getElementById('upload-form');
    var uploadedFile = document.getElementById('uploaded-file');
    if(dropArea && fileInput && form) {
        dropArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            dropArea.classList.add('dragover');
        });
        dropArea.addEventListener('dragleave', function(e) {
            dropArea.classList.remove('dragover');
        });
        dropArea.addEventListener('drop', function(e) {
            e.preventDefault();
            dropArea.classList.remove('dragover');
            if(e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                if(uploadedFile) uploadedFile.innerText = 'Selected: ' + fileInput.files[0].name;
            }
        });
        dropArea.addEventListener('click', function() {
            fileInput.click();
        });
        fileInput.addEventListener('change', function(e) {
            if(fileInput.files.length && uploadedFile) uploadedFile.innerText = 'Selected: ' + fileInput.files[0].name;
        });
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            var file = fileInput.files[0];
            if(!file) { alert('Please select a file.'); return; }
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/generate', true);
            xhr.upload.onprogress = function(e) {
                if(e.lengthComputable) {
                    var percent = Math.round((e.loaded/e.total)*100);
                    progressBar.style.width = percent+'%';
                    progressBar.innerText = percent+'%';
                }
            };
            xhr.onload = function() {
                progressBar.style.width = '0%';
                progressBar.innerText = '';
                if(xhr.status == 200) {
                    window.location.reload();
                } else {
                    alert('Upload failed: ' + xhr.responseText);
                }
            };
            var formData = new FormData();
            formData.append('file', file);
            xhr.send(formData);
        });
    }
});
'''
    return f'''
<html>
<head>
<title>Product HTML Generator</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(120deg,#e0eafc,#cfdef3); margin:0; padding:0; }}
    .container {{ max-width: 800px; margin: 40px auto; background: #fff; border-radius: 16px; box-shadow: 0 4px 24px #b0c4de; padding: 40px 36px 36px 36px; transition: box-shadow 0.3s; }}
    h1 {{ color: #2c3e50; font-size:2.2em; letter-spacing:1px; }}
    .btn {{ display:inline-block; background:#3498db; color:#fff; padding:10px 18px; border-radius:5px; text-decoration:none; margin-top:10px; border:none; cursor:pointer; font-size:1em; transition: background 0.2s, box-shadow 0.2s; box-shadow:0 2px 8px #cce; }}
    .btn:hover {{ background:#217dbb; box-shadow:0 4px 16px #aac; }}
    .btn-clear {{ background:#e74c3c; margin-left:10px; }}
    .btn-clear:hover {{ background:#c0392b; }}
    .logout-btn {{ position: absolute; top: 30px; right: 40px; z-index: 10; }}
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
    .drop-area {{ border:2px dashed #3498db; border-radius:10px; padding:30px; text-align:center; color:#3498db; margin-bottom:18px; background:#f8fbff; transition:background 0.2s; }}
    .drop-area.dragover {{ background:#e0eafc; }}
    .progress-bar-bg {{ width:100%; background:#eee; border-radius:8px; margin:10px 0; height:18px; }}
    .progress-bar-fill {{ height:18px; background:#27ae60; border-radius:8px; width:0%; transition:width 0.3s; color:#fff; text-align:center; font-size:0.95em; }}
    @media (max-width: 600px) {{
        .container {{ padding: 10px; }}
        h1 {{ font-size:1.3em; }}
        .btn {{ font-size:0.95em; padding:8px 10px; }}
        .drop-area {{ padding:16px; font-size:0.98em; }}
    }}
</style>
<script>{js_code}</script>
</head>
<body>
<div class="container" style="position:relative;">
{logout_block}
<h1>Product HTML Generator</h1>
{dashboard_block}
<a href="/download-sample" class="btn">Download Sample CSV</a><br><br>
<form id="upload-form" action="/generate" method="post" enctype="multipart/form-data" style="margin-bottom:24px;">
  <div id="drop-area" class="drop-area">Drag & Drop Excel/CSV file here or click to select.<br><input id="file-input" type="file" name="file" accept=".xlsx,.xls,.csv" required style="display:none;" onclick="event.stopPropagation();" /></div>
  <div class="progress-bar-bg"><div id="progress-bar-fill" class="progress-bar-fill"></div></div>
  <button type="submit" class="btn" style="margin-top:12px;">Upload & Generate HTML</button>
</form>
{uploaded_file_block}
<div id="validation-errors" style="color:#e74c3c;margin-bottom:10px;"></div>
{code_block}
{download_block}
{clear_block}
</div>
</body>
</html>
'''
@app.route('/download')
def download():
    html_file = session.get('generated_html_file', None)
    if not html_file or not os.path.exists(html_file):
        return redirect(url_for('index'))
    return send_file(html_file, as_attachment=True, download_name='products.html')

@app.route('/download-txt')
def download_txt():
    html_file = session.get('generated_html_file', None)
    if not html_file or not os.path.exists(html_file):
        return redirect(url_for('index'))
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    tmp.write(html.encode('utf-8'))
    tmp.close()
    return send_file(tmp.name, as_attachment=True, download_name='products.txt')

@app.route('/clear')
def clear():
    html_file = session.pop('generated_html_file', None)
    if html_file and os.path.exists(html_file):
        try:
            os.remove(html_file)
        except Exception:
            pass
    session.pop('uploaded_file_name', None)
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
@admin_required
def dashboard():
    users = load_users()
    tlist = get_template_list()
    selected = tlist.get('selected', 'default')
    template_content = load_template(selected)
    msg = ''
    if request.method == 'POST':
        if 'template' in request.form:
            save_template(request.form['template'], selected)
            template_content = request.form['template']
            msg = 'Template updated!'
        elif 'add_user' in request.form:
            new_user = request.form.get('new_user').strip()
            new_pass = request.form.get('new_pass').strip()
            if new_user and new_pass and new_user not in users:
                users[new_user] = new_pass
                save_users(users)
                msg = f'User {new_user} added.'
            else:
                msg = 'Invalid or duplicate username.'
        elif 'del_user' in request.form:
            del_user = request.form.get('del_user')
            if del_user and del_user in users and del_user != 'admin':
                users.pop(del_user)
                save_users(users)
                msg = f'User {del_user} deleted.'
            else:
                msg = 'Cannot delete admin or invalid user.'
        elif 'select_template' in request.form:
            tlist['selected'] = request.form['select_template']
            save_template_list(tlist)
            selected = tlist['selected']
            template_content = load_template(selected)
            msg = f'Switched to template {selected}.'
        elif 'add_template' in request.form:
            new_tname = request.form.get('new_template_name').strip()
            if new_tname and new_tname not in tlist:
                fname = new_tname + '.html'
                tlist[new_tname] = fname
                save_template_list(tlist)
                save_template('<div class="product">\n  <h2>{{title}}</h2>\n  <img src="{{image_url}}" alt="{{title}}" style="max-width:200px;"/>\n  <p><strong>Price:</strong> ${{price}}</p>\n  <p><strong>Description:</strong> {{description}}</p>\n</div>', new_tname)
                msg = f'Template {new_tname} added.'
            else:
                msg = 'Invalid or duplicate template name.'
        elif 'restore_version' in request.form:
            version_file = request.form.get('restore_version')
            restore_template_version(version_file, selected)
            template_content = load_template(selected)
            msg = f'Restored version {version_file}.'
        users = load_users()
    # Always build user_list for both GET and POST
    user_list = ''
    for u in users:
        if u == 'admin':
            user_list += f'<li>{u} (admin)</li>'
        else:
            user_list += (
                f'<li>{u} '
                f'<form method="post" style="display:inline;">'
                f'  <input type="hidden" name="del_user" value="{u}">'
                f'  <button class="btn" style="background:#e74c3c;padding:2px 8px;font-size:0.9em;" '
                f'    onclick="return confirm(\'Delete user {u}?\')">Delete</button>'
                f'</form></li>'
            )
        # Template selection UI
        template_options = ''.join([
                f'<option value="{k}" {"selected" if k==selected else ""}>{k}</option>'
                for k in tlist if k not in ["selected"]
        ])
        # Version history UI
        versions = list_template_versions(selected)
        version_list = ''.join([
                f'<form method="post" style="display:inline;"><input type="hidden" name="restore_version" value="{v}"><button class="btn" type="submit">Restore {v}</button></form>'
                for v in versions
        ])
        return f'''
        <html><head><title>Admin Dashboard</title>
        <style>
        body {{ font-family: Arial, sans-serif; background: #f5f6fa; }}
        .container {{ max-width: 700px; margin: 40px auto; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px #b0c4de; padding: 32px; }}
        h2 {{ color: #8e44ad; }}
        textarea {{ width:100%; min-height:180px; font-family:monospace; font-size:15px; border-radius:6px; border:1px solid #ccc; padding:10px; margin-bottom:10px; }}
        .btn {{ background:#8e44ad; color:#fff; border:none; padding:8px 16px; border-radius:5px; cursor:pointer; margin-top:8px; }}
        .btn:hover {{ background:#5e3370; }}
        .user-list {{ margin:18px 0; }}
        .msg {{ color:#27ae60; margin-bottom:10px; }}
        .template-select {{ margin-bottom: 10px; }}
        </style></head><body>
        <div class="container">
        <h2>Admin Dashboard</h2>
        <a href="/" class="btn" style="background:#3498db;">Back to Home</a>
        <h3>Templates</h3>
        <form method="post" class="template-select">
            <select name="select_template">{template_options}</select>
            <button class="btn" type="submit">Switch</button>
        </form>
        <form method="post" style="margin-bottom:10px;">
            <input type="text" name="new_template_name" placeholder="New template name">
            <button class="btn" name="add_template" value="1" type="submit">Add Template</button>
        </form>
        <form method="post">
            <textarea name="template">{template_content}</textarea><br>
            <button class="btn" type="submit">Save Template</button>
        </form>
        <div style="margin:10px 0;">{version_list}</div>
        <h3>Manage Users</h3>
        <form method="post" style="margin-bottom:10px;">
            <input type="text" name="new_user" placeholder="Username" required>
            <input type="password" name="new_pass" placeholder="Password" required>
            <button class="btn" name="add_user" value="1" type="submit">Add User</button>
        </form>
        <ul class="user-list">{user_list}</ul>
        {f'<div class="msg">{msg}</div>' if msg else ''}
        </div></body></html>
        '''

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
    tlist = get_template_list()
    selected = tlist.get('selected', 'default')
    template = load_template(selected)
    # Data validation
    required_cols = ['title', 'price', 'description', 'image_url']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return f"Missing columns: {', '.join(missing)}", 400
    # Performance: process in chunks if large
    html_blocks = []
    chunk_size = 2000 if len(df) > 5000 else len(df)
    for start in range(0, len(df), chunk_size):
        chunk = df.iloc[start:start+chunk_size]
        for _, row in chunk.iterrows():
            html = template
            for col in df.columns:
                html = html.replace(f'{{{{{col}}}}}', str(row[col]))
            html_blocks.append(html)
    combined_html = '\n'.join(html_blocks)
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    tmp.write(combined_html.encode('utf-8'))
    tmp.close()
    session['generated_html_file'] = tmp.name
    session['uploaded_file_name'] = filename
    return '', 200

if __name__ == '__main__':
    app.run(debug=True)
