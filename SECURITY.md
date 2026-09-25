# Security Policy

**English** | [简体中文](docs/zh/SECURITY.md) | [Русский](docs/ru/SECURITY.md) | [Français](docs/fr/SECURITY.md)

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest commit on `main` | ✅ |

We do not maintain separate release branches. Security fixes are applied directly to `main`.

---

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please report them privately via one of the following channels:

- **GitHub Security Advisories**: [Report a vulnerability](https://github.com/chen-xin-Liam/powerful-claw/security/advisories/new)
- **Email**: Open a private discussion on the repository with the `security` label

### What to include

1. **Description** — What the vulnerability is and how it can be exploited
2. **Impact** — What an attacker could achieve (data exposure, code execution, privilege escalation, etc.)
3. **Reproduction steps** — Minimal steps or proof-of-concept code to trigger the issue
4. **Environment** — OS, Python version, affected modules (AI service, WebSocket server, MCP, etc.)
5. **Suggested fix** (optional) — If you have a patch or mitigation idea

### What to expect

| Stage | Timeline |
|-------|----------|
| Acknowledgment | Within 72 hours |
| Initial assessment | Within 7 days |
| Fix or mitigation | Depends on severity (critical issues prioritized) |
| Public disclosure | After fix is merged, with credit to reporter (unless anonymity requested) |

---

## Security Model

### Permission Levels

The application enforces a **4-level permission model** for AI agent operations:

| Level | Capabilities |
|-------|-------------|
| **None** | No screen access, no input simulation |
| **View** | Screen capture only, read-only |
| **Limited** | Screen capture + restricted keyboard/mouse (excludes system-critical areas) |
| **Full** | Full screen access + unrestricted keyboard/mouse |

**Default**: `None` — no agent operations are permitted until explicitly enabled by the user.

### Data Handling

- **API keys** are stored locally in `.env` or `config/settings.ini` — never transmitted to third parties
- **Screen captures** are processed locally; they are only sent to the configured AI provider when the user triggers an AI request
- **Conversation history** is stored locally in `conversations.json` — excluded from version control
- **LAN cluster communication** uses Fernet symmetric encryption (AES-128-CBC) with RSA key exchange

### Network Services

| Port | Service | Exposure |
|------|---------|----------|
| 15000 | WebSocket (primary) | `0.0.0.0` — LAN-accessible |
| 15001 | WebSocket (secondary) | `0.0.0.0` |
| 15002 | HTTP API server | `0.0.0.0` |
| 15003 | WebSocket (API) | `0.0.0.0` |
| 15004 | Screen monitor | `0.0.0.0` |
| 15010 | Video editor | `0.0.0.0` |
| 15012 | Video editor WebSocket | `0.0.0.0` |

**Note**: These services bind to `0.0.0.0` by default for LAN functionality. If you do not need remote access, restrict them via firewall rules.

### MCP Servers

MCP servers are launched as **local subprocesses** with stdio transport. They inherit the application's environment variables, including API keys. Only import MCP configurations from trusted sources.

---

## Known Security Considerations

- **Desktop automation**: The agent can simulate keyboard/mouse input. Malicious prompts or compromised AI providers could trigger unintended actions. Use the `Limited` permission level when possible.
- **Screen capture**: Screenshots may contain sensitive information (passwords, personal data). The application does not filter sensitive content before sending to AI providers.
- **Unvalidated MCP servers**: Imported MCP servers run with the same privileges as the main application. Review configurations before importing.
- **No sandboxing**: The application runs with the user's full OS privileges. Exercise caution when enabling `Full` permission mode.

---

## Best Practices for Users

1. **Use `View` or `Limited` permissions** unless you specifically need full automation
2. **Do not expose ports 15000–15012 to the public internet** — use a firewall to restrict to LAN only
3. **Keep API keys out of version control** — use `.env` files (already in `.gitignore`)
4. **Review MCP configurations** before importing from external sources
5. **Regularly update dependencies** — run `pip install -U -r requirements.txt` to pick up security patches

---

## Scope

The following are **in scope** for security reports:

- Authentication/authorization bypass in the permission model
- Remote code execution via network services
- API key leakage through logs or network traffic
- Privilege escalation in MCP server management
- Data exposure (screen captures, conversation history, API keys) to unauthorized parties

The following are **out of scope**:

- Vulnerabilities in third-party dependencies (report to the upstream project)
- Social engineering attacks
- Physical access to the machine
- Issues requiring user to disable security features (e.g., setting permission to `Full`)
