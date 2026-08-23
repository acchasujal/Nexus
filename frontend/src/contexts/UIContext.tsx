import React, { createContext, useContext, useState } from 'react'

type TableDensity = 'dense' | 'comfortable'

interface UIContextType {
  tableDensity: TableDensity
  setTableDensity: (density: TableDensity) => void
  isEscalateDrawerOpen: boolean
  setEscalateDrawerOpen: (isOpen: boolean) => void
}

export const UIContext = createContext<UIContextType | undefined>(undefined)

export function UIProvider({ children }: { children: React.ReactNode }) {
  const [tableDensity, setTableDensity] = useState<TableDensity>('dense')
  const [isEscalateDrawerOpen, setEscalateDrawerOpen] = useState(false)

  return (
    <UIContext.Provider
      value={{
        tableDensity,
        setTableDensity,
        isEscalateDrawerOpen,
        setEscalateDrawerOpen,
      }}
    >
      {children}
    </UIContext.Provider>
  )
}

export function useUI() {
  const context = useContext(UIContext)
  if (context === undefined) {
    throw new Error('useUI must be used within a UIProvider')
  }
  return context
}
