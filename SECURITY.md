# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.5.x   | ✓ Current |
| < 2.5   | ✗         |

## Reporting a Vulnerability

If you discover a security vulnerability, **do not open a public GitHub issue**.

Please report it by emailing the maintainer directly or opening a private
security advisory on GitHub:
`Settings → Security → Advisories → New draft security advisory`

Include:
- A description of the vulnerability
- Steps to reproduce
- The potential impact

You can expect an acknowledgment within **72 hours** and a fix or mitigation
timeline within **14 days** for critical issues.

## Security Considerations

### Configuration File (`config/config.toml`)

- `config/config.toml` is **not committed** to VCS (it is in `.gitignore`)
- It may contain API keys (`search.meilisearch.api_key`) — keep it private
- Use `config/config.toml.template` as the committed baseline
- For production, prefer environment variable overrides:
  `APP__SEARCH__MEILISEARCH__API_KEY=<secret>`

### API Server

- The REST API (`src/api/`) binds to `127.0.0.1` by default
- Do **not** expose port 8200 to the public internet without authentication
- If deploying behind a reverse proxy, add appropriate rate-limiting and auth

### File System Access

- IndexationScanner respects `allowed_roots` enforced by PathManager
- Paths outside allowed roots are rejected (`PathSecurityError`)
- Never configure `indexing.include_paths` to include system directories

### Dependencies

- Dependencies are pinned in `pyproject.toml`
- Run `pip audit` periodically to check for known CVEs:
  ```
  pip install pip-audit
  pip-audit
  ```

### Logs

- Log files (`data/logs/`) may contain file paths and query content
- Restrict read access: `chmod 600 data/logs/*.log`
- Log rotation is configured via `logger.max_file_mb` and `logger.max_files`
