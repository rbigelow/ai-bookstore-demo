# Security Report

## Threat Model
- Account compromise attempts against login/session flows.
- Abuse of public APIs (book/cart/order/review endpoints).
- Privilege escalation against admin-only endpoints.
- Sensitive data exposure via source control or misconfigured runtime secrets.

## Security Controls Implemented
- Password hashing via Werkzeug `generate_password_hash`.
- Session-based auth with secure cookie settings (`HttpOnly`, `SameSite`, configurable `Secure`) and session timeout.
- CSRF protection for server-rendered form submissions with Flask-WTF.
- Authorization checks for ownership and role-based admin endpoints.
- Input validation for required fields and core numeric bounds.
- Two-factor flow support with Firebase-ready configuration and enforcement hooks.

## Known Limitations / Hardening Recommendations
- Enforce HTTPS and `SESSION_COOKIE_SECURE=true` in production.
- Replace mock payment service with a PCI-compliant provider.
- Implement robust 2FA challenge verification through Firebase MFA APIs.
- Add production-grade rate limiting and WAF protections.
- Add centralized audit logging, alerting, and security monitoring.
- Implement encrypted backups and disaster recovery runbooks.

## Secrets Handling Guidance
- Keep secrets in environment variables only.
- Never commit `.env` with real credentials.
- Rotate Firebase and application keys periodically.
- Grant least-privilege access to deployment and runtime environments.
