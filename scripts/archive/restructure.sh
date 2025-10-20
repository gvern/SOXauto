#!/bin/bash

# Full Project Restructure Script
# Run this after POC validation to reorganize the project

set -e

echo "🔧 Starting full project restructure..."

# Helper function to move files (handles both tracked and untracked)
move_file() {
    if [ -f "$1" ]; then
        echo "  Moving $1 -> $2"
        if git ls-files --error-unmatch "$1" >/dev/null 2>&1; then
            git mv "$1" "$2"
        else
            mv "$1" "$2"
            git add "$2"
        fi
    fi
}

# Create new directory structure
echo "📁 Creating directory structure..."
mkdir -p src/core src/bridges src/agents src/utils
mkdir -p tests/fixtures
mkdir -p scripts/legacy

# Note: docs/ and data/ already exist from quick_wins.sh

# Move core SOX files
echo "📦 Moving core files..."
move_file "main.py" "src/core/"
move_file "config.py" "src/core/"
move_file "ipe_runner.py" "src/core/"
move_file "evidence_manager.py" "src/core/"

# Move bridge analysis
echo "🌉 Moving bridge analysis..."
move_file "timing_difference_analysis.py" "src/bridges/timing_difference.py"

# Move utilities
echo "🔧 Moving utilities..."
move_file "gcp_utils.py" "src/utils/"

# Move scripts
echo "📜 Moving scripts..."
move_file "test_evidence_system.py" "scripts/"

# Move legacy/unclear files
echo "🗄️ Moving legacy files..."
move_file "prompt_v1.py" "scripts/legacy/"

# Create __init__.py files
echo "✨ Creating Python package files..."
touch src/__init__.py
touch src/core/__init__.py
touch src/bridges/__init__.py
touch src/agents/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py

# Add all new files to git
git add src/ tests/

echo "✅ Project restructure complete!"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "1. Update import statements in moved files:"
echo "   - src/core/main.py needs: from src.core.config import ..."
echo "   - src/core/ipe_runner.py needs: from src.utils.gcp_utils import ..."
echo "2. Update timing_difference.py credentials path (already done)"
echo "3. Test that everything still works:"
echo "   - python -m src.core.main"
echo "   - python -m src.bridges.timing_difference"
echo "4. Update Dockerfile COPY commands"
echo "5. Update README.md with new structure"
echo "6. Commit: git commit -m 'refactor: restructure project for scalability'"
echo ""
echo "📚 See PROJECT_STRUCTURE_REVIEW.md for import update examples"
