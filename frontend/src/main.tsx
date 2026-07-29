import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import './index.css'
import { initTelegram } from './lib/telegram'
import { AuthProvider } from './store/auth'
import { NetworkProvider } from './store/network'
import { ToastProvider } from './store/toast'

initTelegram()

const container = document.getElementById('root')
if (!container) throw new Error('#root elementi topilmadi')

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <NetworkProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </NetworkProvider>
      </ToastProvider>
    </BrowserRouter>
  </StrictMode>,
)
