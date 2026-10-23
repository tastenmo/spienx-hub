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

## 5. Proto workflow
- Never hand-edit generated proto or stub files. Use the provided workflow instead.
- Initialize the shared definitions with `git submodule update --init --recursive` before generating protos or building Docker images.
- All `.proto` definitions live in the `spienx-proto/` Git submodule, under `<app>/grpc/<app>.proto`. The paths in `src/<app>/grpc/` are symlinks; preserve them rather than replacing them with copies.
- Generate/refresh protos with `poetry run python manage.py generateproto` from `src/`, or `./manage.sh generateproto` from the repository root. Generation writes through the symlinks into the submodule; Python stubs remain in `src/<app>/grpc/`.
- If a proto change is needed, adjust the service/serializer code, then regenerate; do not edit `.proto`/`_pb2.py`/`_pb2_grpc.py` directly.
- For a new app, create its target directory and initial empty proto file in `spienx-proto/<app>/grpc/`, then create the matching relative symlink in `src/<app>/grpc/` before generation.
- Commit and push proto changes in `spienx-proto` first, then commit the updated submodule pointer together with service/serializer and Python stub changes in this repository.

## 6. Constraint Awareness
- Before generating code or suggesting commands, check `pyproject.toml` to verify installed versions and Python constraints.
- If you are unsure about the local environment setup, ask for clarification instead of defaulting to standard Python workflows.