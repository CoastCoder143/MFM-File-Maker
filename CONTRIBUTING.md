# Contributing to MFM-File-Maker

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. **Install uv** (if not already installed):
   ```bash
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd MFM-File-Maker
   ```

3. **Sync dependencies**:
   ```bash
   uv sync
   ```

## Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** in the `src/` directory

3. **Test your changes**:
   ```bash
   uv run python make_runs.py
   ```

4. **Commit with clear messages**:
   ```bash
   git commit -m "feat: add new feature description"
   ```

## Commit Message Guidelines

Use conventional commit format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `chore:` - Maintenance tasks

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Keep functions focused and testable
- Comment complex logic

## Reporting Issues

When reporting bugs, please include:
- Python version (`python --version`)
- uv version (`uv --version`)
- Steps to reproduce
- Expected vs actual behavior
- Error messages (if any)

## Questions?

Open an issue or discussion on the repository.
