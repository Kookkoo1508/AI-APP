import { createApp } from 'vue'
// import './styles/tailwind.css'
import './assets/main.css'
import App from './App.vue'
import router from './router'
import { useAuth } from '@/composables/useAuth'
useAuth().initAuthHeader()  
createApp(App).use(router).mount('#app')
