# Maya Multi-Shot Context Variables Pipeline

A Maya pipeline tool for managing context-aware file paths across multiple shots within a single scene.

## Features

- **Multi-shot support**: Work on multiple shots in one Maya scene
- **Token-based paths**: Template paths with automatic resolution (`$ep`, `$seq`, `$shot`, `$ver`, etc.)
- **Display layer management**: Shot-specific visibility control
- **Cross-platform**: Windows and Linux support with path mapping
- **Version management**: Independent asset versions per shot
- **Hierarchical data model**: CTX_Manager → CTX_Shot → CTX_Asset custom nodes

## Quick Start

See [Getting Started Guide](spec/GETTING_STARTED.md) for setup instructions.

## Documentation

- **[Technical Specification](spec/spec.md)** - Complete technical design
- **[Implementation Tasks](spec/tasks.md)** - Detailed task list with 92 tasks
- **[Getting Started](spec/GETTING_STARTED.md)** - Quick start guide
- **[POC Analysis](spec/POC_vs_SPEC_alignment_report.md)** - POC vs Spec comparison

## Repository Structure

```
maya-multishot/
├── config/          # Configuration module
├── core/            # Core functionality (context, tokens, resolver)
├── tools/           # User-facing tools (shot manager, asset manager)
├── ui/              # User interface (Qt-based)
├── farm/            # Render farm integration
├── tests/           # Test suite
├── docs/            # Documentation
├── examples/        # Example configurations
└── spec/            # Specification documents
```

See [spec/spec.md Section 0.2](spec/spec.md#02-initial-repository-structure) for complete structure.

## Development

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - Feature branches

### Workflow

```bash
git checkout develop
git pull origin develop
git checkout -b feature/P1-module-01-description
# ... implement task ...
git commit -m "[P1-MODULE-01] Task description"
git push -u origin feature/P1-module-01-description
# ... create PR on GitHub ...
```

See [spec/spec.md Section 0.4](spec/spec.md#04-branch-strategy) for complete workflow.

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=. --cov-report=html tests/
```

## Installation

```bash
# Clone repository
git clone https://github.com/katha-begin/maya-multishot.git
cd maya-multishot

# Install dependencies
pip install -r requirements.txt
```

## Usage

```python
# In Maya Script Editor
import sys
sys.path.append('E:/dev/maya-multishot')  # Adjust path

from tools import shot_manager
shot_manager.show()
```

## License

[Add license information]

## Repository

https://github.com/katha-begin/maya-multishot.git

## Status

**Current Phase:** Phase 0 - Repository Setup  
**Next Phase:** Phase 1 - Core Architecture  
**Total Tasks:** 92 (5 setup + 87 implementation)  
**Estimated Timeline:** 12-16 weeks

