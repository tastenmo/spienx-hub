import pytest
from django.conf import settings
from django.templatetags.static import static
from django.test import AsyncClient
from django.urls import reverse


def test_deployment_urls() -> None:
    prefix = settings.FORCE_SCRIPT_NAME or ''
    assert reverse('admin:index') == f'{prefix}/admin/'
    assert static('admin/css/base.css') == f'{prefix}/static/admin/css/base.css'


@pytest.mark.asyncio
async def test_admin_redirect_preserves_prefix() -> None:
    prefix = settings.FORCE_SCRIPT_NAME or ''
    response = await AsyncClient(root_path=prefix).get('/admin/')
    assert response.status_code == 302
    assert response.url == f'{prefix}/admin/login/?next={prefix}/admin/'
