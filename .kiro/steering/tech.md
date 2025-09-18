# Technology Stack

## Architecture
- **Type**: CLI Tool with optional Web API
- **Pattern**: Command-line interface with modular Python architecture
- **Deployment**: Standalone executable via uvx or local Python environment
- **Processing Model**: Batch processing with optional GPU acceleration

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

### Data Processing
- **json-repair**: 0.1+ (Automatic JSON fixing)
- **protobuf**: 3.20+ (Data serialization)

### Web API (Optional)
- **FastAPI**: 0.100+ (Modern web framework)
- **Uvicorn**: 0.23+ (ASGI server)

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

# Run tests
uv run pytest tests/

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

# Start API server
uvx --from . json_compare_api

# With GPU support
uvx --from . json_compare <input.jsonl> --gpu
```

### Build & Distribution
```bash
# Build package
uv build

# Create distribution
python -m build
```

## Environment Variables

### Model Configuration
- **TRANSFORMERS_CACHE**: Cache directory for downloaded models
- **TORCH_DEVICE**: Force specific device (cpu/cuda)
- **HF_HOME**: Hugging Face home directory

### API Configuration (when using FastAPI)
- **API_HOST**: API server host (default: 0.0.0.0)
- **API_PORT**: API server port (default: 18081)
- **API_WORKERS**: Number of worker processes

### Performance Tuning
- **OMP_NUM_THREADS**: OpenMP thread count for CPU processing
- **CUDA_VISIBLE_DEVICES**: GPU device selection

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

## Security Considerations
- No external API calls except model download (first run only)
- Local processing of all data
- No data persistence unless explicitly saved
- Sandboxed execution via uvx