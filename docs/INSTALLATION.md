# Installation Guide

## Prerequisites

- Python 3.11+
- Ollama
- 8GB+ RAM (12GB+ recommended for 7B models)
- GPU with 6GB+ VRAM (optional but recommended)

## Quick Install (One-liner)

```bash
curl -fsSL https://raw.githubusercontent.com/Krigsexe/Kage/main/scripts/install.sh | bash
```

## Manual Installation

### 1. Install Ollama

**Linux/macOS:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from [ollama.com](https://ollama.com/download)

### 2. Pull the Model

```bash
# Recommended (7B - good quality/speed balance)
ollama pull qwen2.5-coder:7b

# Lightweight (1.5B - faster, less accurate)
ollama pull qwen2.5-coder:1.5b

# High quality (14B - requires more VRAM)
ollama pull qwen2.5-coder:14b
```

### 3. Install KAGE

**From PyPI (when published):**
```bash
pip install kage
```

**From source:**
```bash
git clone https://github.com/Krigsexe/Kage.git
cd Kage
pip install -e .
```

### 4. Verify Installation

```bash
kage doctor
```

Expected output:
```
KAGE System Check

Component          Status           Details
Ollama             [OK] Running     Model 'qwen2.5-coder:7b' available
Memory storage     [OK] Exists      ~/.kage/memory
ChromaDB           [OK] Exists      ~/.kage/chroma
Docs cache         [OK] Exists      ~/.kage/docs_cache
```

## Docker Installation

### Prerequisites
- Docker
- Docker Compose

### Steps

```bash
# Clone repository
git clone https://github.com/Krigsexe/Kage.git
cd Kage

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Wait for Ollama to start, then pull model
docker exec kage-ollama ollama pull qwen2.5-coder:7b

# Start chatting
docker exec -it kage-app kage chat
```

### GPU Support (NVIDIA)

Edit `docker/docker-compose.yml` and uncomment:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## Configuration

### Environment Variables

```bash
# LLM settings
export KAGE_LLM_MODEL="qwen2.5-coder:7b"
export KAGE_LLM_OLLAMA_HOST="http://localhost:11434"
export KAGE_LLM_TEMPERATURE=0.1

# Memory settings
export KAGE_MEMORY_COMPACTION_THRESHOLD=0.8

# Tool settings
export KAGE_TOOL_SANDBOX_ENABLED=true
export KAGE_TOOL_SANDBOX_TYPE=firejail
```

### Project Configuration

Initialize KAGE in your project:
```bash
cd your-project
kage init
```

This creates `.kage/config.json` for project-specific settings.

## Troubleshooting

### Ollama not responding
```bash
# Check if running
curl http://localhost:11434/api/tags

# Restart Ollama
systemctl restart ollama  # Linux
# Or restart the Ollama app on Windows/macOS
```

### Model not found
```bash
# List available models
ollama list

# Pull required model
ollama pull qwen2.5-coder:7b
```

### Permission errors
```bash
# Create directories
mkdir -p ~/.kage/{memory,chroma,docs_cache}
```

## Upgrading

```bash
# From PyPI
pip install --upgrade kage

# From source
cd Kage
git pull
pip install -e .
```
