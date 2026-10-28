import { readFileSync, writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

const root = new URL('../../', import.meta.url)
const source = readFileSync(new URL('artifacts/nexus_graph/nexus_graph.json', root))
const graph = JSON.parse(source)
if (graph.metadata.profile !== 'demo' || graph.metadata.seed !== 42) {
  throw new Error('Demo entry requires the canonical synthetic evaluation artifact')
}
const rows = graph.nodes.filter(node => ['Case', 'CASE'].includes(node.entity_type)).map(node => {
  const props = node.properties
  const incident = graph.edges.filter(edge => edge.source_id === node.id || edge.target_id === node.id)
  const rank = incident.filter(edge => ['ACCUSED_IN', 'INVOLVED_IN'].includes(edge.edge_type)).length * 2
    + incident.filter(edge => edge.edge_type === 'HAS_EVIDENCE').length
  return { id: node.id, fir_number: props.fir_number ?? `FIR-${node.id}`,
    title: props.title ?? node.label ?? `Investigation ${node.id}`,
    district: props.district ?? 'Bengaluru', status: props.status ?? 'OPEN', rank }
}).sort((a, b) => b.rank - a.rank).slice(0, 10).map(({ rank, ...row }) => row)
if (rows.length !== 10) throw new Error('Canonical synthetic worklist must contain at least ten cases')
const snapshot = { source: 'artifacts/nexus_graph/nexus_graph.json', version: graph.metadata.version,
  generated_at: graph.metadata.generated_at,
  checksum: createHash('sha256').update(JSON.stringify(graph)).digest('hex'), worklist: rows }
const output = new URL('../src/lib/demoEntrySnapshot.json', import.meta.url)
const contents = `${JSON.stringify(snapshot, null, 2)}\n`
if (process.argv.includes('--check')) {
  if (readFileSync(output, 'utf8') !== contents) throw new Error('Demo snapshot is stale; run the frontend build')
} else {
  writeFileSync(output, contents)
}
