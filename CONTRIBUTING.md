# Contributing to ASUS Smart Gestures

Thank you for helping improve `asus-smart-gestures`! Contributions for new laptop models, documentation, and code improvements are welcome.

---

## Development Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/IHosseini083/asus-smart-gestures.git
   cd asus-smart-gestures
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install ruff mypy pytest pytest-mock
   ```

3. **Install package in editable mode**:
   ```bash
   pip install -e .
   ```

---

## Code Style & Quality Standards

This project enforces strict typing and modern Python practices:
- **Python 3.10+ syntax**: Use modern union syntax (`X | None`), built-in generic collections (`list[str]`), dataclasses with slots, and enums.
- **Linter & Formatter**: [Ruff](https://astral.sh/ruff)
- **Type Checker**: [Mypy](https://mypy-lang.org/) in strict mode (`--strict`)
- **Test Suite**: [pytest](https://pytest.org/)

### Validation Commands

Before submitting pull requests, ensure all checks pass cleanly:

```bash
# 1. Format code
ruff format .

# 2. Lint and auto-fix
ruff check --fix .

# 3. Type check (strict)
mypy asus_smart_gestures tests

# 4. Run unit tests
pytest
```

---

## Adding Verified Laptop Hardware

If you test this project on a new ASUS laptop model:
1. Run `sudo asus-smart-gestures --scan` to retrieve the device name and hardware ID.
2. Edit `README.md` and append your model to the **Supported & Tested Hardware** table.
3. Submit a Pull Request with your findings!
