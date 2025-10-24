import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './App.css'

const qc = new QueryClient()
ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter basename={import.meta.env.VITE_PUBLIC_BASE || '/'}>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
