import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const dist = resolve('dist')
const manifest = JSON.parse(readFileSync(resolve(dist, '.vite/manifest.json'), 'utf8'))
const html = readFileSync(resolve(dist, 'index.html'), 'utf8')
const assertFile = file => {
  if (!existsSync(resolve(dist, file))) throw new Error(`Missing build asset: ${file}`)
}
const preloads = new Set([...html.matchAll(/<link[^>]+rel="modulepreload"[^>]+href="\/([^"?]+)"/g)].map(m => m[1]))
for (const [key, chunk] of Object.entries(manifest)) {
  assertFile(chunk.file)
  for (const file of [...(chunk.css ?? []), ...(chunk.assets ?? [])]) assertFile(file)
  for (const dependency of [...(chunk.imports ?? []), ...(chunk.dynamicImports ?? [])]) {
    if (!manifest[dependency]) throw new Error(`Missing manifest dependency: ${key} -> ${dependency}`)
  }
  if (chunk.file.endsWith('.js') && !chunk.isEntry && !preloads.has(chunk.file)) {
    throw new Error(`Module not retained by initial document: ${chunk.file}`)
  }
}
for (const m of html.matchAll(/(?:src|href)="\/(assets\/[^"?]+)"/g)) assertFile(m[1])
console.log(`Build integrity verified: ${Object.keys(manifest).length} manifest entries, ${preloads.size} preloaded modules.`)
