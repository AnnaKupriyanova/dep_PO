<template>
  <div class="app">
    <h1>Кемеровский Питомник</h1>
    <ServiceList />
  </div>
</template>

<script>
import ServiceList from './components/ServiceList.vue'

export default {
  name: 'App',
  components: {
    ServiceList
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
}

h1 {
  color: #4f694b;
}

.app {
  min-height: 100vh;
}
</style>