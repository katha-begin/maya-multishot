# Getting Started - Maya Multi-Shot Context Variables Pipeline

**Repository:** https://github.com/katha-begin/maya-multishot.git  
**Last Updated:** 2026-02-14

---

## Quick Start Guide

This guide will help you set up the repository and start development.

### Prerequisites

- **Git** installed and configured
- **Maya 2022+** installed
- **Python 2.7** (Maya 2022) or **Python 3.x** (Maya 2023+)
- **GitHub account** with access to the repository
- **Code editor** (VS Code, PyCharm, or similar)

---

## Step 1: Clone Repository (5 minutes)

```bash
# Clone the repository
git clone https://github.com/katha-begin/maya-multishot.git

# Navigate to project directory
cd maya-multishot

# Verify you're on main branch
git branch
```

**Expected Output:**
```
* main
```

---

## Step 2: Create Directory Structure (10 minutes)

```bash
# Create all module directories
mkdir -p config core tools ui farm tests/test_data/{configs,scenes,caches} docs examples

# Create Python package __init__.py files
touch config/__init__.py
touch core/__init__.py
touch tools/__init__.py
touch ui/__init__.py
touch farm/__init__.py
touch tests/__init__.py

# Verify structure
ls -la
```

**Expected Output:**
```
config/
core/
tools/
ui/
farm/
tests/
docs/
examples/
spec/
```

---

## Step 3: Create Essential Files (15 minutes)

### Create .gitignore

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/

# Maya
*.swatches

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
EOF
```

### Create README.md

```bash
cat > README.md << 'EOF'
# Maya Multi-Shot Context Variables Pipeline

A Maya pipeline tool for managing context-aware file paths across multiple shots within a single scene.

## Features

- Multi-shot support in one Maya scene
- Token-based path resolution
- Display layer management
- Cross-platform (Windows/Linux)
- Version management per shot

## Documentation

- [Technical Specification](spec/spec.md)
- [Implementation Tasks](spec/tasks.md)
- [Getting Started](spec/GETTING_STARTED.md)

## Quick Start

See [spec/tasks.md](spec/tasks.md) Phase 0 for setup instructions.

## Repository Structure

See [spec/spec.md Section 0.2](spec/spec.md#02-initial-repository-structure)
EOF
```

### Create requirements.txt

```bash
cat > requirements.txt << 'EOF'
# Testing
pytest>=6.0.0
pytest-cov>=2.10.0

# Documentation
sphinx>=3.0.0
sphinx-rtd-theme>=0.5.0
EOF
```

---

## Step 4: Create Pull Request Template (10 minutes)

```bash
# Create .github directory
mkdir -p .github

# Create PR template (see spec/spec.md Section 0.6 for full content)
# For now, create a basic version:
cat > .github/pull_request_template.md << 'EOF'
## Task Information

**Task ID:** [P#-MODULE-##]
**Task Name:** 
**Phase:** 

## Changes

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Testing
- [ ] All tests pass
- [ ] Code coverage: ___%

## Checklist
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Ready for merge
EOF
```

---

## Step 5: Initial Commit (5 minutes)

```bash
# Stage all files
git add .

# Create initial commit
git commit -m "Initial repository structure

- Add directory structure for all modules
- Add .gitignore for Python and Maya files  
- Add README.md with project overview
- Add requirements.txt for dependencies
- Add .github/pull_request_template.md
- Add spec/ directory with documentation"

# Push to GitHub
git push -u origin main
```

---

## Step 6: Create Develop Branch (2 minutes)

```bash
# Create and switch to develop branch
git checkout -b develop

# Push develop branch
git push -u origin develop

# Verify branches
git branch -a
```

**Expected Output:**
```
* develop
  main
  remotes/origin/develop
  remotes/origin/main
```

---

## Step 7: Verify Development Environment (10 minutes)

### Check Git Configuration

```bash
git config --global user.name
git config --global user.email
```

If not set:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Test Maya Python Environment

Open Maya and run in Script Editor (Python):

```python
import maya.cmds as cmds
print("Maya Version:", cmds.about(version=True))

import sys
print("Python Version:", sys.version)

# Test PySide
try:
    from PySide2 import QtWidgets
    print("PySide2: Available")
except ImportError:
    try:
        from PySide6 import QtWidgets
        print("PySide6: Available")
    except ImportError:
        print("ERROR: No PySide available")
```

**Expected Output:**
```
Maya Version: 2023
Python Version: 3.9.7
PySide2: Available
```

---

## ✅ Phase 0 Complete!

You've successfully completed Phase 0: Repository Setup. Your repository is now ready for development.

### Next Steps

1. **Review Documentation:**
   - Read [spec/spec.md](spec/spec.md) - Technical specification
   - Read [spec/tasks.md](spec/tasks.md) - Implementation tasks
   - Read [spec/POC_vs_SPEC_alignment_report.md](spec/POC_vs_SPEC_alignment_report.md) - POC analysis

2. **Start Phase 1:**
   - Begin with task `[P1-CONFIG-01]` - Project configuration loader
   - Create feature branch: `git checkout -b feature/P1-config-01-project-config-loader`
   - Follow workflow in [spec/spec.md Section 0.4](spec/spec.md#04-branch-strategy)

3. **Development Workflow:**
   ```bash
   # For each task:
   git checkout develop
   git pull origin develop
   git checkout -b feature/P1-module-##-description
   # ... implement task ...
   git add .
   git commit -m "[P1-MODULE-##] Task description"
   git push -u origin feature/P1-module-##-description
   # ... create PR on GitHub ...
   ```

---

## Troubleshooting

### Issue: Permission denied (publickey)

**Solution:** Set up SSH key for GitHub
```bash
ssh-keygen -t ed25519 -C "your.email@example.com"
cat ~/.ssh/id_ed25519.pub
# Add this key to GitHub: Settings → SSH and GPG keys
```

### Issue: Maya can't import modules

**Solution:** Add project to Maya Python path
```python
import sys
sys.path.append('E:/dev/maya-multishot')  # Adjust path
```

### Issue: Git conflicts

**Solution:** Keep develop branch up to date
```bash
git checkout develop
git pull origin develop
git checkout your-feature-branch
git merge develop
# Resolve conflicts
git commit
```

---

## Resources

- **Specification:** [spec/spec.md](spec/spec.md)
- **Task List:** [spec/tasks.md](spec/tasks.md)
- **Repository:** https://github.com/katha-begin/maya-multishot.git
- **POC Reference:** [spec/maya_context_tools_sample.py](spec/maya_context_tools_sample.py)
- **Build System Reference:** [spec/igl_shot_build.py](spec/igl_shot_build.py)

---

**Status:** ✅ Ready to start Phase 1  
**Next Task:** `[P1-CONFIG-01]` - Implement ProjectConfig class

