# Ramulator2 Runtime Bundle

This directory stores the Windows x64 Ramulator2 runtime used by the HBM E2E backend when `RAMULATOR2_HOME` is not set.

Included artifacts:

- `python/ramulator/_ramulator.cp311-win_amd64.pyd` - Python 3.11 C++ extension
- `python/ramulator/ramulator.dll` - Ramulator2 runtime DLL
- `lib/win_amd64/ramulator.lib` - MSVC import library for relinking
- `python/ramulator/**/*.py` - generated Ramulator2 Python DSL and component wrappers

The backend resolves this folder before the source tree, so the application can run without the full `ramulator2` source checkout. Rebuild the source tree only when the C++ simulator changes, then refresh these files from `ramulator2/python/ramulator` and `ramulator2/build-msvc/ramulator.lib`.
