import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './store/auth'
import { PrefsProvider } from './store/prefs'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <PrefsProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </PrefsProvider>
    </BrowserRouter>
  </React.StrictMode>,
)