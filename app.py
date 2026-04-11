from flask import Flask, redirect, url_for, render_template, send_from_directory, request, jsonify
from flask_cors import CORS
from auth import auth_bp
from tracks import tracks_bp
from favorites import favorites_bp
from survey import survey_bp
from vk_parser_bp import vk_bp
from recommendations import MusicRecommender
import logging
import os


# Настройка простого логгера
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

app.config['SECRET_KEY'] = 'your-secret-key-here'

CORS(app)

# Регистрируем blueprints
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(tracks_bp, url_prefix='/api')
app.register_blueprint(favorites_bp, url_prefix='/api')
app.register_blueprint(survey_bp)
app.register_blueprint(vk_bp)

recommender = MusicRecommender()


@app.route("/api/recommendations/<username>", methods=['GET'])
def get_recommendations(username):
    """Получить персональные рекомендации по username"""
    top_n = request.args.get('limit', 20, type=int)
    
    try:
        recommendations = recommender.get_recommendations(username, top_n)
        
        return jsonify({
            'success': True,
            'username': username,
            'recommendations': recommendations,
            'count': len(recommendations)
        })
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/similar_users/<username>", methods=['GET'])
def get_similar_users(username):
    """Получить похожих пользователей (для отладки)"""
    try:
        similar_users = recommender.find_similar_users(username, top_n=10)
        
        return jsonify({
            'success': True,
            'target_username': username,
            'similar_users': similar_users
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/user_stats/<username>", methods=['GET'])
def get_user_stats(username):
    """Получить статистику пользователя"""
    try:
        favorites_count = recommender.get_user_favorites_count(username)
        
        return jsonify({
            'success': True,
            'username': username,
            'favorites_count': favorites_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/feed/<user_name>")
def feed(user_name):
    # ВАЖНО: используем render_template, а не send_from_directory
    return render_template("index.html", username=user_name)


@app.route("/favorites/<username>")
def favorites_page(username):
    """Страница с избранными треками пользователя"""
    return render_template("favorites.html", username=username)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template('login.html')
    if request.method == "POST":
        username = request.form.get('username')
        return redirect(url_for('feed', user_name=username))


@app.route("/register")
def register():
    return render_template('register.html')


@app.route("/auth_choice/<username>")
def auth_choice(username):
    return send_from_directory('static', "auth_choice.html")


@app.route("/")
def re_route():
    return redirect(url_for('login'))


# Добавьте маршрут для JS файлов на всякий случай
@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename)


@app.route("/api/recommendations/<username>/next", methods=['GET'])
def get_next_recommendation(username):
    """Получить следующий трек для замены"""
    try:
        # Получаем текущие рекомендации
        current_recommendations = request.args.get('current_ids', '').split(',')
        current_ids = [int(id) for id in current_recommendations if id]
        
        # Получаем новые рекомендации
        recommendations = recommender.get_recommendations(username, top_n=30)
        
        # Находим трек, которого нет в текущих
        for track in recommendations:
            if track['id'] not in current_ids:
                return jsonify({
                    'success': True,
                    'track': track
                })
        
        return jsonify({'success': False, 'message': 'Нет новых треков'}), 404
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    


    # Добавьте эти маршруты в app.py после существующих

@app.route("/api/recommendations/mood/<username>/<mood>", methods=['GET'])
def get_mood_recommendations(username, mood):
    """Получить рекомендации по настроению"""
    top_n = request.args.get('limit', 10, type=int)
    
    try:
        recommendations = recommender.get_mood_based_recommendations(username, mood, top_n)
        
        return jsonify({
            'success': True,
            'username': username,
            'mood': mood,
            'recommendations': recommendations,
            'count': len(recommendations)
        })
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций по настроению: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/recommendations/diverse/<username>", methods=['GET'])
def get_diverse_recommendations(username):
    """Получить разнообразные рекомендации (из разных жанров)"""
    top_n = request.args.get('limit', 20, type=int)
    
    try:
        recommendations = recommender.get_diverse_recommendations(username, top_n)
        
        return jsonify({
            'success': True,
            'username': username,
            'recommendations': recommendations,
            'count': len(recommendations)
        })
    except Exception as e:
        logger.error(f"Ошибка получения разнообразных рекомендаций: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)