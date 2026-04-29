# backend/redis_discovery.py
import os
import redis
import json
import logging
import threading
import time
from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

redis_bp = Blueprint('redis_discovery', __name__, url_prefix='/discovery')

# Подключение к Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Параметры TTL
DEFAULT_TTL = 30  # секунд
HEARTBEAT_INTERVAL = 15  # секунд

class RedisServiceRegistry:
    """Сервис регистрации на основе Redis"""
    
    def __init__(self):
        self.redis_client = None
        self._connect()
        self._heartbeat_threads = {}
    
    def _connect(self):
        """Подключение к Redis"""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Проверяем соединение
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None
    
    def register_service(self, service_id: str, service_name: str, 
                        address: str, port: int, tags: List[str], 
                        metadata: Dict = None, ttl: int = DEFAULT_TTL) -> bool:
        """Регистрация сервиса в Redis"""
        try:
            if not self.redis_client:
                self._connect()
                if not self.redis_client:
                    return False
            
            # Формируем ключ сервиса
            service_key = f"service:{service_id}"
            
            # Данные сервиса
            service_data = {
                "service_id": service_id,
                "service_name": service_name,
                "address": address,
                "port": port,
                "tags": tags,
                "metadata": metadata or {},
                "registered_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat()
            }
            
            # Сохраняем в Redis с TTL
            self.redis_client.setex(
                service_key,
                ttl,
                json.dumps(service_data)
            )
            
            # Добавляем в индекс по тегам
            for tag in tags:
                tag_key = f"tag:{tag}"
                self.redis_client.sadd(tag_key, service_id)
                # Устанавливаем TTL для индекса тегов
                self.redis_client.expire(tag_key, ttl + 10)
            
            # Добавляем в общий индекс сервисов
            self.redis_client.sadd("services:all", service_id)
            self.redis_client.expire("services:all", ttl + 10)
            
            # Запускаем heartbeat для автоматического продления TTL
            self._start_heartbeat(service_id, ttl)
            
            logger.info(f"Service registered: {service_id} at {address}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_id}: {str(e)}")
            return False
    
    def deregister_service(self, service_id: str) -> bool:
        """Отмена регистрации сервиса"""
        try:
            if not self.redis_client:
                return False
            
            # Получаем данные сервиса перед удалением
            service_key = f"service:{service_id}"
            service_data = self.redis_client.get(service_key)
            
            if service_data:
                data = json.loads(service_data)
                tags = data.get("tags", [])
                
                # Удаляем из индексов тегов
                for tag in tags:
                    tag_key = f"tag:{tag}"
                    self.redis_client.srem(tag_key, service_id)
            
            # Удаляем сервис
            self.redis_client.delete(service_key)
            
            # Удаляем из общего индекса
            self.redis_client.srem("services:all", service_id)
            
            # Останавливаем heartbeat
            self._stop_heartbeat(service_id)
            
            logger.info(f"Service deregistered: {service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {str(e)}")
            return False
    
    def get_services(self, tag: Optional[str] = None) -> List[Dict]:
        """Получение списка сервисов"""
        try:
            if not self.redis_client:
                self._connect()
                if not self.redis_client:
                    return []
            
            # Получаем ID сервисов
            if tag:
                tag_key = f"tag:{tag}"
                service_ids = self.redis_client.smembers(tag_key)
            else:
                service_ids = self.redis_client.smembers("services:all")
            
            services = []
            for service_id in service_ids:
                service_key = f"service:{service_id}"
                service_data = self.redis_client.get(service_key)
                
                if service_data:
                    service = json.loads(service_data)
                    # Проверяем TTL (оставшееся время жизни)
                    ttl = self.redis_client.ttl(service_key)
                    service["ttl_remaining"] = ttl
                    service["status"] = "healthy" if ttl > 0 else "expired"
                    services.append(service)
                else:
                    # Очищаем невалидные индексы
                    if tag:
                        self.redis_client.srem(tag_key, service_id)
                    else:
                        self.redis_client.srem("services:all", service_id)
            
            return services
            
        except Exception as e:
            logger.error(f"Failed to get services: {str(e)}")
            return []
    
    def get_service(self, service_id: str) -> Optional[Dict]:
        """Получение конкретного сервиса"""
        try:
            if not self.redis_client:
                return None
            
            service_key = f"service:{service_id}"
            service_data = self.redis_client.get(service_key)
            
            if service_data:
                return json.loads(service_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get service {service_id}: {str(e)}")
            return None
    
    def _start_heartbeat(self, service_id: str, ttl: int):
        """Запуск heartbeat для сервиса"""
        def heartbeat_loop():
            while service_id in self._heartbeat_threads:
                try:
                    time.sleep(HEARTBEAT_INTERVAL)
                    service_key = f"service:{service_id}"
                    
                    # Продлеваем TTL
                    if self.redis_client and self.redis_client.exists(service_key):
                        self.redis_client.expire(service_key, ttl)
                        
                        # Обновляем last_heartbeat
                        service_data = self.redis_client.get(service_key)
                        if service_data:
                            data = json.loads(service_data)
                            data["last_heartbeat"] = datetime.now().isoformat()
                            self.redis_client.setex(service_key, ttl, json.dumps(data))
                        
                        logger.debug(f"Heartbeat for {service_id}")
                    else:
                        break
                        
                except Exception as e:
                    logger.error(f"Heartbeat error for {service_id}: {str(e)}")
                    break
            
            # Очищаем запись о потоке
            self._heartbeat_threads.pop(service_id, None)
        
        # Запускаем поток, если еще не запущен
        if service_id not in self._heartbeat_threads:
            thread = threading.Thread(target=heartbeat_loop, daemon=True)
            self._heartbeat_threads[service_id] = thread
            thread.start()
    
    def _stop_heartbeat(self, service_id: str):
        """Остановка heartbeat"""
        self._heartbeat_threads.pop(service_id, None)
    
    def get_service_stats(self) -> Dict:
        """Получение статистики о сервисах"""
        try:
            if not self.redis_client:
                return {"error": "Redis not connected"}
            
            all_services = self.get_services()
            total = len(all_services)
            
            # Подсчет по тегам
            tag_stats = {}
            for service in all_services:
                for tag in service.get("tags", []):
                    tag_stats[tag] = tag_stats.get(tag, 0) + 1
            
            return {
                "total_services": total,
                "healthy_services": sum(1 for s in all_services if s.get("status") == "healthy"),
                "tag_statistics": tag_stats,
                "redis_connected": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {"error": str(e)}

# Глобальный экземпляр реестра
registry = RedisServiceRegistry()

# ==================== Flask Routes ====================

@redis_bp.route('/register', methods=['POST'])
def register_service():
    """Регистрация сервиса в Redis"""
    try:
        data = request.json
        
        service_id = data.get('id')
        service_name = data.get('name', os.getenv('SERVICE_NAME', 'analytics-service'))
        address = data.get('address')
        port = data.get('port', 5000)
        tags = data.get('tags', [])
        metadata = data.get('metadata', {})
        ttl = data.get('ttl', DEFAULT_TTL)
        
        if not service_id or not address:
            return jsonify({"error": "Missing required fields: id, address"}), 400
        
        success = registry.register_service(
            service_id=service_id,
            service_name=service_name,
            address=address,
            port=port,
            tags=tags,
            metadata=metadata,
            ttl=ttl
        )
        
        if success:
            return jsonify({
                "status": "registered",
                "service_id": service_id,
                "backend": "redis",
                "ttl": ttl
            }), 200
        else:
            return jsonify({"error": "Failed to register service"}), 500
            
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@redis_bp.route('/deregister', methods=['POST'])
def deregister_service():
    """Отмена регистрации сервиса"""
    try:
        data = request.json
        service_id = data.get('id')
        
        if not service_id:
            return jsonify({"error": "Missing service id"}), 400
        
        success = registry.deregister_service(service_id)
        
        if success:
            return jsonify({"status": "deregistered", "service_id": service_id}), 200
        else:
            return jsonify({"error": "Failed to deregister service"}), 500
            
    except Exception as e:
        logger.error(f"Deregistration error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@redis_bp.route('/services')
def get_services():
    """Получить список сервисов (с фильтрацией по тегу)"""
    try:
        tag = request.args.get('tag')
        services = registry.get_services(tag)
        return jsonify(services), 200
        
    except Exception as e:
        logger.error(f"Error getting services: {str(e)}")
        return jsonify({"error": str(e)}), 500

@redis_bp.route('/services/<service_id>')
def get_service(service_id):
    """Получить конкретный сервис"""
    try:
        service = registry.get_service(service_id)
        if service:
            return jsonify(service), 200
        else:
            return jsonify({"error": "Service not found"}), 404
            
    except Exception as e:
        logger.error(f"Error getting service: {str(e)}")
        return jsonify({"error": str(e)}), 500

@redis_bp.route('/stats')
def get_stats():
    """Получить статистику сервисов"""
    try:
        stats = registry.get_service_stats()
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

@redis_bp.route('/health')
def redis_health():
    """Health check для Redis"""
    try:
        if registry.redis_client and registry.redis_client.ping():
            return jsonify({
                "status": "healthy",
                "backend": "redis",
                "timestamp": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "unhealthy",
                "backend": "redis",
                "error": "Redis connection failed"
            }), 500
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500