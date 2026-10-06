# Data Contracts

The canonical corporate format is `holding-data-contract-v1`.

- Contract specifications are version-controlled in Git.
- The Data Contract Registry indexes ownership, version, execution engine, latest verification and
  evidence.
- Projects may add engine adapters (for example Soda Core), but the native contract must remain
  complete and portable.
- A blocking contract failure prevents promotion of dependent datasets/releases until resolved or
  explicitly waived through governance.
- Source references must use the corporate Source Registry.
- Licenses/usage constraints must use the corporate License Registry where applicable.
