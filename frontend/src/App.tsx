import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { Toaster } from 'sonner'
import { queryClient } from './lib/queryClient'
import { AuthProvider } from './contexts/AuthContext'
import { UIProvider } from './contexts/UIContext'
import { router } from './routes/router'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <UIProvider>
          <RouterProvider router={router} />
          <Toaster 
            position="top-right" 
            toastOptions={{
              className: 'font-sans text-small border border-neutral-200 bg-neutral-50 text-neutral-800 rounded-radius-md shadow-md',
              duration: 3000,
            }}
          />
        </UIProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
