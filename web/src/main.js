import '@fontsource-variable/inter'
import '@fontsource-variable/bricolage-grotesque'
import '@fontsource-variable/anek-devanagari'
import './styles/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import { reveal } from './lib/reveal'
import { tilt } from './lib/tilt'
import router from './router'

createApp(App)
  .use(router)
  .directive('tilt', tilt) // 3D tilt that follows the mouse
  .directive('reveal', reveal) // fade and rise when scrolled into view
  .mount('#app')
