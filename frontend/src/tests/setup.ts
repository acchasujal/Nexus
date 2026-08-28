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
    svgProto.getBBox = function (this: SVGElement) {
      const getNum = (attr: string, fallback = 0): number => {
        const val = parseFloat(this.getAttribute(attr) || '')
        return Number.isFinite(val) ? val : fallback
      }

      let x = getNum('x', 0)
      let y = getNum('y', 0)
      let width = getNum('width', 0)
      let height = getNum('height', 0)

      // Circles & Ellipses
      const r = getNum('r', 0)
      if (r > 0) {
        const cx = getNum('cx', 0)
        const cy = getNum('cy', 0)
        x = cx - r
        y = cy - r
        width = r * 2
        height = r * 2
      } else {
        const rx = getNum('rx', 0)
        const ry = getNum('ry', 0)
        if (rx > 0 || ry > 0) {
          const cx = getNum('cx', 0)
          const cy = getNum('cy', 0)
          x = cx - rx
          y = cy - ry
          width = rx * 2
          height = ry * 2
        }
      }

      // Text elements derived dynamically from character count and font size
      if (width === 0 && height === 0 && this.textContent) {
        const textLen = this.textContent.trim().length
        if (textLen > 0) {
          const fontSize = parseFloat(window.getComputedStyle?.(this)?.fontSize || '') || 12
          width = textLen * (fontSize * 0.6)
          height = fontSize * 1.2
        }
      }

      // Composite elements (<g>, <svg>) derived dynamically from child bounding boxes
      if (width === 0 && height === 0 && this.children && this.children.length > 0) {
        let minX = Infinity
        let minY = Infinity
        let maxX = -Infinity
        let maxY = -Infinity
        let hasValidChild = false

        for (let i = 0; i < this.children.length; i++) {
          const child = this.children[i] as SVGElement
          const childBBox = typeof (child as unknown as { getBBox?: () => DOMRect }).getBBox === 'function'
            ? (child as unknown as { getBBox: () => DOMRect }).getBBox()
            : null

          if (childBBox && (childBBox.width > 0 || childBBox.height > 0)) {
            minX = Math.min(minX, childBBox.x)
            minY = Math.min(minY, childBBox.y)
            maxX = Math.max(maxX, childBBox.x + childBBox.width)
            maxY = Math.max(maxY, childBBox.y + childBBox.height)
            hasValidChild = true
          }
        }

        if (hasValidChild && Number.isFinite(minX) && Number.isFinite(maxX)) {
          x = minX
          y = minY
          width = Math.max(0, maxX - minX)
          height = Math.max(0, maxY - minY)
        }
      }

      // Fallback default only if element has no dimensional attributes or children
      if (width === 0 && height === 0) {
        width = 100
        height = 100
      }

      return {
        x,
        y,
        width,
        height,
        top: y,
        right: x + width,
        bottom: y + height,
        left: x,
        toJSON: () => ({}),
      }
    }
  }

  if (window.SVGSVGElement) {
    try {
      Object.defineProperty(window.SVGSVGElement.prototype, 'viewBox', {
        get() {
          const vb = this.getAttribute('viewBox')
          if (vb) {
            const parts = vb.trim().split(/[\s,]+/).map(Number)
            if (parts.length === 4 && parts.every(Number.isFinite)) {
              const [vx, vy, vw, vh] = parts
              return {
                baseVal: { x: vx, y: vy, width: vw, height: vh },
                animVal: { x: vx, y: vy, width: vw, height: vh },
              }
            }
          }
          const w = parseFloat(this.getAttribute('width') || '') || 800
          const h = parseFloat(this.getAttribute('height') || '') || 600
          return {
            baseVal: { x: 0, y: 0, width: w, height: h },
            animVal: { x: 0, y: 0, width: w, height: h },
          }
        },
        configurable: true,
      })
      Object.defineProperty(window.SVGSVGElement.prototype, 'width', {
        get() {
          const w = parseFloat(this.getAttribute('width') || '') || 800
          return {
            baseVal: { value: w },
            animVal: { value: w },
          }
        },
        configurable: true,
      })
      Object.defineProperty(window.SVGSVGElement.prototype, 'height', {
        get() {
          const h = parseFloat(this.getAttribute('height') || '') || 600
          return {
            baseVal: { value: h },
            animVal: { value: h },
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

