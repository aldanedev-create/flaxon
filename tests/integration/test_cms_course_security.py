import asyncio
import secrets

import pytest
from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.admin.cms import CMS, CMSField, ContentType
from flaxon.testing import TestClient


def setup_editor():
    password = secrets.token_urlsafe(20) + 'Aa1!'
    app = Flaxon('cms-security', debug=True)
    admin = AdminDashboard(app, strict_permissions=True, users=[{
        'username': 'editor', 'password': password, 'roles': [],
        'permissions': ['article.view_article', 'article.add_article', 'article.change_article', 'cms.restore_revision'],
    }])
    cms = CMS(app, auth=admin.auth)
    content = cms.register(ContentType('article', fields=[CMSField('title', required=True)]))
    token = asyncio.run(admin.auth.login('editor', password))
    headers = {'cookie': f'session_id={token}', 'x-csrf-token': admin.csrf_token()}
    return TestClient(app), cms, content, headers


def test_standalone_cms_denies_anonymous_requests_by_default():
    app = Flaxon('closed-cms')
    cms = CMS(app)
    cms.register(ContentType('article', fields=[CMSField('title')]))
    client = TestClient(app)
    assert client.get('/admin/cms/api/article/items').status_code == 403
    assert client.post('/admin/cms/api/article/items', json_data={'title': 'Anonymous'}).status_code == 403


@pytest.mark.parametrize('status', ['approved', 'scheduled', 'published'])
@pytest.mark.parametrize('method', ['create', 'update', 'import'])
def test_editor_cannot_publish_through_generic_write_paths(status, method):
    client, cms, content, headers = setup_editor()
    data = {'title': 'Blocked', 'status': status}
    if method == 'create':
        response = client.post('/admin/cms/api/article/items', json_data=data, headers=headers)
    elif method == 'update':
        item = content.create({'title': 'Draft'})
        response = client.put(f"/admin/cms/api/article/items/{item['id']}", json_data=data, headers=headers)
        assert item['status'] == 'draft'
    else:
        response = client.post('/admin/cms/api/import/article', json_data=[data], headers=headers)
    assert response.status_code == 403
    assert not any(item['status'] == status for item in content.items.values())


def test_editor_cannot_restore_published_revision_or_edit_published_content():
    client, cms, content, headers = setup_editor()
    item = content.create({'title': 'Published', 'status': 'published'})
    assert client.put(f"/admin/cms/api/article/items/{item['id']}", json_data={'title': 'Changed'}, headers=headers).status_code == 403
    content.update(item['id'], {'status': 'draft'})
    assert client.post(f"/admin/cms/api/article/items/{item['id']}/restore/0", headers=headers).status_code == 403
    assert item['status'] == 'draft'


def test_draft_editing_and_publisher_creation_work_with_csrf():
    client, cms, content, headers = setup_editor()
    assert client.post('/admin/cms/api/article/items', json_data={'title': 'Draft'}, headers=headers).status_code == 201
    cms.auth.users['editor']['permissions'].append('cms.publish_content')
    assert client.post('/admin/cms/api/article/items', json_data={'title': 'Published', 'status': 'published'}, headers=headers).status_code == 201
    assert client.post('/admin/cms/api/article/items', json_data={'title': 'No CSRF'}, headers={'cookie': headers['cookie']}).status_code == 400


def test_import_authorization_is_checked_before_any_row_is_created():
    client, cms, content, headers = setup_editor()
    response = client.post('/admin/cms/api/import/article', json_data=[
        {'title': 'Draft'}, {'title': 'Forbidden', 'status': 'published'},
    ], headers=headers)
    assert response.status_code == 403
    assert content.items == {}


@pytest.mark.parametrize('action', ['publish', 'unpublish', 'custom'])
def test_actions_require_publisher_permission(action):
    client, cms, content, headers = setup_editor()
    item = content.create({'title': 'Draft'})
    content.register_action('custom', 'Custom', lambda content_type, ids: None)
    response = client.post(f'/admin/cms/api/article/actions/{action}', json_data={'ids': [item['id']]}, headers=headers)
    assert response.status_code == 403
