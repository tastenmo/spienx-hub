from pathlib import Path

import pytest


@pytest.mark.parametrize('app', ['accounts', 'documents', 'repositories'])
def test_proto_generation_path_uses_shared_definition(app: str) -> None:
    root = Path(__file__).resolve().parents[2]
    generation_path = root / 'src' / app / 'grpc' / f'{app}.proto'
    shared_path = root / 'spienx-proto' / app / 'grpc' / f'{app}.proto'

    assert generation_path.is_symlink()
    assert shared_path.is_file()
    assert generation_path.resolve() == shared_path
    assert generation_path.read_bytes() == shared_path.read_bytes()
