from flask import Blueprint, request, jsonify
from vk_parser import parse_vk_data_api
from database import get_db_connection

vk_bp = Blueprint('vk', __name__)


def save_user_vk_data(data):
    conn = get_db_connection()
    cur = conn.cursor()


@vk_bp.route('/api/vk_parse', methods=['POST'])
def vk_parse():
    try:
        data = request.get_json()
        vk_url = data.get('vk_url')
        consent = data.get('consent', False)
        
        if not vk_url:
            return jsonify({'error': 'VK URL не указан'}), 400
        
        if not consent:
            return jsonify({'error': 'Необходимо согласие на обработку данных'}), 400
        
        # Парсим данные
        user_data = parse_vk_data_api(vk_url, consent)
        
        # Здесь вы можете сохранить данные в базу
        #save_user_vk_data(user_data)

        
        return jsonify({
            'success': True,
            'data': user_data
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:

        return jsonify({'error': 'Ошибка при обработке VK данных'}), 500