import vk_api
from vk_api.exceptions import VkApiError
import logging
from datetime import datetime
from typing import Dict, Optional, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_vk_user_info(vk_url: str, access_token: str = None) -> Dict[str, Any]:
    """
    Получает информацию о пользователе VK через официальное API.
    
    Args:
        vk_url: URL профиля VK
        access_token: токен доступа VK API (опционально, но рекомендуется)
    
    Returns:
        Dict с полями: sex, age, city, country, bdate, user_id
    """
    
    user_id = extract_user_id_from_url(vk_url)
    if not user_id:
        raise ValueError(f"Не удалось извлечь ID пользователя из URL: {vk_url}")
    
    if access_token:
        vk_session = vk_api.VkApi(token=access_token)
    else:
        
        try:
            vk_session = vk_api.VkApi()
            vk_session.auth(token_only=True)
        except Exception as e:
            logger.warning(f"Не удалось авторизоваться без токена: {e}")
            vk_session = None
    
    if vk_session is None:
        raise ValueError("Необходим access_token для доступа к API VK")
    
    vk = vk_session.get_api()
    
    try:
        
        user_info = vk.users.get(
            user_ids=user_id,
            fields='sex, bdate, city, country, domain'
        )[0]
        
        result = {
            'user_id': str(user_info.get('id')),
            'sex': parse_sex(user_info.get('sex')),
            'bdate': user_info.get('bdate'),
            'age': calculate_age(user_info.get('bdate')),
            'city': parse_city(user_info.get('city')),
            'country': parse_country(user_info.get('country')),
            'domain': user_info.get('domain'),
            'first_name': user_info.get('first_name'),
            'last_name': user_info.get('last_name')
        }
        
        logger.info(f"Получена информация о пользователе: {result['user_id']}, "
                   f"пол: {result['sex']}, возраст: {result['age']}, "
                   f"город: {result['city']}")
        
        return result
        
    except VkApiError as e:
        logger.error(f"Ошибка VK API: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        raise

def extract_user_id_from_url(url: str) -> Optional[str]:
    """Извлекает ID пользователя из URL VK"""
    import re
    
    if not url or not isinstance(url, str):
        return None
    
    patterns = [
        r'vk\.com/(?:id|club|public)(\d+)',  
        r'vk\.com/([a-zA-Z0-9_.]+)',          
        r'wall(\d+)_',                        
        r'photo(\d+)_',                       
        r'/audios(\d+)',                      
        r'\?w=likes/photo(\d+)_',             
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            user_id = match.group(1)
            
            if user_id.isdigit():
                return user_id
            return user_id  
    
    return None

def parse_sex(sex_code: Optional[int]) -> str:
    """Преобразует код пола в читаемый текст"""
    sex_map = {
        0: 'unknown',
        1: 'female',
        2: 'male'
    }
    return sex_map.get(sex_code, 'unknown')

def calculate_age(bdate: Optional[str]) -> Optional[int]:
    """Вычисляет возраст из даты рождения"""
    if not bdate:
        return None
    
    try:
        
        parts = bdate.split('.')
        if len(parts) == 3:
            year = int(parts[2])
            today = datetime.now()
            age = today.year - year
            
            month = int(parts[1])
            day = int(parts[0])
            if (today.month, today.day) < (month, day):
                age -= 1
            return age
    except (ValueError, IndexError):
        pass
    
    return None

def parse_city(city_data: Optional[Dict]) -> Optional[str]:
    """Извлекает название города из данных API"""
    if city_data and isinstance(city_data, dict):
        return city_data.get('title')
    return None

def parse_country(country_data: Optional[Dict]) -> Optional[str]:
    """Извлекает название страны из данных API"""
    if country_data and isinstance(country_data, dict):
        return country_data.get('title')
    return None

def get_user_info_with_consent(vk_url: str, consent: bool = True, 
                               access_token: str = None) -> Dict[str, Any]:
    """
    Обертка с проверкой согласия на обработку данных.
    
    Args:
        vk_url: URL профиля VK
        consent: согласие на обработку данных
        access_token: токен доступа VK API
    
    Returns:
        Dict с информацией о пользователе
    """
    if not consent:
        raise ValueError("Необходимо согласие на обработку данных")
    
    return get_vk_user_info(vk_url, access_token)
