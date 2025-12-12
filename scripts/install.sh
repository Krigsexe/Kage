#!/bin/bash
set -e

echo "🚀 Installing KAGE..."

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $required_version or higher required (found $python_version)"
    exit 1
fi

echo "✓ Python $python_version"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "📦 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "🔄 Starting Ollama..."
    ollama serve &
    sleep 5
fi

# Pull default model
echo "📥 Pulling Qwen2.5-Coder model..."
ollama pull qwen2.5-coder:7b-instruct-q4_K_M

# Install KAGE
echo "📦 Installing KAGE..."
pip install -e .

# Create directories
mkdir -p ~/.kage/{memory,chroma,docs_cache}

# Install firejail for sandboxing (optional)
if command -v apt-get &> /dev/null; then
    echo "📦 Installing firejail (optional, requires sudo)..."
    sudo apt-get update && sudo apt-get install -y firejail || echo "⚠️ Could not install firejail"
fi

echo ""
echo "✅ KAGE installed successfully!"
echo ""
echo "Quick start:"
echo "  kage chat          # Start interactive chat"
echo "  kage init          # Initialize in current project"
echo "  kage doctor        # Check system status"
echo ""
