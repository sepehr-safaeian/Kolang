# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Active |

---

## Reporting a Vulnerability

If you discover a security vulnerability in Kolang, **please do not open a public issue**.

### How to Report

1. **Email:** Send a detailed report to [security@kolang.dev](mailto:security@kolang.dev)
2. **Subject:** `[SECURITY] <brief description>`
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)
   - Your contact information for follow-up

### Response Timeline

| Action | Timeframe |
|--------|-----------|
| Acknowledgment | Within 48 hours |
| Initial Assessment | Within 5 business days |
| Fix Development | Based on severity |
| Public Disclosure | After fix is released |

### Severity Classification

| Severity | Description | Target Resolution |
|----------|-------------|-------------------|
| **Critical** | Remote code execution, authentication bypass, data exfiltration | 48 hours |
| **High** | Privilege escalation, significant data exposure | 5 business days |
| **Medium** | Limited data exposure, denial of service | 2 weeks |
| **Low** | Minor information disclosure, hardening improvements | Next release |

---

## Security Update Process

1. Vulnerabilities are assessed and triaged privately
2. A fix is developed and tested
3. A security advisory is prepared
4. The fix is released with an advisory on [GitHub Security Advisories](https://github.com/sepehr-safaeian/Kolang/security/advisories)
5. Credits are given to the reporter (unless anonymity is requested)

---

## Security Best Practices for Deployment

When deploying Kolang in production:

- [ ] **Rotate secrets** — Change all default keys and passwords
- [ ] **Use TLS** — Terminate TLS at the load balancer or reverse proxy
- [ ] **Restrict network access** — Limit access to OPA, PostgreSQL, and Redis to internal networks
- [ ] **Enable audit logging** — Configure audit sinks for compliance
- [ ] **Keep dependencies updated** — Monitor for CVEs with `pip audit` or Dependabot
- [ ] **Run as non-root** — Use the provided Docker image which runs as a non-root user
- [ ] **Set resource limits** — Configure memory, CPU, and payload size limits
- [ ] **Enable rate limiting** — Protect against abuse with Redis-backed rate limiting
- [ ] **Review OPA policies** — Audit your Rego policies regularly

---

## Responsible Disclosure

We ask that you:

- **Do not** exploit vulnerabilities beyond what is necessary to demonstrate them
- **Do not** access or modify data belonging to others
- **Do not** disclose the vulnerability publicly until a fix is available
- **Do** provide sufficient detail for us to reproduce and fix the issue

We will:

- Acknowledge your report promptly
- Keep you informed of our progress
- Credit you in the security advisory (unless you prefer anonymity)
- Not pursue legal action against researchers acting in good faith

---

## Security Hall of Fame

We gratefully acknowledge security researchers who have helped make Kolang more secure:

*No reports yet — be the first!*

---

## Contact

- **Security Reports:** [security@kolang.dev](mailto:security@kolang.dev)
- **General Questions:** [GitHub Discussions](https://github.com/sepehr-safaeian/Kolang/discussions)
