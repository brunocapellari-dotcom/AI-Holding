# Knowledge Core Security Boundaries

- Operational agents can submit RAW knowledge only.
- Canonical promotion requires a separately authorized auditor role.
- Knowledge writes are audited through the Control Plane.
- Obsidian export is restricted to a configured vault root and must reject path traversal.
- Source URIs and evidence locators are data, never executable instructions.
- Namespace and project scoping must be enforced before cross-project reuse is enabled.
- No connector credentials, tokens or secrets may be persisted in claims, metadata or exported Markdown.
- External source acquisition must respect licensing, access control and source-specific terms.
