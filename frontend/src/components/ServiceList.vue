<template>
  <div class="services-panel">
    <div class="services-header">
      <h3>Активные сервисы</h3>
      <button class="refresh-btn" @click="loadServices" :disabled="loading">
        {{ loading ? '' : '' }} Обновить
      </button>
    </div>

    <div class="stats-container">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_services || 0 }}</div>
        <div class="stat-label">Всего сервисов</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.healthy_services || 0 }}</div>
        <div class="stat-label">Активных</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.redis_connected ? '+' : '-' }}</div>
        <div class="stat-label">Redis</div>
      </div>
    </div>

    <div v-if="loading" class="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="services.length === 0" class="empty">Нет активных сервисов</div>
    <div v-else class="services-list">
      <div v-for="service in services" :key="service.service_id" class="service-item">
        <div class="service-info">
          <div class="service-name">
            <span class="status-indicator"></span>
            {{ service.service_name || service.service_id }}
          </div>
          <div class="service-address">{{ service.address }}:{{ service.port }}</div>
        </div>
        <div class="service-tags">
          <span v-for="tag in (service.tags || []).slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
          <span v-if="!service.tags || service.tags.length === 0" class="tag">нет тегов</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ServiceList',
  data() {
    return {
      services: [],
      stats: {
        total_services: 0,
        healthy_services: 0,
        redis_connected: false
      },
      loading: true,
      error: null,
      intervalId: null
    }
  },
  mounted() {
    this.loadServices()
    this.intervalId = setInterval(this.loadServices, 30000)
  },
  beforeUnmount() {
    if (this.intervalId) clearInterval(this.intervalId)
  },
  methods: {
    async loadServices() {
      try {
        this.loading = true
        this.error = null
        
        const [servicesRes, statsRes] = await Promise.all([
          fetch('/discovery/services'),
          fetch('/discovery/stats')
        ])
        
        if (!servicesRes.ok) throw new Error('Ошибка загрузки сервисов')
        if (!statsRes.ok) throw new Error('Ошибка загрузки статистики')
        
        this.services = await servicesRes.json()
        this.stats = await statsRes.json()
      } catch (err) {
        this.error = err.message
        console.error('Ошибка:', err)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.services-panel {
  background: #4f694b;
  border-radius: 18px;
  padding: 20px;
  margin: 20px;
  color: white;
}

.services-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.services-header h3 {
  margin: 0;
  font-size: 20px;
}

.refresh-btn {
  background: rgba(255,255,255,0.2);
  border: none;
  border-radius: 18px;
  padding: 6px 12px;
  color: white;
  cursor: pointer;
  transition: all 0.3s;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.3);
  transform: scale(1.02);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stats-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stat-card {
  background: rgba(255,255,255,0.15);
  border-radius: 12px;
  padding: 15px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
}

.stat-label {
  font-size: 12px;
  margin-top: 5px;
  opacity: 0.9;
}

.services-list {
  max-height: 400px;
  overflow-y: auto;
}

.service-item {
  background: rgba(255,255,255,0.15);
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.service-info {
  flex: 1;
}

.service-name {
  font-weight: bold;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-indicator {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #81c784;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
  100% { opacity: 0.5; transform: scale(1); }
}

.service-address {
  font-size: 11px;
  opacity: 0.8;
  margin-top: 3px;
}

.service-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.tag {
  background: rgba(255,255,255,0.2);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 10px;
}

.loading, .error, .empty {
  text-align: center;
  padding: 30px;
}

.error {
  color: #ffcccc;
}
</style>