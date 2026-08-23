import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/index.css'

async function enableMocking() {
  // Only run MSW in non-production mode
  if (import.meta.env.PROD || import.meta.env.VITE_ENABLE_MOCKS === 'false') {
    return
  }
  
  try {
    const { worker } = await import('./lib/mocks/browser')
    // Start MSW worker
    return await worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: {
        url: '/mockServiceWorker.js',
      }
    })
  } catch (error) {
    console.error('Failed to start MSW worker:', error)
  }
}

enableMocking().then(() => {
  const rootElement = document.getElementById('root')
  if (!rootElement) throw new Error('Failed to find the root element')

  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
})
