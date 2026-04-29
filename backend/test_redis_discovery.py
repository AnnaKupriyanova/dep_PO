# test_redis_discovery.py
import requests
import time
import json

BASE_URL = "http://localhost:5000"

def test_register_service():
    """Тест регистрации сервиса"""
    print("\n=== Testing Service Registration ===")
    
    service_data = {
        "id": "test-service-001",
        "name": "test-analytics",
        "address": "192.168.1.100",
        "port": 8080,
        "tags": ["test", "analytics", "ml-model"],
        "metadata": {
            "version": "1.0",
            "owner": "test_user"
        }
    }
    
    response = requests.post(f"{BASE_URL}/discovery/register", json=service_data)
    print(f"Registration response: {response.status_code}")
    print(f"Response body: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200

def test_get_services():
    """Тест получения списка сервисов"""
    print("\n=== Testing Get Services ===")
    
    # Все сервисы
    response = requests.get(f"{BASE_URL}/discovery/services")
    print(f"All services: {response.status_code}")
    if response.status_code == 200:
        services = response.json()
        print(f"Found {len(services)} services")
        for service in services:
            print(f"  - {service.get('service_id')}: {service.get('address')}:{service.get('port')}")
    
    # Фильтрация по тегу
    response = requests.get(f"{BASE_URL}/discovery/services?tag=test")
    print(f"\nServices with tag 'test': {len(response.json())}")

def test_get_stats():
    """Тест получения статистики"""
    print("\n=== Testing Stats ===")
    
    response = requests.get(f"{BASE_URL}/discovery/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"Stats: {json.dumps(stats, indent=2)}")

def test_register_ml_model():
    """Тест регистрации ML модели"""
    print("\n=== Testing ML Model Registration ===")
    
    ml_data = {
        "model_id": "yolov8-detector",
        "model_name": "YOLOv8 Object Detector",
        "model_type": "detection",
        "framework": "yolo",
        "accuracy": 0.89,
        "metrics": {
            "mAP": 0.85,
            "f1_score": 0.82
        },
        "version": "8.0"
    }
    
    response = requests.post(f"{BASE_URL}/ml/register_model", json=ml_data)
    print(f"ML model registration: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_register_sensor():
    """Тест регистрации сенсора"""
    print("\n=== Testing IoT Sensor Registration ===")
    
    sensor_data = {
        "sensor_id": "temp-sensor-01",
        "type": "temperature",
        "location": "greenhouse-1",
        "unit": "celsius",
        "address": "sensor-network",
        "port": 1883
    }
    
    response = requests.post(f"{BASE_URL}/ml/register_sensor", json=sensor_data)
    print(f"Sensor registration: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_health_check():
    """Тест health check"""
    print("\n=== Testing Health Check ===")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health status: {response.status_code}")
    if response.status_code == 200:
        health = response.json()
        print(f"Status: {health.get('status')}")
        print(f"Service Discovery: {health.get('service_discovery')}")
        print(f"Redis: {health.get('redis')}")

def main():
    """Запуск всех тестов"""
    print("=" * 50)
    print("Testing Redis Service Discovery")
    print("=" * 50)
    
    # Ждем запуска приложения
    print("Waiting for application to start...")
    time.sleep(5)
    
    # Запускаем тесты
    test_health_check()
    test_register_service()
    test_get_services()
    test_get_stats()
    test_register_ml_model()
    test_register_sensor()
    
    # Повторно получаем обновленный список
    print("\n=== Updated Services List ===")
    response = requests.get(f"{BASE_URL}/discovery/services")
    if response.status_code == 200:
        services = response.json()
        print(f"Total services after registration: {len(services)}")
        for service in services:
            tags = service.get('tags', [])
            print(f"  - {service.get('service_id')}: tags={tags}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()