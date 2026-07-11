# Universal Pre-Commit Validation Framework

A production-ready, highly modular, and extensible pre-commit validation framework designed to orchestrate code formatting, linting, compilation builds, test execution, security scans, and code coverage checks across multiple programming languages and environments.

Designed with **SOLID design principles**, it auto-detects codebase languages and executes strict validation gates before code is committed to Git or pushed to remote CI systems.

---

## Folder Structure

```text
universal-precommit/
│
├── .pre-commit-config.yaml    # Git pre-commit hooks configuration
├── README.md                  # Comprehensive framework documentation
├── requirements.txt           # Python baseline dependencies
│
├── config/
│   └── config.yaml            # Pipeline stages and tool configuration
│
├── scripts/
│   ├── common.py              # Shared abstractions and BaseChecker base class
│   ├── config.py              # Parser and dataclasses for config.yaml
│   ├── detect_project.py      # Scan rules for language footprints (Monorepo support)
│   ├── python_check.py        # Python checker wrapper (Ruff, Black, Pytest, etc.)
│   ├── react_check.py         # React/JS checker wrapper (Prettier, ESLint, npm)
│   ├── dotnet_check.py        # .NET C# checker wrapper (dotnet format, build, test)
│   ├── java_check.py          # Java Maven/Gradle checker wrapper (Spotless, Checkstyle)
│   ├── run_validation.py      # Entry point orchestrator & Git hook receiver
│   └── utils.py               # Process executor, colored console, and logging utilities
│
└── .github/
    └── workflows/
        └── ci.yml             # GitHub Actions CI workflow pipeline
```

---

## Supported Languages & Tools

| Language | Footprints / Markers | Formatter | Linter | Build / Compiler | Test Runner | Security & Auditing | Coverage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Python** | `pyproject.toml`, `requirements.txt`, `setup.py` | `black`, `isort` | `ruff check` | Bytecode syntax verification | `pytest` | `bandit`, `pip-audit` | `pytest-cov` |
| **React (JS/TS)** | `package.json` | `prettier` | `eslint` | `npm run build` | `npm test` | `npm audit` | Jest coverage reports |
| **.NET (C#)** | `*.csproj`, `*.sln` | `dotnet format` | Style analysis checks | `dotnet build` | `dotnet test` | `dotnet list package --vulnerable` | Coverlet collectors |
| **Java** | `pom.xml`, `build.gradle`, `build.gradle.kts` | Spotless apply | Checkstyle check / Gradle check | Maven compile / Gradle build | Maven/Gradle test | OWASP Dependency Check | JaCoCo reports |

### Global Quality Gates
- **Conventional Commit Messages**: Enforces structure like `feat(auth): login integration` on staging.
- **Branch Protection**: Scans for direct commits to production-critical branches (`main`, `master`, `develop`) and outlines safety steps.
- **Gitleaks**: Auto-scans codebase for exposed passwords, keys, or credentials.

---

## Installation

### Prerequisites
1. **Python 3.12+** installed and added to your environment `PATH`.
2. Target toolchains installed globally or in project directories depending on repository types (e.g., `npm`, `dotnet`, `java`/`mvn`/`gradle`).
3. (Optional) [Gitleaks CLI](https://github.com/gitleaks/gitleaks) installed for secrets validation.

### Setup Steps
1. Clone or copy this framework into your project workspace root.
2. Install framework dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install the pre-commit environment helper tool:
   ```bash
   pip install pre-commit
   ```
4. Install the Git hooks:
   ```bash
   pre-commit install --hook-type pre-commit --hook-type commit-msg
   ```

---

## Configuration (`config.yaml`)

Control stages and custom security scanners via `config/config.yaml`:

```yaml
stages:
  formatter: true      # Run code styling engines
  lint: true           # Run static program code analysis
  build: true          # Validate that code compiles cleanly
  tests: true          # Run unit test suites
  security_scan: true  # Audit code security and vulnerabilities
  coverage: true       # Run code test coverage evaluation

security:
  bandit: true                  # Python Bandit scanning
  pip_audit: true               # Python dependency audit
  npm_audit: true               # Node package vulnerability audit
  owasp_dependency_check: false # Java OWASP vulnerability audit (requires plugin config)
  gitleaks: false               # Gitleaks API/secrets validator

git:
  conventional_commits: true    # Enforce conventional commit structures
  branch_protection: true       # Warn on direct push to master/main branches
```

---

## Usage

### Automated Execution (Git Hooks)
Once installed, the framework triggers automatically:
- On `git commit`: Runs formatting, linting, builds, testing, security, and coverage scans for detected codebases.
- On commit message write (`commit-msg` phase): Validates standard Conventional Commit formatting rules.

### Manual Execution (CLI Runner)
You can trigger validation checks manually using Python at any time:

```bash
# Run all validation stages for all auto-discovered projects
python scripts/run_validation.py

# Run a specific validation stage only (e.g., tests)
python scripts/run_validation.py --stage tests

# Parse a custom configuration schema
python scripts/run_validation.py --config path/to/custom-config.yaml --log execution.log
```

---

## Adding a New Language

The validation framework is designed for easy extension without modifications to the runner logic:

1. **Create Checker Class**: Create a new checker script in the `scripts/` folder (e.g., `scripts/go_check.py`).
2. **Inherit BaseChecker**: Inherit from `BaseChecker` (defined in [common.py](file:///d:/Yoburaj/Universal%20Pre-Commit%20Hook/scripts/common.py)) and implement abstract properties and methods:
   ```python
   from common import BaseChecker
   from utils import CommandResult, run_command

   class GoChecker(BaseChecker):
       @property
       def name(self) -> str:
           return "Go"

       def detect(self) -> bool:
           return (self.context.project_root / "go.mod").exists()

       def run_formatter(self) -> CommandResult:
           return run_command(["go", "fmt", "./..."], cwd=self.context.project_root)

       # Implement run_lint, run_build, run_tests, run_security_scan, run_coverage...
   ```
3. **Register Checker**: Import and append your class to `detect_projects` in [detect_project.py](file:///d:/Yoburaj/Universal%20Pre-Commit%20Hook/scripts/detect_project.py):
   ```python
   from go_check import GoChecker
   # Inside detect_projects scan loops:
   if (current_dir / "go.mod").exists():
       detected_checkers.append(GoChecker(sub_context))
   ```

---

## Troubleshooting

### "Executable command not found" (e.g. `black` or `eslint`)
- **Reason**: The runner attempts to run tools in shell environment sub-processes.
- **Solution**: Ensure your target languages toolchains are installed and in your environment `PATH`. Alternatively, run `npm install`, setup a python virtualenv and install dependencies (`pip install black ruff pytest pytest-cov bandit pip-audit`).

### Java wrapper failures on Windows
- **Reason**: Unix wrappers (`./mvnw`, `./gradlew`) don't execute natively on Windows CMD/PowerShell.
- **Solution**: The `JavaChecker` class automatically handles wrappers by targeting `.cmd` or `.bat` executable paths on Windows systems. If your project does not contain wrapper files, it falls back to system global `mvn`/`gradle` executables.

### Stage Skipped status in Summary
- **Reason**: The stage is disabled globally in your `config.yaml`, or the language-specific checker class does not implement that specific stage.
