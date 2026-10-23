import logging
from types import SimpleNamespace

import pytest

from repositories.services import GitRepositoryService, RepositoryPermission


@pytest.mark.parametrize(
    ('authenticated', 'superuser', 'allowed'),
    [(False, False, False), (True, False, False), (True, True, True)],
)
def test_list_permission_diagnostics(
    authenticated: bool,
    superuser: bool,
    allowed: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = GitRepositoryService()
    service.action = 'List'
    service.context = SimpleNamespace(
        user=SimpleNamespace(
            is_authenticated=authenticated, is_superuser=superuser
        )
    )

    with caplog.at_level(logging.INFO, logger='repositories.services'):
        assert RepositoryPermission().has_permission(service.context, service) is allowed

    assert 'controller=GitRepositoryController action=List' in caplog.text
    assert 'permission=repositories.services.RepositoryPermission' in caplog.text
    assert f'is_authenticated={authenticated}' in caplog.text
    assert f'is_superuser={superuser}' in caplog.text
    assert f'allowed={allowed}' in caplog.text


def test_list_permission_diagnostics_for_missing_user(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = GitRepositoryService()
    service.action = 'List'
    service.context = SimpleNamespace(user=None)

    assert not RepositoryPermission().has_permission(service.context, service)
    assert 'is_authenticated=False is_superuser=False allowed=False' in caplog.text
