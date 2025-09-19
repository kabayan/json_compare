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
├── config_management.py            # Configuration file management and validation
├── console_network_monitor.py      # Playwright MCP console/network monitoring
├── drag_drop_manager.py             # Playwright MCP drag-and-drop operations
├── llm_configuration_manager.py     # Playwright MCP LLM settings management
├── tab_navigation_manager.py        # Playwright MCP tab navigation and history
├── test_data_manager.py             # Test data generation and management
├── page_navigator.py                # Page navigation and URL handling
├── viewport_manager.py              # Viewport and display management
├── file_upload_manager.py           # File upload and form interaction
├── form_interaction_manager.py      # Form field interaction and validation
├── download_and_error_manager.py    # Download handling and error management
├── comparison_result_validator.py   # Cross-method result validation and anomaly detection
├── mcp_wrapper.py                   # Lightweight Playwright MCP wrapper
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
├── test_playwright_mcp_wrapper.py        # Playwright MCP軽量ラッパーテスト（実装済み）
├── test_strategy_integration.py          # Strategy pattern tests
├── test_comparison_result_validator.py   # Cross-method validation tests
├── test_console_network_monitor.py       # Console/network monitoring tests
├── test_drag_drop_manager.py             # Drag-and-drop operation tests
├── test_llm_configuration_manager.py     # LLM configuration tests
├── test_tab_navigation_manager.py        # Tab navigation and history tests
├── test_test_data_manager.py             # Test data management tests
├── test_page_navigation.py               # Page navigation tests
├── test_viewport_manager.py              # Viewport management tests
├── test_file_upload_manager.py           # File upload tests
├── test_form_interaction_manager.py      # Form interaction tests
├── test_advanced_form_operations.py      # Advanced form operation tests
├── test_download_and_error_manager.py    # Download and error handling tests
├── test_config_management.py             # Configuration management tests
├── mock_api_server.py                    # Mock API server for testing
└── fixtures/                             # Test data fixtures
    └── sample.jsonl                      # Sample test data
```

### Prompts (`prompts/`)
```
prompts/
├── default_similarity.yaml      # Default similarity prompt template (updated with markdown bold patterns)
├── semantic_similarity.yaml     # Semantic comparison prompt
├── strict_similarity.yaml       # Strict comparison prompt
├── [uuid].yaml                  # User-defined custom prompts (dynamically generated)
└── temp/                        # Temporary prompt files (auto-cleanup)
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
- **prompt_template.py**: Load and manage YAML prompt templates with validation
- **score_parser.py**: Extract numeric scores from LLM responses (enhanced with markdown bold support)
- **similarity_strategy.py**: Strategy pattern implementation for calculation methods
- **caching_resource_manager.py**: Cache LLM responses for efficiency
- **llm_metrics.py**: Track LLM usage statistics and performance
- **enhanced_result_format.py**: Result formatting with comparison method identification and conditional detailed output
- **config_management.py**: Configuration file validation, loading, and management system
- **comparison_result_validator.py**: Cross-method result validation and anomaly detection for quality assurance
- **console_network_monitor.py**: Playwright MCP-based console and network monitoring for WebUI testing
- **drag_drop_manager.py**: Playwright MCP-based drag-and-drop operations for file upload testing
- **llm_configuration_manager.py**: Playwright MCP-based LLM settings and model selection testing
- **tab_navigation_manager.py**: Playwright MCP-based tab management and navigation history testing
- **test_data_manager.py**: Test data generation, validation, and lifecycle management
- **page_navigator.py**: Page navigation, URL handling, and routing management
- **viewport_manager.py**: Viewport sizing, responsive design testing, and display management
- **file_upload_manager.py**: File upload operations, validation, and progress tracking
- **form_interaction_manager.py**: Form field interaction, validation, and submission handling
- **download_and_error_manager.py**: Download operations, error recovery, and status management
- **mcp_wrapper.py**: Lightweight wrapper for Playwright MCP operations with error handling and retry logic

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
5. **Validation Layer**:
   - Result validation (`comparison_result_validator.py`)
   - Quality assurance and anomaly detection
6. **Test Infrastructure Layer**:
   - Playwright MCP wrapper (`mcp_wrapper.py`)
   - WebUI test automation (`console_network_monitor.py`, `drag_drop_manager.py`)
   - LLM configuration testing (`llm_configuration_manager.py`)
   - Navigation testing (`tab_navigation_manager.py`)

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
    [Result Validation]
           ↓
    Add metadata & method identification
           ↓
    [Output Format Control]
           ↓
    ┌──────┴──────┐
    ↓             ↓
[Score Format] [File Format]
    ↓             ↓
 No detailed   Include detailed
  results       results array
    ↓             ↓
    └──────┬──────┘
           ↓
    Display/Save result
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
- Playwright MCP包括テストフレームワーク（実装済み）
  - 12の専門化されたテストマネージャーによる完全自動化
  - 43テストケース、100%成功率の実績
  - AIアシスタント統合によるWebUI機能テスト
  - 軽量ラッパーによる効率的なPlaywright操作
- Error handling tests (`test_error_handling.py`)
- Configuration management tests (`test_config_management.py`)
- Strategy pattern integration tests (`test_strategy_integration.py`)
- Fixtures for consistent test data
- 実際のvLLM APIとの統合テスト（モック未使用）
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
   - Integration tests for API（モック未使用）
   - Playwright MCP tests for Web UI（実装済みフレームワーク使用）
4. Update documentation
5. Test all interfaces (CLI, API, Web UI) before committing
6. Follow rules.md禁止事項（モック使用禁止、フォールバック実装禁止）

### Code Review Checklist
- [ ] Follows naming conventions
- [ ] Imports properly organized
- [ ] Single responsibility maintained
- [ ] Tests included（モック未使用）
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] rules.md禁止事項遵守
  - [ ] モック使用禁止
  - [ ] フォールバック実装禁止
  - [ ] テスト要件変更禁止
- [ ] 実装済み機能のみを使用
- [ ] llm-similarity-vllm仕様との整合性確認