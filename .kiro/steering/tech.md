# Technology Stack

## Architecture
- **Type**: CLI Tool with optional Web API
- **Pattern**: Command-line interface with modular Python architecture
- **Deployment**: Standalone executable via uvx or local Python environment
- **Processing Model**: Batch processing with optional GPU acceleration
- **Computation Strategy**: Strategy pattern for embedding-based or LLM-based processing
- **Testing Strategy**: Playwright MCP統合（導入済み、軽量ラッパーで実装）

## Core Technologies

### Language & Runtime
- **Python**: 3.8+ (Primary language)
- **Package Manager**: uv/uvx (Modern Python package management)
- **Build System**: setuptools with pyproject.toml

### Machine Learning Stack
- **Transformers**: 4.30+ (Hugging Face transformers library)
- **PyTorch**: 2.0+ (Deep learning framework)
- **Model**: cl-nagoya/ruri-v3-310m (Japanese embedding model)
- **SentencePiece**: 0.1.99+ (Tokenization)
- **SciPy**: 1.10+ (Scientific computing, similarity calculations)

### LLM Integration Stack
- **vLLM API**: External LLM inference service support
- **httpx**: 0.28.1+ (Async HTTP client for LLM API calls)
- **PyYAML**: 6.0.2+ (YAML-based prompt template management)
- **Supported Models**: Qwen, Llama, and other vLLM-compatible models
- **Comparison Method Identification**: Automatic tagging of similarity calculation methods (embedding vs llm)
- **Strategy Pattern**: Dynamic switching between embedding and LLM calculation methods
- **Caching System**: LLM response caching for improved performance
- **Configuration Management**: Advanced YAML-based configuration with validation
- **Metrics Collection**: Comprehensive LLM usage tracking and performance monitoring

### Data Processing
- **json-repair**: 0.50.1 (Automatic JSON fixing)
- **protobuf**: 3.20+ (Data serialization)
- **tqdm**: 4.66+ (Progress bar for large file processing)

### Web API & UI
- **FastAPI**: 0.104.1 (Modern web framework)
- **Uvicorn[standard]**: 0.24.0 (ASGI server)
- **python-multipart**: 0.0.6 (File upload handling)
- **pydantic**: 2.5.0 (Data validation)
- **SSE/WebSocket** [計画中]: リアルタイム進捗更新のための通信機構

### Testing & Development
- **pytest**: 8.0+ (Testing framework)
- **pytest-asyncio**: 0.21+ (Async test support)
- **pytest-playwright**: 0.4+ (Web UI testing)
- **playwright**: 1.40+ (Browser automation for E2E tests)
- **Playwright MCP Framework**: 完全統合済み (AIアシスタント連携テスト自動化)
  - **Test Managers**: 12の専門化されたテストマネージャー
  - **Coverage Areas**: UI操作、ファイルアップロード、LLM設定、ナビゲーション
  - **Automation Level**: 43テストケース、100%自動化
  - **MCP Wrapper**: 軽量ラッパーによる効率的なPlaywright操作
- **httpx**: 0.28.1+ (HTTP client for API testing)

### Monitoring & Logging
- **psutil**: 5.9+ (System resource monitoring)
- **Structured logging**: JSON format with rotation support

## Development Environment

### Setup Requirements
```bash
# Clone repository
git clone <repository>
cd json_compare

# Using uv (recommended)
uv sync

# Or traditional pip
pip install -e .
```

### Virtual Environment
- **.venv**: Local Python virtual environment
- **Python Version**: 3.8-3.12 compatible

## Common Commands

### Development
```bash
# Run with uv
uv run python -m src.__main__ <input.jsonl> [options]

# Run unit tests
uv run pytest tests/

# Run integration tests (requires API server running)
uv run python tests/test_integration.py

# Run Web UI tests with Playwright
uv run playwright install chromium
uv run pytest tests/test_ui_playwright_improved.py -xvs

# Run Playwright MCP tests (包括的テストフレームワーク)
# 全テストマネージャーの実行
uv run pytest tests/test_*_manager.py -v

# 特定のテストマネージャー実行
uv run pytest tests/test_llm_configuration_manager.py -v
uv run pytest tests/test_drag_drop_manager.py -v
uv run pytest tests/test_console_network_monitor.py -v

# LLM機能統合テスト（実際のvLLM API使用）
uv run pytest tests/test_task_6_api_llm_integration.py -v
uv run pytest tests/test_task_3_2_score_processing.py -v
uv run pytest tests/test_task_4_1_strategy_switching.py -v

# Format code
uv run black src/
uv run isort src/

# Type checking
uv run mypy src/
```

