"""backend/app/auth/__init__.py

Authentication and authorization package for NEXUS.

Includes:
  - Token verification interface and JWT claims extraction
  - RBAC permission guards for route-level authorization (INVESTIGATOR, ANALYST, SUPERVISOR, ADMIN)
  - Audit-on-deny: rejected access attempts are logged to AuditService
"""
