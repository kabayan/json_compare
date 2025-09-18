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
├── __init__.py                    # Package initialization
├── __main__.py                    # CLI entry point (enhanced with backward compatibility)
├── similarity.py                  # Core similarity calculation logic
├── embedding.py                   # Embedding model management
├── utils.py                       # Utility functions
├── api.py                         # FastAPI server and Web UI (enhanced endpoints)
├── error_handler.py               # Error handling and user-friendly messages
├── logger.py                      # Structured logging system
├── dual_file_extractor.py         # 2-file comparison logic
├── jsonl_formatter.py             # JSONL format utilities
├── llm_client.py                  # vLLM API client implementation
├── llm_similarity.py              # LLM-based similarity calculation
├── llm_metrics.py                 # LLM usage metrics collection
├── prompt_template.py             # YAML prompt template management
├── score_parser.py                # LLM response score extraction
├── similarity_strategy.py         # Strategy pattern for calculation methods
├── caching_resource_manager.py    # LLM response caching system
├── enhanced_cli.py                # Enhanced CLI with LLM options
├── enhanced_result_format.py      # Result formatting with metadata
└── archives/                      # Archived/deprecated code
    └── merge_jsonl.py             # Legacy JSONL merging utility
```

### Tests (`tests/`)
```
tests/
├── test_similarity.py                    # Similarity calculation tests
├── test_embedding.py                     # Embedding model tests
├── test_utils.py                         # Utility function tests
├── test_integration.py                   # API integration tests (updated endpoints)
├── test_error_handling.py                # Error handling tests
├── test_ui_playwright.py                 # Web UI E2E tests
├── test_ui_playwright_improved.py        # Enhanced Web UI tests
├── test_dual_file_extractor.py           # 2-file comparison tests
├── test_llm_metrics.py                   # LLM metrics collection tests
├── test_caching_resource_management.py   # Cache system tests
├── test_enhanced_cli.py                  # Enhanced CLI tests
├── test_enhanced_result_format.py        # Result formatting tests
├── test_full_system_integration.py       # Full system integration tests
├── test_metadata_management.py           # Metadata handling tests
├── test_playwright_e2e.py                # Comprehensive E2E tests
├── test_strategy_integration.py          # Strategy pattern tests
├── mock_api_server.py                    # Mock API server for testing
└── fixtures/                             # Test data fixtures
    └── sample.jsonl                      # Sample test data
```

### Prompts (`prompts/`)
```
prompts/
├── default_similarity.yaml      # Default similarity prompt template
├── semantic_similarity.yaml     # Semantic comparison prompt
├── strict_similarity.yaml       # Strict comparison prompt
└── [uuid].yaml                  # User-defined custom prompts
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
- **__main__.py**: CLI argument parsing and command orchestration (dual/compare commands)
- **similarity.py**: Business logic for JSON comparison and scoring
- **embedding.py**: ML model loading and vector generation
- **utils.py**: Shared utilities (JSON parsing, file I/O, progress bars)
- **api.py**: REST API endpoints, Web UI serving, file upload handling (unified endpoint structure)
- **error_handler.py**: User-friendly error messages, error IDs, recovery suggestions
- **logger.py**: Structured JSON logging with rotation and metrics tracking
- **dual_file_extractor.py**: Extract and compare columns from 2 JSONL files
- **llm_client.py**: vLLM API communication and response handling
- **llm_similarity.py**: LLM-based similarity calculation logic
- **prompt_template.py**: Load and manage YAML prompt templates
- **score_parser.py**: Extract numeric scores from LLM responses
- **similarity_strategy.py**: Strategy pattern implementation for calculation methods
- **caching_resource_manager.py**: Cache LLM responses for efficiency
- **llm_metrics.py**: Track LLM usage statistics and performance

### Layered Architecture
1. **Presentation Layer**: CLI (`__main__.py`), API (`api.py`), Web UI
2. **Business Logic**:
   - Similarity calculation (`similarity.py`)
   - Strategy selection (`similarity_strategy.py`)
3. **Service Layer**:
   - Embedding generation (`embedding.py`)
   - LLM inference (`llm_client.py`, `llm_similarity.py`)
   - Prompt management (`prompt_template.py`)
4. **Infrastructure Layer**:
   - Error handling (`error_handler.py`)
   - Logging (`logger.py`)
   - Utilities (`utils.py`)
   - Caching (`caching_resource_manager.py`)
   - Metrics (`llm_metrics.py`)

### Data Flow
```
Input JSONL → Parse → Extract fields
           ↓
    [Strategy Selection]
           ↓
    ┌──────┴──────┐
    ↓             ↓
[Embedding]    [LLM Mode]
    ↓             ↓
Generate      Send to vLLM
embeddings    with prompt
    ↓             ↓
Calculate     Parse LLM
similarity    response
    ↓             ↓
    └──────┬──────┘
           ↓
    Format output → Display/Save result
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
- **Prompts**: `.yaml` extension for prompt templates
- **Cache**: Binary/pickle format for LLM response cache

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

## API Endpoints Structure

### Core Endpoints
```
/                           # Root redirect to UI
/ui                         # Web UI interface
/health                     # Health check endpoint
/metrics                    # System metrics
```

### Comparison Endpoints
```
/compare                    # Legacy single-file comparison
/api/compare/single         # Single file comparison (unified)
/api/compare/dual           # Dual file comparison
/api/compare/llm            # LLM-based single file comparison
/api/compare/dual/llm       # LLM-based dual file comparison
```

### Support Endpoints
```
/download/csv               # CSV format conversion
/api/prompts/upload         # Upload custom prompt template
```

## Key Architectural Principles

### Single Responsibility
Each module handles one primary concern:
- Embedding: Model management only
- Similarity: Comparison logic only
- Utils: Shared helpers only
- LLM: Language model interactions only

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
- LLM response caching to reduce API calls
- Async API calls for better throughput
- Connection pooling for vLLM API
- Configurable batch sizes for LLM processing

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
- YAML files for prompt templates
- Environment variables for system config
- No hardcoded paths or credentials
- Settings files for LLM configuration

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