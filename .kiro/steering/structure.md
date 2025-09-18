# Project Structure

## Root Directory Organization

```
json_compare/
├── src/                    # Main source code
├── tests/                  # Test files
├── utils/                  # Utility scripts
├── logs/                   # Log files (auto-created)
├── docs/                   # Documentation
├── datas/                  # Data files (gitignored)
├── claudecodeui/           # Web UI assets (if present)
├── .kiro/                  # Kiro spec-driven development
│   ├── steering/          # Project steering documents
│   └── specs/             # Feature specifications
├── .claude/                # Claude Code configuration
│   └── commands/          # Custom commands
├── .venv/                  # Python virtual environment
├── pyproject.toml          # Package configuration
├── requirements.txt        # Python dependencies
├── README.md              # User documentation
├── WEB_UI_README.md       # Web UI documentation
├── CLAUDE.md              # Claude Code instructions
└── init.sh                # Environment setup script
```

## Subdirectory Structures

### Source Code (`src/`)
```
src/
├── __init__.py            # Package initialization
├── __main__.py            # CLI entry point
├── similarity.py          # Core similarity calculation logic
├── embedding.py           # Embedding model management
├── utils.py               # Utility functions
├── api.py                 # FastAPI server and Web UI
├── error_handler.py       # Error handling and user-friendly messages
├── logger.py              # Structured logging system
└── archives/              # Archived/deprecated code
    └── merge_jsonl.py     # Legacy JSONL merging utility
```

### Tests (`tests/`)
```
tests/
├── test_similarity.py           # Similarity calculation tests
├── test_embedding.py            # Embedding model tests
├── test_utils.py                # Utility function tests
├── test_integration.py          # API integration tests
├── test_error_handling.py       # Error handling tests
├── test_ui_playwright.py        # Web UI E2E tests
├── test_ui_playwright_improved.py # Enhanced Web UI tests
└── fixtures/                    # Test data fixtures
    └── sample.jsonl            # Sample test data
```

### Utilities (`utils/`)
```
utils/
├── fix_jsonl_format.py     # JSONL format correction tool
└── README.md               # Utility documentation
```

### Logs (`/tmp/json_compare/logs/`)
```
logs/                       # Auto-created at runtime
├── access.log             # HTTP request logs
├── error.log              # Error logs with IDs
└── metrics.log            # Performance metrics
```

### Documentation (`docs/`)
```
docs/
├── spec.md               # Feature specifications
├── rules.md              # Development rules
├── envs.md               # Environment setup
├── setup.md              # Installation guide
└── implementation_plan.md # Development roadmap
```

### Kiro Development (`.kiro/`)
```
.kiro/
├── steering/             # Project guidance
│   ├── product.md       # Product overview
│   ├── tech.md          # Technology stack
│   └── structure.md     # This file
└── specs/               # Feature specifications
    └── [feature]/       # Per-feature specs
        ├── requirements.md
        ├── design.md
        └── tasks.md
```

## Code Organization Patterns

### Module Responsibilities
- **__main__.py**: CLI argument parsing and command orchestration
- **similarity.py**: Business logic for JSON comparison and scoring
- **embedding.py**: ML model loading and vector generation
- **utils.py**: Shared utilities (JSON parsing, file I/O, progress bars)
- **api.py**: REST API endpoints, Web UI serving, file upload handling
- **error_handler.py**: User-friendly error messages, error IDs, recovery suggestions
- **logger.py**: Structured JSON logging with rotation and metrics tracking

### Layered Architecture
1. **Presentation Layer**: CLI (`__main__.py`), API (`api.py`), Web UI
2. **Business Logic**: Similarity calculation (`similarity.py`)
3. **Service Layer**: Embedding generation (`embedding.py`)
4. **Infrastructure Layer**:
   - Error handling (`error_handler.py`)
   - Logging (`logger.py`)
   - Utilities (`utils.py`)

### Data Flow
```
Input JSONL → Parse → Extract inference fields → Generate embeddings
→ Calculate similarity → Format output → Display/Save result
```

## File Naming Conventions

### Python Files
- **Modules**: lowercase with underscores (`similarity.py`, `embedding.py`)
- **Classes**: PascalCase in files (`class SimilarityCalculator`)
- **Functions**: snake_case (`calculate_similarity()`)
- **Constants**: UPPER_CASE (`DEFAULT_MODEL_NAME`)

### Data Files
- **Input**: `.jsonl` extension for JSON Lines format
- **Output**: `.json` for structured output
- **Temp files**: Prefixed with `tmp_` or in `/tmp/`

### Documentation
- **Markdown**: `.md` extension, lowercase with underscores
- **Specs**: Organized in feature-named directories
- **Commands**: Descriptive names in `.claude/commands/`

## Import Organization

### Standard Structure
```python
# 1. Standard library imports
import json
import sys
from pathlib import Path

# 2. Third-party imports
import torch
from transformers import AutoModel

# 3. Local application imports
from .embedding import EmbeddingGenerator
from .utils import parse_jsonl
```

### Relative vs Absolute
- **Within package**: Relative imports (`.embedding`, `..utils`)
- **Entry points**: Absolute imports (`src.similarity`)
- **Scripts**: Direct module execution (`python -m src.__main__`)

## Key Architectural Principles

### Single Responsibility
Each module handles one primary concern:
- Embedding: Model management only
- Similarity: Comparison logic only
- Utils: Shared helpers only

### Dependency Injection
- Model paths configurable via CLI arguments
- Device selection (CPU/GPU) at runtime
- Output format determined by user choice

### Error Handling
- JSON repair for malformed input
- Graceful degradation for missing fields
- Clear error messages with context

### Performance Optimization
- Lazy model loading (on first use)
- Batch processing for multiple comparisons
- Optional GPU acceleration
- Model caching to avoid re-downloads

### Testing Strategy
- Unit tests for each module (`test_*.py`)
- Integration tests for API endpoints (`test_integration.py`)
- E2E tests for Web UI (`test_ui_playwright*.py`)
- Error handling tests (`test_error_handling.py`)
- Fixtures for consistent test data
- Mock external dependencies (model downloads)
- Automated testing with pytest and playwright

### Configuration Management
- `pyproject.toml` for package metadata
- CLI arguments for runtime configuration
- No hardcoded paths or credentials
- Environment variables for system config

## Development Workflows

### Adding New Features
1. Create spec in `.kiro/specs/[feature]/`
2. Implement in appropriate module
3. Add tests in `tests/`
   - Unit tests for core logic
   - Integration tests for API
   - Playwright tests for Web UI
4. Update documentation
5. Test all interfaces (CLI, API, Web UI) before committing

### Code Review Checklist
- [ ] Follows naming conventions
- [ ] Imports properly organized
- [ ] Single responsibility maintained
- [ ] Tests included
- [ ] Documentation updated
- [ ] No hardcoded values