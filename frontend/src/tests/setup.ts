import '@testing-library/jest-dom'

const storageMap = new Map<string, string>()
const mockLocalStorage = {
  getItem: (key: string) => storageMap.get(key) ?? null,
  setItem: (key: string, value: string) => { storageMap.set(key, String(value)) },
  removeItem: (key: string) => { storageMap.delete(key) },
  clear: () => { storageMap.clear() },
  get length() { return storageMap.size },
  key: (index: number) => Array.from(storageMap.keys())[index] ?? null,
}

if (typeof window !== 'undefined') {
  try {
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
      configurable: true,
    })
  } catch {
    // ignore
  }
}
if (typeof globalThis !== 'undefined') {
  try {
    Object.defineProperty(globalThis, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
      configurable: true,
    })
  } catch {
    // ignore
  }
}

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined') {
  window.ResizeObserver = window.ResizeObserver || ResizeObserverMock
  const svgProto = window.SVGElement?.prototype as (SVGElement & { getBBox?: () => unknown }) | undefined
  if (svgProto && typeof svgProto.getBBox !== 'function') {
    svgProto.getBBox = () => ({
      x: 0,
      y: 0,
      width: 100,
      height: 100,
      top: 0,
      right: 100,
      bottom: 100,
      left: 0,
      toJSON: () => {},
    })
  }

  if (window.SVGSVGElement) {
    try {
      Object.defineProperty(window.SVGSVGElement.prototype, 'viewBox', {
        get() {
          return {
            baseVal: { x: 0, y: 0, width: 800, height: 600 },
            animVal: { x: 0, y: 0, width: 800, height: 600 },
          }
        },
        configurable: true,
      })
      Object.defineProperty(window.SVGSVGElement.prototype, 'width', {
        get() {
          return {
            baseVal: { value: 800 },
            animVal: { value: 800 },
          }
        },
        configurable: true,
      })
      Object.defineProperty(window.SVGSVGElement.prototype, 'height', {
        get() {
          return {
            baseVal: { value: 600 },
            animVal: { value: 600 },
          }
        },
        configurable: true,
      })
    } catch {
      // ignore
    }
  }
}
if (typeof global !== 'undefined') {
  const g = global as typeof globalThis & { ResizeObserver?: typeof ResizeObserverMock }
  g.ResizeObserver = g.ResizeObserver || ResizeObserverMock
}

