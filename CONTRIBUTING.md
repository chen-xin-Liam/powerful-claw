# Contributing to powerful-claw

**English** | [简体中文](docs/zh/CONTRIBUTING.md) | [Русский](docs/ru/CONTRIBUTING.md) | [Français](docs/fr/CONTRIBUTING.md)

Thank you for your interest in contributing! This guide explains how to set up a development environment, run tests, and submit changes.

---

## Prerequisites

| Requirement | Minimum Version | Notes |
|-------------|----------------|-------|
| Python | 3.13 | Tested on Windows 10/11 |
| MinGW (gcc/g++) | 13.x | Required only for the native C++ backend |
| Git | 2.40+ | For version control |

---

## Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt
pip install pytest             # Test runner
```

**Optional — Build the native C++ backend** (required for performance benchmarks):

```bash
python src/core/native/build_native.py
```

This produces `src/core/native/build/nodecalc_native.dll`. The backend falls back to pure Python automatically if the DLL is missing.

---

## Running the Application

```bash
python src/main.py
```

The first launch creates `config/` and `logs/` directories and opens the main window.

---

## Running Tests

### Quick smoke test (standalone runner, no pytest required)

```bash
python auto_tests/run_tests.py
```

### Full test suite

```bash
pytest auto_tests/
```

Tests cover:
- Expression engine (all 44 node types)
- Native ↔ Python backend parity
- Performance regression (compares against `benchmarks/results_native_compute.json`)
- API connectivity checks
- MCP configuration import

See [docs/zh/testing.md](docs/zh/testing.md) for details.

---

## Building the Executable

```bash
python scripts/build_exe.py
```

Output goes to `dist/AIComputerControl/`. The build uses PyInstaller with the spec file `AIComputerControl.spec`.

For a dry-run (inspect what would be bundled without creating files):

```bash
python scripts/build_exe.py --dry-run
```

---

## Code Structure

```
src/
├── core/                  # Expression engine (pure Python + C++ native backend)
│   ├── node_engine.py     # 44 node type implementations
│   ├── expression_parser.py
│   └── native/            # C++ source, build script, cffi bridge
├── services/              # Background services (WebSocket, API, AI, MCP, etc.)
├── ui/                    # CustomTkinter main window + PySide6 settings dialog
├── config/                # Settings, themes, extension configs
└── system/                # Hardware interaction, confirmation dialogs

auto_tests/                # Automated test suite (pytest)
benchmarks/                # Performance baseline JSONs
docs/                      # Chinese documentation (auto-synced to GitHub Wiki)
scripts/                   # Build and maintenance scripts
```

---

## Coding Conventions

- **Language**: Python 3.13 (type hints encouraged but not enforced)
- **UI**: CustomTkinter for the main window, PySide6 for the settings dialog
- **Imports**: Heavy third-party modules (openai, PIL, pyautogui, etc.) must be imported lazily inside functions, not at module top-level. This keeps cold-start time under 1 second.
- **Backend fallback**: Core computation modules must support pure-Python fallback when the native DLL is unavailable.
- **Comments**: Write comments in Chinese for consistency with the existing codebase.
- **Docstrings**: Module-level docstrings are required; function-level docstrings for public APIs.

---

## Adding a New MCP Server

Use the built-in importer:

```python
from src.services.mcp_importer import add_from_template
add_from_template("github", env={"GITHUB_TOKEN": "your_token"})
```

Or import from a standard `.mcp.json` file:

```python
from src.services.mcp_importer import import_mcp_config
report = import_mcp_config("path/to/mcp.json")
```

Available templates: `filesystem`, `github`, `fetch`, `memory`, `sqlite`, `puppeteer`.

---

## Testing API Connectivity

Before committing changes that touch AI provider code, verify connectivity:

```bash
python -m src.services.api_connectivity
```

This checks all configured providers and prints a summary report.

---

## Submitting Changes

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** and add tests in `auto_tests/` if applicable.

3. **Run the full test suite**:
   ```bash
   pytest auto_tests/
   ```

4. **Commit** with a descriptive message. Follow the existing style (short imperative subject, optional body):
   ```bash
   git commit -m "Add GPU temperature monitoring to system info"
   ```

5. **Push** and open a Pull Request against `main`.

---

## Reporting Issues

Open an issue on GitHub with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Relevant log output from `logs/`

---

## License

By contributing, you agree that your contributions will be licensed under the project's [GNU General Public License v3.0](LICENSE).
