# Shared Contracts — CHANGELOG

Owned by Lane 4 (Sujal). Every change to `api.py` or `api.ts` is logged here.
Keep Python and TypeScript mirrors in sync — every entry must describe what changed in both.

---

## [Unreleased]

### Added
- Initial contract types: `ClockInstanceResponse`, `DependencyResponse`, `CaseSummaryResponse`,
  `CaseDetailResponse`, `EscalationResponse`, `CopilotQueryRequest`, `CopilotQueryResponse`,
  `TokenResponse`
- Enums: `UserRole`, `ClockStatus`, `DependencyStatus`

### Changed
- Added `updated_at` to `CaseSummaryResponse` in both Python and TypeScript contracts.

---

<!-- Template for future entries:

## [YYYY-MM-DD] — vX.Y.Z

### Added
- Description of new type or field (both api.py and api.ts updated)

### Changed
- Description of modified type — note: breaking changes must be coordinated with all lanes
  before landing

### Removed
- Description of removed type — confirm no lane is still importing before removing

### Breaking
- ⚠️ List any breaking changes here with migration instructions

-->
