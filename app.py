from flask import Flask, render_template, request, redirect, session
import sqlite3
import pytesseract
import cv2
import numpy as np
from PIL import Image
import os

app = Flask(__name__)
app.secret_key = 'secret123'

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT,
            password TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            filename TEXT,
            text TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
        result = c.fetchone()
        conn.close()

        if result:
            session['user'] = user
            return redirect('/dashboard')
        else:
            return "Invalid login"

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?, ?)", (user, pwd))
        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    text = ""
    current_user = session.get('user')

    if not current_user:
        return redirect('/')   # 🚨 IMPORTANT FIX

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        file = request.files.get('image')

        if file:
            try:
                img = Image.open(file).convert("RGB")
                img = np.array(img)
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

                gray = cv2.GaussianBlur(gray, (3,3), 0)
                _, gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

                lang = request.form.get('lang', 'eng')
                text = pytesseract.image_to_string(gray, lang=f"eng+{lang}")

                c.execute(
                    "INSERT INTO history (username, filename, text) VALUES (?, ?, ?)",
                    (current_user, file.filename, text)
                )
                conn.commit()

            except Exception as e:
                text = f"OCR Error: {str(e)}"

    c.execute("SELECT filename, text FROM history WHERE username=?", (current_user,))
    history = c.fetchall()

    conn.close()

    return render_template('dashboard.html', text=text, history=history, user=current_user)
@app.route('/clear_history')
def clear_history():
    current_user = session.get('user')

    if not current_user:
        return redirect('/')   # 🚨 IMPORTANT

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("DELETE FROM history WHERE username=?", (current_user,))
    conn.commit()
    conn.close()

    return redirect('/dashboard')


if __name__ == '__main__':
    app.run(debug=True)