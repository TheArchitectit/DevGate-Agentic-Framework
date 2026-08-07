# DevGate-Agentic-Framework

A quality engineering framework for AI agent development — test runner, regression scanner, deploy gates, CI workflows, and guardrails. Extracted from [pi-mega-compact](https://github.com/TheArchitectit/pi-mega-compact).

## What This Is

DevGate is the enforcement layer for AI-assisted development. It provides the tooling to validate, gate, and deploy code that was written by or with AI agents — ensuring the velocity of AI-generated code doesn't come at the cost of quality.

**DevGate is not another agent framework.** It's the quality gate that sits between your agents and your production code.

## Components

### Test Runner (`scripts/run-tests.mjs`)
- Node.js native test runner (`node --test`) with custom driver
- Per-file process isolation — each test file gets its own subprocess
- Parallel pooling (max 8 workers, configurable)
- Serial lanes for dashboard (port collision) and perf-budget (CPU sensitivity) tests
- Flake adjudication — failed files re-run solo; flakes pass with flag
- Hang-on-exit detection — open handles don't block the pool
- Stale temp-dir sweeper

### Regression Scanner (`scripts/regression_check.py`)
- File-size limit enforcement (src: 300 soft / 500 hard, extensions: 400 / 500, tests: 600 hard)
- npm audit gate (blocks on runtime HIGH/CRITICAL, warns on dev-only)
- Settings coverage check (every env var must have a dashboard entry)
- Soft-as-hard headroom gate — promotes soft violations to blocking, only for files changed since prior release tag
- Reads `.guardrails/failure-registry.jsonl` for known bug patterns

### Pattern Scanner (`scripts/guardrails-scan.mjs`)
- PREVENT-PI-004: no network constructors outside annotated exemptions
- PREVENT-PI-002: no SQL string concatenation
- PREVENT-PI-001: no JSON.parse without null check
- Supports inline `// guardrails-allow PREVENT-PI-xxx: <reason>` annotations

### Semantic Scanner (`scripts/semantic-scan.mjs`)
- AST-based using TypeScript compiler API
- SEMANTIC-001: detects `.then()` chains without `.catch()` (unhandled promise rejection)

### Schema Health Check (`scripts/schema-health-check.mjs`)
- Validates database schema integrity
- Checks for orphaned tables, missing indexes, constraint violations

### Deploy Pipeline (`scripts/deploy.sh`)
10-step gated publish pipeline:
1. Clean git tree check
2. Native deps pre-flight
3. Full gate (build + test + lint + regression + guardrails)
4. Schema health validation
5. React dashboard build (if applicable)
6. Critical verify — bundle exists in npm pack output
7. Dashboard tab smoke (Playwright headless)
8. Asset gate (encoder manifest + model + tokenizer present, package ≤ 80 MiB)
9. Version bump
10. Commit + tag + push (before npm publish — push failure aborts)
11. npm publish
12. Stale dashboard bounce
13. Merge to master
14. GitHub release
15. Post-publish device instructions

### CI Workflows (`.github/workflows/`)
| Workflow | Purpose |
|---|---|
| `ci.yml` | Full gate: build + test + lint + regression + schema health |
| `regression-guard.yml` | PR regression check + failure registry cross-reference + bot comment |
| `guardrails-lint.yml` | Scope boundaries, forbidden files, commit message format, AI attribution |
| `secret-validation.yml` | Gitleaks scan, .env file detection, hardcoded secret patterns |
| `documentation-check.yml` | 500-line doc limit, required sections, broken links, trailing whitespace |

### Pre-Commit Hook (`.claude/hooks/pre-commit.sh`)
Runs the full guardrails gate locally before commit.

### Failure Registry (`.guardrails/failure-registry.jsonl`)
Append-only JSONL log of historical bugs with:
- Affected files
- Root causes
- Prevention rules
- Status (active/resolved)

### Prevention Rules (`.guardrails/prevention-rules/`)
- `pattern-rules.json` — forbidden pattern definitions
- `pattern-rules.schema.json` — JSON schema for rule validation
- `semantic-rules.json` — AST-based semantic rules
- `extracted-rules.json` — extracted rule summaries

## Installation

### As a git submodule
```bash
git submodule add https://github.com/TheArchitectit/DevGate-Agentic-Framework.git .devgate
```

### As a direct clone
```bash
git clone https://github.com/TheArchitectit/DevGate-Agentic-Framework.git .devgate
```

### Copy specific tools
Each script is standalone. Copy only what you need:
```bash
# Just the test runner
curl -o scripts/run-tests.mjs https://raw.githubusercontent.com/TheArchitectit/DevGate-Agentic-Framework/main/scripts/run-tests.mjs

# Just the regression scanner
curl -o scripts/regression_check.py https://raw.githubusercontent.com/TheArchitectit/DevGate-Agentic-Framework/main/scripts/regression_check.py
```

## Usage

### Run the full test suite
```bash
node scripts/run-tests.mjs
```

### Run regression check
```bash
python3 scripts/regression_check.py --all
```

### Run guardrails scan
```bash
node scripts/guardrails-scan.mjs
```

### Run semantic scan
```bash
node scripts/semantic-scan.mjs
```

### Run the full gate (pre-commit)
```bash
bash .claude/hooks/pre-commit.sh
```

### Deploy
```bash
bash scripts/deploy.sh
```

## Configuration

### File Size Limits
Edit `scripts/regression_check.py` to adjust:
```python
SRC_SOFT = 300    # src/ soft limit (lines)
SRC_HARD = 500    # src/ hard limit
EXT_SOFT = 400    # extensions/ soft limit
EXT_HARD = 500    # extensions/ hard limit
TEST_HARD = 600   # test files hard limit
```

### Prevention Rules
Add custom patterns to `.guardrails/prevention-rules/pattern-rules.json`:
```json
{
  "id": "PREVENT-CUSTOM-001",
  "pattern": "eval\\(",
  "description": "No eval() usage",
  "severity": "error"
}
```

### Failure Registry
Append new entries to `.guardrails/failure-registry.jsonl`:
```json
{
  "id": "BUG-001",
  "title": "Missing dashboard bundle in npm package",
  "affected_files": ["extensions/dashboard-client/dist/index.html"],
  "root_cause": "Vite build ran but output wasn't included in npm pack files array",
  "prevention_rules": ["deploy.sh step 6 verifies bundle in npm pack --dry-run"],
  "status": "resolved",
  "date": "2026-07-15"
}
```

## Origin

Extracted from [pi-mega-compact](https://github.com/TheArchitectit/pi-mega-compact) v0.20.46, where this framework was battle-tested across:
- 332 test files (~3,900+ tests)
- 51 acceptance test aggregators
- 890 conformance fixtures
- 60 sprint specs with evidence records
- 20+ tagged releases

## License

BSD-3-Clause

## Author

TheArchitectit
