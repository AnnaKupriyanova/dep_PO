import os
import random
import time
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv('BACKEND_URL', 'http://app:5000')
SERVICE_ID = os.getenv('HOSTNAME', 'generator-1')

def generate_sensor_data():
    """Генерация научных данных (IoT сенсоры)"""
    return {
        "sensor_id": f"seedling-sensor-{random.randint(1, 5)}",
        "temperature": round(random.uniform(15.0, 35.0), 2),
        "humidity": round(random.uniform(30.0, 80.0), 2),
        "light_level": random.randint(500, 2000),
        "timestamp": datetime.now().isoformat(),
        "location": {
            "rack_id": random.randint(1, 10),
            "shelf_id": random.randint(1, 5)
        }
    }

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def register_service():
    """Регистрация сервиса в Redis через бэкенд"""
    registration_data = {
        "id": f"generator-{SERVICE_ID}",
        "name": "data-generator",
        "address": "generator-service",
        "port": 8000,
        "tags": ["iot", "sensor", "data-generator", "scientific"],
        "metadata": {
            "type": "seedling_monitoring",
            "version": "1.0.0"
        },
        "ttl": 60
    }
    
    response = requests.post(
        f"{BACKEND_URL}/discovery/register",
        json=registration_data,
        timeout=10
    )
    response.raise_for_status()
    logger.info(f"Service registered: generator-{SERVICE_ID}")
    return response.json()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
def send_data(data):
    """Отправка данных в бэкенд"""
    response = requests.post(
        f"{BACKEND_URL}/api/v1/sensors/data",
        json=data,
        timeout=5,
        headers={"X-Service-Id": SERVICE_ID}
    )
    response.raise_for_status()
    return response.json()

def main():
    logger.info(f"Starting Data Generator Service: {SERVICE_ID}")
    
    # Регистрация сервиса
    try:
        register_service()
    except Exception as e:
        logger.error(f"Failed to register service: {e}")
    
    # Бесконечный цикл генерации данных
    while True:
        try:
            data = generate_sensor_data()
            logger.info(f"Generated data: {data}")
            
            result = send_data(data)
            logger.info(f"Data sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send data: {e}")
        
        # Интервал между отправками (5-10 секунд)
        time.sleep(random.uniform(5, 10))

if __name__ == "__main__":
    main()