### Production
```bash
# Via uvx (no install required)
uvx --from . json_compare <input.jsonl> [options]

# 2ファイル比較
json_compare dual file1.jsonl file2.jsonl --type score

# LLMベースの類似度判定
json_compare <input.jsonl> --llm --model qwen3-14b-awq

# Start API/Web UI server
uv run json_compare_api

# With GPU support
uvx --from . json_compare <input.jsonl> --gpu

# LLMとGPU両方を使用
json_compare <input.jsonl> --gpu --llm

# カスタムプロンプトテンプレート使用
json_compare <input.jsonl> --llm --prompt prompts/semantic_similarity.yaml

# LLM設定を環境変数で指定
export VLLM_API_URL="http://localhost:8000"
export LLM_MODEL_NAME="qwen3-14b-awq"
json_compare <input.jsonl> --llm
```

### Build & Distribution
```bash
# Build package
uv build

# Create distribution
python -m build
```

### Utility Tools
```bash
# Fix JSONL format (multi-line to single-line)
python3 utils/fix_jsonl_format.py data.jsonl

# Fix all JSONL files in directory
python3 utils/fix_jsonl_format.py --dir ./datas

# Validate JSONL file
python3 utils/fix_jsonl_format.py --validate data.jsonl
```

## Environment Variables

### Model Configuration
- **TRANSFORMERS_CACHE**: Cache directory for downloaded models
- **TORCH_DEVICE**: Force specific device (cpu/cuda)
- **HF_HOME**: Hugging Face home directory

### LLM Configuration
- **VLLM_API_URL**: vLLM API endpoint URL (default: http://192.168.1.18:8000)
- **VLLM_API_KEY**: API key for vLLM service (if required)
- **LLM_MODEL_NAME**: Default LLM model to use (default: qwen3-14b-awq)
- **LLM_TEMPERATURE**: Generation temperature (default: 0.2)
- **LLM_MAX_TOKENS**: Maximum tokens for generation (default: 64 for score format, 128 for file format)
- **PROMPT_TEMPLATE_DIR**: Directory for custom prompt templates (default: prompts/)
- **LLM_CACHE_SIZE**: Maximum size of LLM response cache
- **LLM_BATCH_SIZE**: Batch size for LLM processing
- **LLM_TIMEOUT**: Request timeout for LLM API calls (seconds)
- **COMPARISON_METHOD_METADATA**: Enable detailed method identification (default: true)
- **LLM_FALLBACK_ENABLED**: Enable automatic fallback to embedding mode (default: true)
- **LLM_ENABLE_THINKING**: Enable thinking mode in chat templates (default: false)

### API Configuration (when using FastAPI)
- **API_HOST**: API server host (default: 0.0.0.0)
- **API_PORT**: API server port (default: 18081)
- **API_WORKERS**: Number of worker processes

### Performance Tuning
- **OMP_NUM_THREADS**: OpenMP thread count for CPU processing
- **CUDA_VISIBLE_DEVICES**: GPU device selection
- **LLM_CACHE_SIZE**: Maximum size of LLM response cache
- **LLM_BATCH_SIZE**: Batch size for LLM processing
- **LLM_TIMEOUT**: Request timeout for LLM API calls
- **CACHE_TTL**: Time-to-live for cached responses (seconds)
- **MAX_CONCURRENT_REQUESTS**: Maximum parallel API requests
- **RESOURCE_POOL_SIZE**: Size of resource connection pool

## Port Configuration
- **API Server**: 18081 (default FastAPI port)
- **Development Server**: 18082 (for development/testing)

## Dependencies Management

### Core Dependencies (Always Required)
- transformers: Model loading and inference
- torch: Neural network operations
- scipy: Similarity calculations
- json-repair: Data cleaning

### Optional Dependencies
- fastapi + uvicorn: Only for API mode
- CUDA toolkit: Only for GPU acceleration

## Performance Considerations

### CPU Mode (Default)
- Memory: ~2GB for model loading
- Processing: Single-threaded by default
- Suitable for: Small to medium datasets

### GPU Mode
- Memory: ~4GB GPU memory required
- Processing: Parallelized batch processing
- Suitable for: Large datasets, real-time processing

## Logging & Monitoring

### Log Structure
- **Location**: `/tmp/json_compare/logs/`
- **Rotation**: 10MB max size with automatic rotation
- **Format**: Structured JSON for easy parsing

### Log Types
1. **access.log**: HTTP request logging
   - Request ID, method, path, status
   - Client IP, processing time

2. **error.log**: Error tracking
   - Unique error IDs
   - Stack traces
   - Recovery suggestions

3. **metrics.log**: Performance metrics
   - Upload success/failure rates
   - Average processing times
   - System resource usage (CPU/Memory/Disk)

## Security Considerations
- External API calls: Model download (first run) and vLLM API (when LLM mode enabled)
- Local processing of embedding-based comparisons
- No data persistence unless explicitly saved
- Sandboxed execution via uvx
- File size limits: 100MB default for uploads
- Request validation with pydantic
- API key management for vLLM service (environment variable)
- LLM response caching to minimize external API calls
- Comparison method metadata for transparency and auditability
- Configuration validation to prevent injection attacks
- Secure prompt template handling with YAML safe loading
- Resource limit enforcement to prevent DoS attacks
- Comprehensive error handling without information leakage
- Test environment isolation with MCP wrapper security