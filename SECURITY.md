# Security and privacy model

This is a local, offline document reading tool, **not** a hardened public document-processing
service. Inputs may be malformed or adversarial.

- No network client or telemetry is called by project code.
- No embedded PDF instructions or user YAML are executed as code.
- Profile YAML uses `safe_load`, size/depth limits, typed config checks and an operation whitelist.
- Installed Python entry-point profiles are **trusted code** and are loaded only if explicitly
  selected. Install plugins only from vendors you trust.
- Source PDF and CSV files may be located outside the repo; the input path is not copied into
  result metadata, only the basename and hash.
- Readers process a single bounded in-memory byte snapshot and record its SHA-256.
- Output files and manifests may contain sensitive personal information; secure those folders.
- Output publication refuses overwrite and symlink targets. File permission behavior is
  subject to the host OS, filesystem, and directory permissions.
- Limits on bytes/pages/cells are useful but do not prevent all CPU/memory/exploit risks from
  malformed compressed streams in native/transitive PDF parsers.

For a public SaaS, add process isolation, resource quotas, read-only mounts, blocked outbound
networking, dependency lockfiles/CVE scanning, and extra tests before accepting untrusted users.
Never put real bank statements in the repository or CI artifacts.
