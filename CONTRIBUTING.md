# Contributing to Clippy AI Agent

Thank you for your interest in contributing to Clippy! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Issues
1. **Search existing issues** first to avoid duplicates
2. **Use issue templates** when available
3. **Provide detailed information**:
   - Operating system and version
   - Python version
   - Error messages and stack traces
   - Steps to reproduce the issue
   - Expected vs actual behavior

### Suggesting Features
1. **Check the roadmap** in the README first
2. **Open a feature request issue**
3. **Describe the use case** and expected benefit
4. **Consider implementation complexity**

### Code Contributions

#### Development Setup
```bash
# 1. Fork and clone the repository
git clone https://github.com/yourusername/clippy-ai-agent.git
cd clippy-ai-agent

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 3. Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Install pre-commit hooks
pre-commit install
```

#### Making Changes
1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow coding standards**:
   - Use Python 3.8+ features appropriately
   - Follow PEP 8 style guidelines
   - Add type hints where possible
   - Write docstrings for functions and classes

3. **Write tests** for new functionality:
   ```bash
   # Run tests
   pytest tests/
   
   # Run with coverage
   pytest --cov=src tests/
   ```

4. **Update documentation** if needed:
   - Update README.md for user-facing changes
   - Add docstrings for new functions/classes
   - Update configuration examples

#### Code Style
- **Formatting**: Use `black` for code formatting
- **Linting**: Use `flake8` for linting
- **Type checking**: Use `mypy` for type checking
- **Imports**: Use `isort` for import sorting

```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/
```

#### Commit Messages
Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(platforms): add support for YouTube Community posts
fix(video): resolve FFmpeg audio encoding issue
docs(readme): update installation instructions
```

### Pull Request Process

1. **Update your branch** with the latest main:
   ```bash
   git checkout main
   git pull origin main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Ensure all checks pass**:
   - All tests pass
   - Code coverage is maintained
   - Linting passes
   - Documentation is updated

3. **Create a pull request**:
   - Use a descriptive title
   - Reference related issues
   - Provide a detailed description
   - Include screenshots/videos for UI changes

4. **Respond to feedback**:
   - Address review comments promptly
   - Update tests if requested
   - Rebase and force-push if needed

## 🏗️ Project Structure

```
clippy/
├── src/                    # Main source code
│   ├── core/              # Core processing modules
│   ├── ai/                # AI and ML components
│   ├── platforms/         # Platform integrations
│   └── utils/             # Utilities and helpers
├── tests/                 # Test files
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── examples/              # Example configurations
```

## 🧪 Testing Guidelines

### Test Categories
1. **Unit tests**: Test individual functions/classes
2. **Integration tests**: Test component interactions
3. **End-to-end tests**: Test complete workflows
4. **Platform tests**: Test platform integrations (with mocks)

### Writing Tests
```python
import pytest
from unittest.mock import Mock, patch
from src.core.video_processor import VideoProcessor

class TestVideoProcessor:
    def setup_method(self):
        self.processor = VideoProcessor(config={})
    
    def test_extract_audio_success(self):
        # Test implementation
        pass
    
    @patch('src.core.video_processor.ffmpeg')
    def test_extract_audio_error(self, mock_ffmpeg):
        # Test error handling
        pass
```

### Test Coverage
- Maintain at least 80% code coverage
- Focus on critical paths and error handling
- Mock external dependencies (APIs, file systems)

## 📋 Platform-Specific Guidelines

### Adding New Platforms
1. **Create platform module** in `src/platforms/`
2. **Implement base interface**:
   ```python
   from abc import ABC, abstractmethod
   
   class PlatformBase(ABC):
       @abstractmethod
       async def post_video(self, video_path: str, metadata: dict) -> dict:
           pass
       
       @abstractmethod
       async def get_analytics(self, post_id: str) -> dict:
           pass
   ```

3. **Add configuration schema**
4. **Write comprehensive tests**
5. **Update documentation**

### Platform Testing
- Use mock responses for API calls
- Test rate limiting and error handling
- Validate metadata formats
- Test authentication flows

## 🐛 Debugging Guidelines

### Logging
- Use structured logging with context
- Include relevant metadata in log messages
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)

### Error Handling
- Catch specific exceptions
- Provide meaningful error messages
- Include recovery suggestions
- Log stack traces for debugging

## 📖 Documentation

### Code Documentation
- Write clear docstrings for all public functions
- Include parameter and return type information
- Provide usage examples where helpful

### User Documentation
- Update README.md for user-facing changes
- Include configuration examples
- Provide troubleshooting information

## 🎯 Focus Areas

We're particularly interested in contributions for:

1. **New Platform Support**: TikTok improvements, LinkedIn, Twitter
2. **AI Enhancements**: Better viral moment detection, content optimization
3. **Performance**: Faster processing, memory optimization
4. **User Experience**: Better CLI, web interface, configuration validation
5. **Testing**: Increase coverage, integration tests, platform mocks

## ❓ Questions?

- **General questions**: Open a discussion
- **Bug reports**: Open an issue
- **Feature requests**: Open an issue with the feature template
- **Security issues**: Email security@clippy-agent.com

## 📄 Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

1. **Be respectful** and inclusive
2. **Be collaborative** and constructive
3. **Focus on the project** and technical merits
4. **Help others learn** and grow

We're committed to providing a welcoming and harassment-free experience for everyone.

## 🙏 Recognition

All contributors will be recognized in our CONTRIBUTORS.md file. Significant contributions may also be highlighted in release notes.

Thank you for helping make Clippy better! 🚀
