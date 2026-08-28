import '@testing-library/jest-dom'

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined') {
  window.ResizeObserver = window.ResizeObserver || ResizeObserverMock
  if (window.SVGElement && !window.SVGElement.prototype.getBBox) {
    window.SVGElement.prototype.getBBox = () => ({
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
  // @ts-expect-error test polyfill
  global.ResizeObserver = global.ResizeObserver || ResizeObserverMock
}

