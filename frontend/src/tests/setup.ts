import '@testing-library/jest-dom'

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined') {
  window.ResizeObserver = window.ResizeObserver || ResizeObserverMock
}
if (typeof global !== 'undefined') {
  // @ts-expect-error test polyfill
  global.ResizeObserver = global.ResizeObserver || ResizeObserverMock
}
