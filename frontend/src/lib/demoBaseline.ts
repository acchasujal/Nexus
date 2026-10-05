import canonical from '../../../backend/app/db/canonical_read_model.json'
import type { IntelligenceBootstrapResponse, NetworkPulseItem } from '@shared/contracts/api'

// A bundled synthetic snapshot, never a successful API response or live query-cache entry.
// Reuse the backend's versioned artifact; do not maintain a second set of demo numbers.
export const DEMO_BASELINE = {
  bootstrap: {
    dataset_version: canonical.dataset_version,
    snapshot_id: canonical.network_delta.after_snapshot_id,
    baseline_snapshot_id: canonical.network_delta.before_snapshot_id,
    generated_at: canonical.generated_at,
    kpis: canonical.kpis,
    primary_pulse: canonical.primary_pulse as unknown as NetworkPulseItem,
    affected_cases: canonical.affected_investigations,
  } satisfies IntelligenceBootstrapResponse,
  pulses: canonical.pulses as unknown as NetworkPulseItem[],
  worklist: canonical.worklist.map(item => ({ ...item, id: item.case_id })),
  checksum: canonical.checksum,
}
