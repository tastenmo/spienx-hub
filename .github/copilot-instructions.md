# Project-Specific Instructions (Python & Poetry)

You are an expert Python developer. Adhere strictly to the following project rules:

## 1. Dependency Management & Tooling
- **Poetry is Mandatory:** This project uses `Poetry` exclusively. Never suggest `pip`, `venv`, or `conda`.
- **Command Prefix:** Always use the `poetry run` prefix for execution (e.g., `poetry run python main.py`, `poetry run pytest`).
- **Adding Dependencies:** Use `poetry add <package>` for new dependencies. Do not suggest manual edits to `pyproject.toml` unless requested.
- **Environment:** Always assume the environment is managed via `poetry shell`.

## 2. Code Execution & Scope
- **Minimal Intervention:** Modify ONLY the code necessary to solve the specific task. Avoid unsolicited large-scale refactorings or changing unrelated logic. Try to keep code simple, efficient, and maintainable.
- **Type Safety:** Use strict Python type hints for all function signatures.
- **Documentation:** Don't add docstrings or comments unless explicitly requested.

## 3. Testing Standards
- **Local Execution:** Run unit tests ONLY in the local Poetry environment, NOT inside Docker.
- **Framework:** Use `pytest` for all tests.
- **Execution:** Suggest running tests via `poetry run pytest`.
- **Structure:** Follow existing patterns in the `tests/` directory.

## 4. API usage
- **API architecture:** use **gRPC only** for inter-service communication. Do not suggest REST or HTTP-based solutions.
- **Tools:** Exclusively use 'django-socio-grpc' for gRPC integration and use the commands provided by this package for generating proto files and stubs.

## 5. Constraint Awareness
- Before generating code or suggesting commands, check `pyproject.toml` to verify installed versions and Python constraints.
- If you are unsure about the local environment setup, ask for clarification instead of defaulting to standard Python workflows.