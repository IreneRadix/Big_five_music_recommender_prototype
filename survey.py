from flask import Blueprint, request, jsonify, current_app, send_from_directory
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

survey_bp = Blueprint('survey', __name__)

@survey_bp.route('/survey/<user_name>')
def ask_user(user_name):
    return send_from_directory('static', "survey.html")

@survey_bp.route('/api/survey', methods = ['POST', 'OPTIONS'])
def get_user_big5():
    if request.method == 'OPTIONS':
        return '', 200
    
    conn = get_db_connection()
    cur = conn.cursor()

    data = request.get_json()
    age =  data.get('personal', {}).get('age')
    gender = data.get('personal', {}).get('gender')
    user_id =  data.get('personal', {}).get('id')

    group_sums = data.get('groupSums', {})
    Extraversion =  group_sums.get('group1')
    Agreeableness = group_sums.get('group2')
    Conscientiousness = group_sums.get('group3')
    Neuroticism = group_sums.get('group4')
    Openness = group_sums.get('group5')

    logger.warning(data)

    try:
        logger.warning("query start")

        cur.execute(
            "INSERT INTO user_features (user_id, gender, age, extraversion, conscientiousness, agreeableness, neuroticism, openness) " \
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (user_id, gender, age, Extraversion, Conscientiousness, Agreeableness, Neuroticism, Openness)
        )
        conn.commit()
        return jsonify({"message": "values inserted", "user_id": user_id}), 201
    except Exception as e:
        logger.error(str(e))
        conn.rollback()
        return jsonify({"error": "Username or email already exists"}), 400
    finally:
        cur.close()
        conn.close()
