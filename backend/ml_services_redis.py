# backend/ml_services_redis.py
import os
import json
import redis
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime
from redis_discovery import registry

logger = logging.getLogger(__name__)
ml_redis_bp = Blueprint('ml_redis', __name__, url_prefix='/ml')

@ml_redis_bp.route('/register_sensor', methods=['POST'])
def register_sensor():
    """Регистрация IoT сенсора"""
    try:
        data = request.json
        sensor_id = data.get('sensor_id')
        sensor_type = data.get('type', 'temperature')
        location = data.get('location')
        unit = data.get('unit', 'celsius')
        
        service_id = f"sensor-{sensor_id}"
        
        tags = [
            "iot",
            "sensor",
            f"type={sensor_type}",
            f"location={location}",
            "realtime"
        ]
        
        metadata = {
            "sensor_type": sensor_type,
            "location": location,
            "unit": unit,
            "data_format": "json"
        }
        
        success = registry.register_service(
            service_id=service_id,
            service_name="iot-sensor",
            address=data.get('address', 'sensor-network'),
            port=data.get('port', 8080),
            tags=tags,
            metadata=metadata,
            ttl=15  # Сенсоры обновляются чаще
        )
        
        if success:
            return jsonify({
                "status": "registered",
                "sensor_id": sensor_id,
                "service_id": service_id
            }), 200
        else:
            return jsonify({"error": "Registration failed"}), 500
            
    except Exception as e:
        logger.error(f"Sensor registration error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@ml_redis_bp.route('/register_model', methods=['POST'])
def register_ml_model():
    """Регистрация ML модели"""
    try:
        data = request.json
        model_id = data.get('model_id')
        model_name = data.get('model_name')
        model_type = data.get('model_type')  # classification, detection, segmentation
        framework = data.get('framework', 'yolo')
        accuracy = data.get('accuracy', 0.0)
        
        service_id = f"ml-{model_id}"
        
        tags = [
            "ml-model",
            f"type={model_type}",
            f"framework={framework}",
            f"accuracy={accuracy}",
            "scientific"
        ]
        
        metadata = {
            "model_name": model_name,
            "model_type": model_type,
            "framework": framework,
            "metrics": data.get('metrics', {}),
            "training_date": datetime.now().isoformat(),
            "version": data.get('version', '1.0.0')
        }
        
        success = registry.register_service(
            service_id=service_id,
            service_name="ml-service",
            address=data.get('address', 'ml-cluster'),
            port=data.get('port', 8000),
            tags=tags,
            metadata=metadata,
            ttl=60  # ML модели регистрируются дольше
        )
        
        if success:
            return jsonify({
                "status": "registered",
                "model_id": model_id,
                "service_id": service_id,
                "tags": tags
            }), 200
        else:
            return jsonify({"error": "Registration failed"}), 500
            
    except Exception as e:
        logger.error(f"ML model registration error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@ml_redis_bp.route('/register_bio_tool', methods=['POST'])
def register_bio_tool():
    """Регистрация биоинформатического инструмента"""
    try:
        data = request.json
        tool_name = data.get('tool_name')
        tool_version = data.get('version', 'latest')
        database = data.get('database', 'unknown')
        
        service_id = f"bio-{tool_name}-{tool_version}"
        
        tags = [
            "bioinformatics",
            f"tool={tool_name}",
            f"version={tool_version}",
            f"database={database}",
            "scientific-computing"
        ]
        
        metadata = {
            "tool_name": tool_name,
            "version": tool_version,
            "database": database,
            "parameters": data.get('parameters', {}),
            "citation": data.get('citation', '')
        }
        
        success = registry.register_service(
            service_id=service_id,
            service_name="bioinformatics-tool",
            address=data.get('address', 'bio-cluster'),
            port=data.get('port', 9000),
            tags=tags,
            metadata=metadata,
            ttl=120  # Биоинструменты регистрируются надолго
        )
        
        if success:
            return jsonify({
                "status": "registered",
                "tool_name": tool_name,
                "service_id": service_id
            }), 200
        else:
            return jsonify({"error": "Registration failed"}), 500
            
    except Exception as e:
        logger.error(f"Bio tool registration error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@ml_redis_bp.route('/services')
def list_services():
    """Список всех научных сервисов"""
    try:
        service_type = request.args.get('type')  # iot, ml, bio
        
        if service_type == 'iot':
            services = registry.get_services('iot')
        elif service_type == 'ml':
            services = registry.get_services('ml-model')
        elif service_type == 'bio':
            services = registry.get_services('bioinformatics')
        else:
            services = registry.get_services()
        
        return jsonify(services), 200
        
    except Exception as e:
        logger.error(f"Error listing services: {str(e)}")
        return jsonify({"error": str(e)}), 500

@ml_redis_bp.route('/sensors/data')
def get_sensor_data():
    """Получение данных с сенсоров"""
    try:
        sensors = registry.get_services('iot')
        
        # Имитация получения данных с сенсоров
        sensor_data = []
        for sensor in sensors:
            sensor_data.append({
                "sensor_id": sensor['service_id'],
                "type": sensor['metadata'].get('sensor_type', 'unknown'),
                "value": 20 + (hash(sensor['service_id']) % 30),  # Имитация данных
                "unit": sensor['metadata'].get('unit', 'unknown'),
                "timestamp": datetime.now().isoformat()
            })
        
        return jsonify(sensor_data), 200
        
    except Exception as e:
        logger.error(f"Error getting sensor data: {str(e)}")
        return jsonify({"error": str(e)}), 500