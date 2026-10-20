import { createApplication } from './app/createApplication'
import './app/styles.css'

const { app, router } = createApplication()
await router.isReady()
app.mount('#app')
