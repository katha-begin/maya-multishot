# Maya Multi-Shot Context Variables Pipeline

A Maya pipeline tool for managing context-aware file paths across multiple shots within a single scene.

## Features

- **Multi-shot support**: Work on multiple shots in one Maya scene
- **Token-based paths**: Template paths with automatic resolution (`$ep`, `$seq`, `$shot`, `$ver`, etc.)
- **Display layer management**: Shot-specific visibility control
- **Cross-platform**: Windows and Linux support with path mapping
- **Version management**: Independent asset versions per shot
- **Hierarchical data model**: CTX_Manager → CTX_Shot → CTX_Asset custom nodes
- **Light Gaffer System**: Hierarchical light management with inheritance-based overrides (NEW!)

## Quick Start

See [Getting Started Guide](spec/GETTING_STARTED.md) for setup instructions.

## Documentation

### Core System
- **[Technical Specification](spec/spec.md)** - Complete technical design
- **[Implementation Tasks](spec/tasks.md)** - Detailed task list with 92 tasks
- **[Architecture Summary](spec/ARCHITECTURE_SUMMARY.md)** - Repository structure and architecture

### Light Gaffer System
- **[Gaffer System Overview](docs/gaffer_system_overview.md)** - Introduction and key concepts
- **[Gaffer API Reference](docs/gaffer_api_reference.md)** - Complete API documentation
- **[Gaffer UI Guide](docs/gaffer_ui_guide.md)** - User interface guide
- **[Gaffer Workflows](docs/gaffer_workflows.md)** - Common workflows and examples
- **[Gaffer Specification](spec/CTX_lightGaffer_spec.md)** - Technical specification
- **[Gaffer UI Specification](spec/CTX_gaffer_UI.md)** - UI design specification

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

### Shot Manager

```python
# In Maya Script Editor
import sys
sys.path.append('E:/dev/maya-multishot')  # Adjust path

from tools import shot_manager
shot_manager.show()
```

### Light Gaffer System

```python
# Open Gaffer Manager
from ui.gaffer_manager_dialog import GafferManagerDialog

dialog = GafferManagerDialog()
dialog.show()

# Or from Main Window: Tools → Gaffer Manager
```

See [Gaffer System Overview](docs/gaffer_system_overview.md) for complete usage guide.

## License

[Add license information]

## Repository

https://github.com/katha-begin/maya-multishot.git

## Status

**Current Phase:** Phase 0 - Repository Setup
**Next Phase:** Phase 1 - Core Architecture
**Total Tasks:** 92 (5 setup + 87 implementation)
**Estimated Timeline:** 12-16 weeks

### Light Gaffer System Status

**Status:** ✅ Production Ready (Phase 4 Complete)
**Branch:** `feature/gaffer-system`
**Lines of Code:** 4,229 (2,676 core + 1,553 UI)
**Tests:** 63 passing
**Documentation:** Complete

**Completed Phases:**
- ✅ Phase 1: Core Schemas and Wrappers
- ✅ Phase 2: Gaffer Manager and Attribute Resolver
- ✅ Phase 3: Light Operations and Chain Management
- ✅ Phase 4: UI Implementation (Gaffer Manager, Light Editor, Add Light Dialog)
- ✅ Phase 5: Documentation Updates

**Next:** Phase 6 - Testing & Integration

