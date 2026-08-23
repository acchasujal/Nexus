import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
/// <reference types="vitest" />

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@shared': path.resolve(__dirname, '../shared'),
    },
  },
  server: {
    port: 5173,
  },
  build: {
    // Raise the warning threshold — our chunks are now split intentionally
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Manually chunk heavy dependencies into separate vendor files
        // This dramatically reduces the initial parse cost on first load
        manualChunks: {
          // React core — loads with the shell, always cached after first visit
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // TanStack Query — always needed for data fetching
          'vendor-query': ['@tanstack/react-query'],
          // React Flow — only needed on the Network Analysis tab
          'vendor-reactflow': ['@xyflow/react'],
          // Recharts — only needed on the Patterns page
          'vendor-recharts': ['recharts'],
          // Lucide icons — large icon set, separate chunk
          'vendor-icons': ['lucide-react'],
        },
      },
    },
  },
  // Vitest configuration
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.ts'],
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@shared': path.resolve(__dirname, '../shared'),
    },
    exclude: ['**/node_modules/**', '**/dist/**'],
  },
})
