# Claude Guardrails for Safe Coding

This document provides a compact, practical set of guardrails and checklists to follow when writing code with or for Claude (or other AI-assisted coding). It focuses on safety, security, privacy, maintainability, and responsible dependency use.

## Purpose
- Prevent accidental introduction of security vulnerabilities.
- Protect user data and privacy.
- Ensure code is maintainable and testable.
- Provide quick PR review checklist items when AI-generated code is included.

## High-level principles
1. Least privilege: Only request or grant the minimal permissions required.
2. Fail-safe defaults: Deny by default; explicit allow when necessary.
3. Input validation: Treat all external input as untrusted.
4. Secure dependencies: Prefer well-maintained, audited packages.
5. Human-in-the-loop: Require human review for significant changes, secrets, or infra config.

## Security guardrails
- Secrets and credentials
  - Never hard-code secrets (API keys, DB passwords) in source code.
  - Use environment variables or secret managers (e.g., HashiCorp Vault, AWS Secrets Manager).
  - Add secret scanning in CI (e.g., GitHub secret scanning, truffleHog, detect-secrets).

- Input validation & sanitization
  - Validate and sanitize all external input (requests, files, CLI args).
  - Use parameterized queries or ORM query builders to prevent SQL injection.
  - Escape or encode data before rendering in HTML to prevent XSS.

- Authentication & authorization
  - Prefer proven auth libraries (OAuth, OpenID Connect) rather than rolling your own.
  - Enforce least privilege for API tokens and service accounts.
  - Audit and rotate long-lived credentials regularly.

- Transport & storage
  - Enforce TLS for all network traffic.
  - Encrypt sensitive data at rest using strong, standard algorithms.

- Logging & error handling
  - Do not log secrets or PII in plaintext.
  - Use structured logging with sampling where appropriate.
  - Fail with safe, generic error messages; record detailed errors to secure logs only.

## Privacy & data handling
- Minimize data collection: collect only what's necessary.
- Anonymize or pseudonymize personal data where possible.
- Define retention policies and delete data according to policy.
- For datasets used in AI training: verify licensing and remove sensitive PII.

## Dependency & supply chain
- Pin dependency versions and use lockfiles (package-lock.json, Pipfile.lock, poetry.lock).
- Limit transitive dependencies; prefer smaller, audited libraries.
- Regularly run dependency vulnerability scans (e.g., Dependabot, Snyk, GitHub Advanced Security).
- Use reproducible builds where possible.

## Testing & CI
- Add unit tests for any logic introduced by AI.
- Add integration tests for external interactions (DB, APIs).
- Use automated linters and formatters in pre-commit hooks.
- Require CI checks (lint, tests, security scans) to pass before merging.

## Code review & human oversight
- Label AI-generated code clearly in PR descriptions.
- Require at least one human reviewer for changes that touch security, infra, or data handling.
- For substantial or risky changes, run a short threat model analysis or security review.

## PR checklist (quick)
- [ ] Secrets removed and stored securely
- [ ] Inputs validated and sanitized
- [ ] Dependency versions pinned and scanned
- [ ] Tests added/updated (unit/integration)
- [ ] Lint and format checks pass
- [ ] Human reviewer assigned

## AI-specific rules when using Claude
- Do not allow Claude to output secrets, private data, or proprietary code bases.
- Use Claude for drafts and suggestions; verify logic and security-critical code manually.
- When prompting Claude, avoid including real production secrets or PII in prompts.

## Example prompts (safer patterns)
- Instead of: "Write a script that connects to my production DB with this password: ..."
- Use: "Show a parameterized example of connecting to a database. Use placeholders for credentials and explain secure storage options."

## Incident & rollback
- Have a rollback plan and tags for releases.
- If sensitive data is leaked, rotate credentials and revoke access immediately.
- Run post-incident review and update these guardrails as needed.

## Notes and follow-ups
- Consider integrating automated policy-as-code checks (e.g., Open Policy Agent) for infra.
- Add examples tailored to the project's main languages and frameworks.

---

Last updated: 2026-05-03
