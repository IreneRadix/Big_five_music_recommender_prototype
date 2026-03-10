from flask import Flask, redirect, url_for, render_template, send_from_directory, request
from flask_cors import CORS
from auth import auth_bp
from tracks import tracks_bp
from favorites import favorites_bp
import os

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Нужно добавить в app.py
app.config['SECRET_KEY'] = 'your-secret-key-here'  # В продакшне использовать переменные окружения

CORS(app)

# Регистрируем blueprints
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(tracks_bp, url_prefix='/api')
app.register_blueprint(favorites_bp, url_prefix='/api')


@app.route("/feed/<user_name>")
def feed(user_name):
    return render_template("index.html", 
                         name=user_name, 
                         title="Приветствие")

@app.route("/login", methods = ['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template('login.html')
    if request.method == "POST":
        username = request['username']
        return redirect(url_for('feed', user_name = username))



@app.route("/")
def re_route():
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)