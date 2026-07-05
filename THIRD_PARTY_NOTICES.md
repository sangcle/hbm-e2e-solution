# Third-Party Notices

This repository includes third-party software and generated artifacts used by the local HBM E2E runtime.

## Ramulator2 Runtime Bundle

- Project: Ramulator2
- Upstream repository: `https://github.com/CMU-SAFARI/ramulator2`
- Upstream commit used for this runtime bundle: `c5b1c3a478b68853a61a0b8f99510d0dde7e6fd0`
- License: MIT
- Included path: `runtime/ramulator2`
- Included artifacts:
  - `runtime/ramulator2/python/ramulator/_ramulator.cp311-win_amd64.pyd`
  - `runtime/ramulator2/python/ramulator/ramulator.dll`
  - `runtime/ramulator2/lib/win_amd64/ramulator.lib`
  - `runtime/ramulator2/python/ramulator/**/*.py`

The upstream MIT license is included at `runtime/ramulator2/LICENSE`.

The checked runtime files are included so the backend can run without requiring users to rebuild the full Ramulator2 C++ source tree. The full local source checkout under `ramulator2/` is intentionally excluded from this repository.

## Frontend Packages

Frontend dependencies are resolved from npm through `frontend/package-lock.json`. Their package-level license metadata is recorded in that lockfile and is not vendored into this repository.
