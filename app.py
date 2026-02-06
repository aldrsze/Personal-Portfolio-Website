from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import sqlite3
import json
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta

APP_ENV = os.environ.get("APP_ENV", "development").lower()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_insecure_change_me")

if APP_ENV == "production" and app.secret_key == "dev_insecure_change_me":
    raise RuntimeError("SECRET_KEY must be set in production")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(APP_ENV == "production"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    
    # Table for content sections
    c.execute('''CREATE TABLE IF NOT EXISTS content 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  section TEXT NOT NULL,
                  title TEXT,
                  description TEXT,
                  image_url TEXT,
                  link_url TEXT,
                  order_num INTEGER DEFAULT 0)''')
    
    # Table for personal info
    c.execute('''CREATE TABLE IF NOT EXISTS personal_info 
                 (id INTEGER PRIMARY KEY,
                  name TEXT,
                  intro TEXT,
                  career_objective TEXT,
                  email TEXT,
                  phone TEXT,
                  address TEXT,
                  age TEXT,
                  birthday TEXT,
                  gender TEXT,
                  civil_status TEXT,
                  nationality TEXT,
                  religion TEXT,
                  language TEXT,
                  height TEXT,
                  weight TEXT,
                  facebook TEXT,
                  github TEXT,
                  linkedin TEXT,
                  about_website TEXT,
                  profile_image TEXT)''')
    
    # Table for stats (Visits, Hearts)
    c.execute('''CREATE TABLE IF NOT EXISTS stats 
                 (name TEXT PRIMARY KEY, count INTEGER)''')
    
    # Table for admin credentials
    c.execute('''CREATE TABLE IF NOT EXISTS admin_users 
                 (id INTEGER PRIMARY KEY,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL)''')
    
    # Table for theme settings
    c.execute('''CREATE TABLE IF NOT EXISTS theme_settings 
                 (id INTEGER PRIMARY KEY,
                  theme_name TEXT DEFAULT 'rose',
                  bg_gradient_start TEXT DEFAULT '#ffe4e6',
                  bg_gradient_end TEXT DEFAULT '#fecaca',
                  accent_color TEXT DEFAULT '#f43f5e',
                  accent_hover TEXT DEFAULT '#e11d48')''')
    
    # Add missing columns if they don't exist (for existing databases)
    columns_to_add = [
        ("phone", "TEXT"),
        ("address", "TEXT"),
        ("age", "TEXT"),
        ("birthday", "TEXT"),
        ("gender", "TEXT"),
        ("civil_status", "TEXT"),
        ("nationality", "TEXT"),
        ("religion", "TEXT"),
        ("language", "TEXT"),
        ("height", "TEXT"),
        ("weight", "TEXT"),
        ("profile_image", "TEXT")
    ]
    for column_name, column_type in columns_to_add:
        try:
            c.execute(f"SELECT {column_name} FROM personal_info LIMIT 1")
        except sqlite3.OperationalError:
            c.execute(f"ALTER TABLE personal_info ADD COLUMN {column_name} {column_type}")

    # Insert default data if empty
    c.execute("INSERT OR IGNORE INTO stats (name, count) VALUES ('visits', 0)")
    c.execute("INSERT OR IGNORE INTO stats (name, count) VALUES ('profile_clicks', 0)")
    c.execute("INSERT OR IGNORE INTO stats (name, count) VALUES ('likes', 0)")
    c.execute("INSERT OR IGNORE INTO theme_settings (id, theme_name) VALUES (1, 'rose')")
    
    # Insert default personal info
    c.execute('''INSERT OR IGNORE INTO personal_info 
                 (id, name, intro, career_objective, email, phone, address, age, birthday, gender,
                  civil_status, nationality, religion, language, height, weight,
                  facebook, github, linkedin, about_website) 
                 VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (
                  'Aldrin Miguel A. Jariel',
                  "Hi! I'm Aldrin Miguel A. Jariel!",
                  "Motivated and hardworking individual seeking an opportunity to gain practical experience and develop new skills. I am eager to learn, able to follow instructions, and committed to performing tasks responsibly and efficiently. My goal is to improve my communication, teamwork, and problem-solving skills while contributing positively to the company and growing as a reliable and productive member of the team.",
                  'aldrinjariel0@gmail.com',
                  '09955954094',
                  '12-D Legislative St., Batasan Hills, Quezon City, 1126',
                  '18',
                  'October 15, 2007',
                  'Male',
                  'Single',
                  'Filipino',
                  'Roman Catholic',
                  'English, Filipino',
                  '167 cm',
                  '56 kg',
                  '',
                  '',
                  '',
                  'This portfolio highlights my background, achievements, and projects.'
              ))
    
    # Insert skills if empty
    skills_count = c.execute("SELECT COUNT(*) FROM content WHERE section = 'skills'").fetchone()[0]
    if skills_count == 0:
        skills_data = [
            ('Communication Skills', 'Clear and effective verbal and written communication.'),
            ('Responsible', 'Dependable and committed to completing tasks on time.'),
            ('Adaptability', 'Quick to adjust to new tools and requirements.'),
            ('Problem-Solving', 'Analytical approach to resolving technical issues.'),
            ('Teamwork', 'Collaborates well with peers and cross-functional teams.'),
            ('Time Management', 'Organized and efficient in prioritizing tasks.'),
            ('Fast Learner', 'Eager to learn and apply new technologies quickly.')
        ]
        for index, (title, description) in enumerate(skills_data, start=1):
            c.execute('''INSERT INTO content (section, title, description, order_num)
                         VALUES ('skills', ?, ?, ?)''', (title, description, index))

    # Insert default tech stack if empty
    tech_count = c.execute("SELECT COUNT(*) FROM content WHERE section = 'tech_stack'").fetchone()[0]
    if tech_count == 0:
        c.execute('''INSERT INTO content (section, title, description, order_num) 
                     VALUES ('tech_stack', 'VS Code', 'Primary code editor', 1)''')
        c.execute('''INSERT INTO content (section, title, description, order_num) 
                     VALUES ('tech_stack', 'Python', 'Backend programming language', 2)''')
        c.execute('''INSERT INTO content (section, title, description, order_num) 
                     VALUES ('tech_stack', 'Flask', 'Lightweight web framework', 3)''')
        c.execute('''INSERT INTO content (section, title, description, order_num) 
                     VALUES ('tech_stack', 'SQLite', 'Embedded database', 4)''')

    # Insert awards if empty
    awards_count = c.execute("SELECT COUNT(*) FROM content WHERE section = 'awards'").fetchone()[0]
    if awards_count == 0:
        awards_data = [
            ('With Honors, STEM-11', '2024 — Mary The Queen College of Quezon City'),
            ('With High Honors, STEM-12', '2025 — Mary The Queen College of Quezon City')
        ]
        for index, (title, description) in enumerate(awards_data, start=1):
            c.execute('''INSERT INTO content (section, title, description, order_num)
                         VALUES ('awards', ?, ?, ?)''', (title, description, index))

    # Insert education if empty
    education_count = c.execute("SELECT COUNT(*) FROM content WHERE section = 'education'").fetchone()[0]
    if education_count == 0:
        education_data = [
            ('Quezon City University — BS in Information Technology', 'Tertiary • 2025 - Present'),
            ('Batasan Hills National Highschool / Mary The Queen College of Quezon City', 'Secondary • 2019 - 2025'),
            ('San Diego Elementary School', 'Primary • 2012 - 2019')
        ]
        for index, (title, description) in enumerate(education_data, start=1):
            c.execute('''INSERT INTO content (section, title, description, order_num)
                         VALUES ('education', ?, ?, ?)''', (title, description, index))

    # Insert project if empty
    projects_count = c.execute("SELECT COUNT(*) FROM content WHERE section = 'projects'").fetchone()[0]
    if projects_count == 0:
        project_description = (
            'Capstone Project (Oct–Dec 2025). Built a professional inventory system for small businesses with '
            'sales tracking, QR code integration, real-time analytics, automatic profit calculation, and '
            'low-stock alerts. Led system programming, database architecture, and technical documentation.'
        )
        c.execute('''INSERT INTO content (section, title, description, order_num)
                     VALUES ('projects', 'SmartStock Inventory Management System', ?, 1)''',
                  (project_description,))
    
    # Insert default admin user (username: admin, password: 1234)
    c.execute("SELECT * FROM admin_users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
                 ('admin', generate_password_hash('1234')))
    
    # Seed personal info if still using placeholders
    existing = c.execute("SELECT phone FROM personal_info WHERE id = 1").fetchone()
    if existing and (existing[0] is None or str(existing[0]).strip() == ""):
        c.execute('''UPDATE personal_info SET
                     name = ?, intro = ?, career_objective = ?, email = ?, phone = ?, address = ?,
                     age = ?, birthday = ?, gender = ?, civil_status = ?, nationality = ?,
                     religion = ?, language = ?, height = ?, weight = ?, about_website = ?
                     WHERE id = 1''',
                  (
                      'Aldrin Miguel A. Jariel',
                      "Hi! I'm Aldrin Miguel A. Jariel!",
                      "Motivated and hardworking individual seeking an opportunity to gain practical experience and develop new skills. I am eager to learn, able to follow instructions, and committed to performing tasks responsibly and efficiently. My goal is to improve my communication, teamwork, and problem-solving skills while contributing positively to the company and growing as a reliable and productive member of the team.",
                      'aldrinjariel0@gmail.com',
                      '09955954094',
                      '12-D Legislative St., Batasan Hills, Quezon City, 1126',
                      '18',
                      'October 15, 2007',
                      'Male',
                      'Single',
                      'Filipino',
                      'Roman Catholic',
                      'English, Filipino',
                      '167 cm',
                      '56 kg',
                      'This portfolio highlights my background, achievements, and projects.'
                  ))
    
    conn.commit()
    conn.close()

# Initialize DB on start
init_db()

# --- Helper Functions ---
def get_db_connection():
    conn = sqlite3.connect('portfolio.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_portfolio_data():
    conn = get_db_connection()
    
    # Get personal info
    personal_info = conn.execute('SELECT * FROM personal_info WHERE id = 1').fetchone()
    
    # Get content sections
    skills = conn.execute("SELECT * FROM content WHERE section = 'skills' ORDER BY order_num").fetchall()
    tech_stack = conn.execute("SELECT * FROM content WHERE section = 'tech_stack' ORDER BY order_num").fetchall()
    projects = conn.execute("SELECT * FROM content WHERE section = 'projects' ORDER BY order_num").fetchall()
    awards = conn.execute("SELECT * FROM content WHERE section = 'awards' ORDER BY order_num").fetchall()
    education = conn.execute("SELECT * FROM content WHERE section = 'education' ORDER BY order_num").fetchall()
    
    # Get stats
    visits = conn.execute("SELECT count FROM stats WHERE name='visits'").fetchone()[0]
    profile_clicks = conn.execute("SELECT count FROM stats WHERE name='profile_clicks'").fetchone()[0]
    likes = conn.execute("SELECT count FROM stats WHERE name='likes'").fetchone()[0]
    
    # Get theme settings
    theme = conn.execute("SELECT * FROM theme_settings WHERE id=1").fetchone()
    theme_dict = {
        'theme_name': theme[1] if theme else 'rose',
        'bg_gradient_start': theme[2] if theme else '#ffe4e6',
        'bg_gradient_end': theme[3] if theme else '#fecaca',
        'accent_color': theme[4] if theme else '#f43f5e',
        'accent_hover': theme[5] if theme else '#e11d48'
    }
    
    conn.close()
    
    return {
        'personal_info': personal_info,
        'skills': skills,
        'tech_stack': tech_stack,
        'projects': projects,
        'awards': awards,
        'education': education,
        'visits': visits,
        'profile_clicks': profile_clicks,
        'likes': likes,
        'theme': theme_dict
    }

# --- Routes ---

@app.route('/')
def home():
    # Increment visit counter
    conn = get_db_connection()
    conn.execute("UPDATE stats SET count = count + 1 WHERE name = 'visits'")
    conn.commit()
    conn.close()
    
    data = get_portfolio_data()
    return render_template('index.html', data=data)

@app.route('/profile-click', methods=['POST'])
def profile_click():
    conn = get_db_connection()
    conn.execute("UPDATE stats SET count = count + 1 WHERE name = 'profile_clicks'")
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/like', methods=['POST'])
def like():
    conn = get_db_connection()
    conn.execute("UPDATE stats SET count = count + 1 WHERE name = 'likes'")
    conn.commit()
    likes = conn.execute("SELECT count FROM stats WHERE name='likes'").fetchone()[0]
    conn.close()
    return jsonify({'likes': likes})

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Get theme settings for login page styling
    conn = get_db_connection()
    theme = conn.execute("SELECT * FROM theme_settings WHERE id=1").fetchone()
    theme_dict = {
        'bg_gradient_start': theme[2] if theme else '#ffe4e6',
        'bg_gradient_end': theme[3] if theme else '#fecaca',
        'accent_color': theme[4] if theme else '#f43f5e',
        'accent_hover': theme[5] if theme else '#e11d48'
    }
    conn.close()
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM admin_users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials', 'error')
            return render_template('login.html', error=True, theme=theme_dict)
    
    return render_template('login.html', error=False, theme=theme_dict)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    data = get_portfolio_data()
    return render_template('dashboard.html', data=data)

@app.route('/admin/update-personal-info', methods=['POST'])
def update_personal_info():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Handle profile image upload
    profile_image = request.form.get('existing_profile_image')
    if 'profile_image' in request.files:
        file = request.files['profile_image']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = 'profile_' + secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            profile_image = '/static/uploads/' + filename
    
    conn.execute('''UPDATE personal_info SET 
                    name = ?, intro = ?, career_objective = ?, 
                    email = ?, facebook = ?, github = ?, linkedin = ?, about_website = ?, profile_image = ?
                    WHERE id = 1''',
                 (request.form['name'], request.form['intro'], request.form['career_objective'],
                  request.form['email'], request.form['facebook'], request.form['github'],
                  request.form['linkedin'], request.form['about_website'], profile_image))
    conn.commit()
    conn.close()
    
    flash('Personal information updated successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/update-content/<section>', methods=['POST'])
def update_content(section):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    content_id = request.form.get('id')
    title = request.form.get('title')
    description = request.form.get('description')
    
    conn = get_db_connection()
    if content_id:
        # Update existing content
        conn.execute('UPDATE content SET title = ?, description = ? WHERE id = ?',
                    (title, description, content_id))
    else:
        # Insert new content
        conn.execute('INSERT INTO content (section, title, description) VALUES (?, ?, ?)',
                    (section, title, description))
    conn.commit()
    conn.close()
    
    flash(f'{section.title()} updated successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete-content/<int:content_id>', methods=['POST'])
def delete_content(content_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM content WHERE id = ?', (content_id,))
    conn.commit()
    conn.close()
    
    flash('Content deleted successfully!', 'success')
    return redirect(url_for('admin'))

# New batch update routes
@app.route('/admin/batch-update-skills', methods=['POST'])
def batch_update_skills():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get form data
    updates = json.loads(request.form.get('updates', '[]'))
    deletes = json.loads(request.form.get('deletes', '[]'))
    
    # Process updates
    for item in updates:
        if item['id'] == 'new':
            conn.execute('INSERT INTO content (section, title, description) VALUES (?, ?, ?)',
                        ('skills', item['title'], item['description']))
        else:
            conn.execute('UPDATE content SET title = ?, description = ? WHERE id = ?',
                        (item['title'], item['description'], item['id']))
    
    # Process deletes
    for item_id in deletes:
        conn.execute('DELETE FROM content WHERE id = ?', (item_id,))
    
    conn.commit()
    conn.close()
    
    flash('Skills updated successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/batch-update-tech', methods=['POST'])
def batch_update_tech():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    updates = json.loads(request.form.get('updates', '[]'))
    deletes = json.loads(request.form.get('deletes', '[]'))
    
    for item in updates:
        # Handle image upload
        image_url = item.get('image_url', '')
        file_key = f"tech_image_{item['id']}"
        
        if file_key in request.files:
            file = request.files[file_key]
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"tech_{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_url = f"/static/uploads/{filename}"
        
        if item['id'] == 'new':
            conn.execute('INSERT INTO content (section, title, description, image_url) VALUES (?, ?, ?, ?)',
                        ('tech_stack', item['title'], item['description'], image_url))
        else:
            if image_url:
                conn.execute('UPDATE content SET title = ?, description = ?, image_url = ? WHERE id = ?',
                            (item['title'], item['description'], image_url, item['id']))
            else:
                conn.execute('UPDATE content SET title = ?, description = ? WHERE id = ?',
                            (item['title'], item['description'], item['id']))
    
    for item_id in deletes:
        conn.execute('DELETE FROM content WHERE id = ?', (item_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/admin/batch-update-projects', methods=['POST'])
def batch_update_projects():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    updates = json.loads(request.form.get('updates', '[]'))
    deletes = json.loads(request.form.get('deletes', '[]'))
    images = request.files
    
    for item in updates:
        image_url = item.get('image_url', '')
        
        # Handle image upload for this project
        image_key = f"project_image_{item['id']}"
        if image_key in images:
            file = images[image_key]
            if file and file.filename != '' and allowed_file(file.filename):
                filename = f"project_{item['id']}_" + secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = '/static/uploads/' + filename
        
        if item['id'] == 'new':
            conn.execute('INSERT INTO content (section, title, description, image_url) VALUES (?, ?, ?, ?)',
                        ('projects', item['title'], item['description'], image_url))
        else:
            conn.execute('UPDATE content SET title = ?, description = ?, image_url = ? WHERE id = ?',
                        (item['title'], item['description'], image_url, item['id']))
    
    for item_id in deletes:
        conn.execute('DELETE FROM content WHERE id = ?', (item_id,))
    
    conn.commit()
    conn.close()
    
    flash('Projects updated successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/change-password', methods=['POST'])
def change_password():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if new_password != confirm_password:
        flash('Passwords do not match!', 'error')
        return redirect(url_for('admin'))
    
    conn = get_db_connection()
    conn.execute('UPDATE admin_users SET password_hash = ? WHERE username = ?',
                (generate_password_hash(new_password), session['username']))
    conn.commit()
    conn.close()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/update-theme', methods=['POST'])
def update_theme():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    theme_name = request.form.get('theme_name')
    
    # Theme presets
    themes = {
        'rose': {
            'bg_gradient_start': '#ffe4e6',
            'bg_gradient_end': '#fecaca',
            'accent_color': '#f43f5e',
            'accent_hover': '#e11d48'
        },
        'blue': {
            'bg_gradient_start': '#dbeafe',
            'bg_gradient_end': '#bfdbfe',
            'accent_color': '#3b82f6',
            'accent_hover': '#2563eb'
        },
        'emerald': {
            'bg_gradient_start': '#d1fae5',
            'bg_gradient_end': '#a7f3d0',
            'accent_color': '#10b981',
            'accent_hover': '#059669'
        },
        'orange': {
            'bg_gradient_start': '#fed7aa',
            'bg_gradient_end': '#fdba74',
            'accent_color': '#f97316',
            'accent_hover': '#ea580c'
        },
        'cyan': {
            'bg_gradient_start': '#cffafe',
            'bg_gradient_end': '#a5f3fc',
            'accent_color': '#06b6d4',
            'accent_hover': '#0891b2'
        },
        'purple': {
            'bg_gradient_start': '#ddd6fe',
            'bg_gradient_end': '#c4b5fd',
            'accent_color': '#8b5cf6',
            'accent_hover': '#7c3aed'
        },
        'sunset': {
            'bg_gradient_start': '#fef3c7',
            'bg_gradient_end': '#fca5a5',
            'accent_color': '#dc2626',
            'accent_hover': '#b91c1c'
        },
        'ocean': {
            'bg_gradient_start': '#e0f2fe',
            'bg_gradient_end': '#7dd3fc',
            'accent_color': '#0284c7',
            'accent_hover': '#0369a1'
        },
        'mint': {
            'bg_gradient_start': '#ecfdf5',
            'bg_gradient_end': '#a7f3d0',
            'accent_color': '#059669',
            'accent_hover': '#047857'
        },
        'lavender': {
            'bg_gradient_start': '#f5f3ff',
            'bg_gradient_end': '#ddd6fe',
            'accent_color': '#7c3aed',
            'accent_hover': '#6d28d9'
        },
        'peach': {
            'bg_gradient_start': '#fff7ed',
            'bg_gradient_end': '#fed7aa',
            'accent_color': '#ea580c',
            'accent_hover': '#c2410c'
        },
        'midnight': {
            'bg_gradient_start': '#e0e7ff',
            'bg_gradient_end': '#a5b4fc',
            'accent_color': '#4f46e5',
            'accent_hover': '#4338ca'
        },
        'ruby': {
            'bg_gradient_start': '#ffe4e6',
            'bg_gradient_end': '#fda4af',
            'accent_color': '#be123c',
            'accent_hover': '#9f1239'
        },
        'forest': {
            'bg_gradient_start': '#f0fdf4',
            'bg_gradient_end': '#86efac',
            'accent_color': '#15803d',
            'accent_hover': '#166534'
        },
        'amber': {
            'bg_gradient_start': '#fffbeb',
            'bg_gradient_end': '#fde68a',
            'accent_color': '#d97706',
            'accent_hover': '#b45309'
        },
        'sky': {
            'bg_gradient_start': '#f0f9ff',
            'bg_gradient_end': '#bae6fd',
            'accent_color': '#0369a1',
            'accent_hover': '#075985'
        },
        'fuchsia': {
            'bg_gradient_start': '#fdf4ff',
            'bg_gradient_end': '#f0abfc',
            'accent_color': '#c026d3',
            'accent_hover': '#a21caf'
        },
        'teal': {
            'bg_gradient_start': '#f0fdfa',
            'bg_gradient_end': '#5eead4',
            'accent_color': '#0f766e',
            'accent_hover': '#115e59'
        },
        'crimson': {
            'bg_gradient_start': '#fef2f2',
            'bg_gradient_end': '#fecaca',
            'accent_color': '#991b1b',
            'accent_hover': '#7f1d1d'
        },
        'slate': {
            'bg_gradient_start': '#f8fafc',
            'bg_gradient_end': '#cbd5e1',
            'accent_color': '#334155',
            'accent_hover': '#1e293b'
        },
        'lime': {
            'bg_gradient_start': '#f7fee7',
            'bg_gradient_end': '#bef264',
            'accent_color': '#65a30d',
            'accent_hover': '#4d7c0f'
        },
        'indigo': {
            'bg_gradient_start': '#eef2ff',
            'bg_gradient_end': '#a5b4fc',
            'accent_color': '#4338ca',
            'accent_hover': '#3730a3'
        }
    }
    
    if theme_name in themes:
        theme = themes[theme_name]
        conn = get_db_connection()
        conn.execute('''UPDATE theme_settings 
                       SET theme_name=?, bg_gradient_start=?, bg_gradient_end=?, 
                           accent_color=?, accent_hover=? 
                       WHERE id=1''',
                    (theme_name, theme['bg_gradient_start'], theme['bg_gradient_end'],
                     theme['accent_color'], theme['accent_hover']))
        conn.commit()
        conn.close()
        flash(f'Theme changed to {theme_name.title()}!', 'success')
    else:
        flash('Invalid theme selection!', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/change-username', methods=['POST'])
def change_username():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    new_username = request.form['new_username']
    
    conn = get_db_connection()
    try:
        conn.execute('UPDATE admin_users SET username = ? WHERE username = ?',
                    (new_username, session['username']))
        conn.commit()
        session['username'] = new_username
        flash('Username changed successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Username already exists!', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=(APP_ENV != "production"))