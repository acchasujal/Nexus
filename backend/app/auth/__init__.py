"""backend/app/auth/__init__.py

Authentication and authorization package for CaseClock.

Phase 3 implementation:
  - Catalyst Auth token verification interface
  - JWT claims extraction and principal model
  - RBAC permission guards for route-level authorization
  - Audit-on-deny: every rejected access is recorded

Phase 1 routes accept a role query parameter as a stopgap.
Phase 3 introduces this layer; Phase 4 removes the query-parameter bypass.
"""
