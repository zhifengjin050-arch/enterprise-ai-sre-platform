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

SSH 托管服务器的密码/私钥、以及知识源连接器配置，均使用由 `JWT_SECRET` 派生的 Fernet 密钥加密后写入数据库。更换 `JWT_SECRET` 后旧密文将无法解密，需要重新保存凭据。

历史遗留的 SSH 明文凭据在读取时仍可兼容，但新写入一律加密。API 响应永不回传 `auth_credential`。

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
