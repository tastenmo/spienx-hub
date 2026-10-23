from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django_socio_grpc.request_transformer.socio_internal_request import RequestMeta

from core.authentication import GrpcSessionAuthentication


@pytest.mark.django_db
def test_grpc_metadata_cookie_authenticates_superuser() -> None:
    user = User.objects.create_superuser(username='grpc-admin', password='test-password')
    client = Client()
    client.force_login(user)
    request = SimpleNamespace(
        user=None,
        META=RequestMeta(
            {'cookie': f'sessionid={client.cookies["sessionid"].value}'}
        ),
    )

    result = GrpcSessionAuthentication().authenticate(request)

    assert result is not None
    assert result[0].pk == user.pk
    assert request.user.is_authenticated
    assert request.user.is_superuser


@pytest.mark.parametrize(
    ('cookie', 'reason'),
    [
        ('', 'missing_cookie_header'),
        ('csrftoken=test', 'missing_session_cookie'),
    ],
)
def test_missing_grpc_session_diagnostic(
    cookie: str, reason: str, caplog: pytest.LogCaptureFixture
) -> None:
    request = SimpleNamespace(user=None, META=RequestMeta({'cookie': cookie}))

    assert GrpcSessionAuthentication().authenticate(request) is None
    assert f'reason={reason}' in caplog.text
    assert 'csrftoken=test' not in caplog.text
