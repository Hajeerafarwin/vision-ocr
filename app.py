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

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        file = request.files['image']

        if file:
            img = Image.open(file)
            img = np.array(img)

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # enlarge image
            gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

            # remove noise
            gray = cv2.GaussianBlur(gray, (3, 3), 0)

            # make text darker / background cleaner
            gray = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)[1]

            h, w = gray.shape
            gray = gray[25:h-35, 0:w]

            lang = request.form.get('lang', 'eng')

            custom_config = r'--oem 3 --psm 11'
            text = pytesseract.image_to_string(gray, lang=lang, config=custom_config)  

            c.execute(
                "INSERT INTO history (username, filename, text) VALUES (?, ?, ?)",
                (current_user, file.filename, text)
            )
            conn.commit()

    c.execute("SELECT filename, text FROM history WHERE username=? ORDER BY id DESC", (current_user,))
    history = c.fetchall()

    conn.close()

    return render_template('dashboard.html', text=text, history=history, user=current_user)


if __name__ == '__main__':
    app.run(debug=True)