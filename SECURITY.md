# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 3.3.x   | Yes       |
| < 3.3   | No        |

## Reporting a Vulnerability

Please **do not** open a public GitHub Issue for security vulnerabilities.

Report privately by opening a GitHub Security Advisory on this repository, or by contacting the maintainers through the repository owner's GitHub profile.

Include:

- Affected version and commit
- Reproduction steps (no exploit payload required)
- Impact assessment

We will acknowledge the report and work on a fix before any public disclosure.

## Secrets and credentials

Never commit:

- `.env` files with real keys
- API keys (`SILICONFLOW_API_KEY`, cloud tokens)
- JWT production secrets
- kubeconfig, SSH private keys, TLS certificates

Use `.env.example` as the template. Generate a production `JWT_SECRET` with:

```bash
openssl rand -hex 32
```

Run the local scanner before publishing:

```bash
python scripts/security_check.py
```
