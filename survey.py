from flask import Blueprint, request, jsonify, current_app, send_from_directory

survey_bp = Blueprint('survey', __name__)

@survey_bp.route('/survey/<user_name>')
def ask_user(user_name):
    return send_from_directory('static', "survey.html")

@survey_bp.route('/api/survey', methods = ['POST', 'OPTIONS'])
def get_user_big5():
    if request.method == 'OPTIONS':
        return '', 200
    
    return jsonify(request.get_json()), 201