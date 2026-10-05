# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from redis.exceptions import RedisError

from plane.db.models import Page, Project, ProjectMember, ProjectPage, User
from plane.settings.redis import redis_instance

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


@pytest.fixture
def page_project(workspace, create_user):
    project = Project.objects.create(name="Systems", identifier="SYS", workspace=workspace)
    ProjectMember.objects.get_or_create(project=project, member=create_user, defaults={"role": 20})
    return project


@pytest.fixture
def pages_url(workspace, page_project):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{page_project.id}/pages/"


@pytest.fixture(autouse=True)
def content_task(mocker):
    mocker.patch("plane.middleware.logger.process_logs.delay")
    mocker.patch("plane.db.mixins.soft_delete_related_objects.delay")
    return mocker.patch("plane.api.views.page.page_transaction.delay")


def create_page(client, url, **values):
    response = client.post(url, {"name": "Runbook", "description_html": "<p>Hello</p>", **values}, format="json")
    assert response.status_code == 201, response.data
    return response.data


def test_create_get_list(api_key_client, pages_url, page_project, workspace, create_user):
    data = create_page(api_key_client, pages_url)
    page = Page.objects.get(pk=data["id"])
    assert page.workspace_id == workspace.id
    assert page.owned_by_id == create_user.id
    assert page.created_by_id == create_user.id
    assert ProjectPage.objects.filter(page=page, project=page_project).exists()
    assert api_key_client.get(f"{pages_url}{page.id}/").data["description_html"] == "<p>Hello</p>"
    response = api_key_client.get(pages_url)
    assert response.status_code == 200
    assert str(page.id) in [str(row["id"]) for row in response.data["results"]]
    assert "description_html" not in response.data["results"][0]


@pytest.mark.parametrize(
    "payload",
    [
        {"description_html": "<p>Missing title</p>"},
        {"name": "Missing body"},
        {"name": "", "description_html": ""},
        {"name": "x", "description_html": "", "owned_by": "forged"},
        {"name": "x", "description_html": "", "description_binary": "forged"},
        {"name": "x", "description_html": "", "workspace": "forged"},
        {"name": "x", "description_html": "", "parent_id": "forged"},
        {"name": "x", "description_html": "", "access": 99},
        {"name": "x", "description_html": "", "view_props": []},
        [{"name": "not an object"}],
    ],
)
def test_reject_invalid_payload(api_key_client, pages_url, payload):
    response = api_key_client.post(pages_url, payload, format="json")
    assert response.status_code == 400
    assert not Page.objects.exists()


def test_html_sanitized(api_key_client, pages_url):
    data = create_page(api_key_client, pages_url, description_html='<p onclick="evil()">OK</p><script>evil()</script>')
    assert "script" not in data["description_html"]
    assert "onclick" not in data["description_html"]
    assert "OK" in data["description_html"]


def test_token_required(api_client, pages_url):
    assert api_client.get(pages_url).status_code in (401, 403)
    api_client.credentials(HTTP_X_API_KEY="invalid")
    assert api_client.get(pages_url).status_code in (401, 403)


def test_expired_token(api_key_client, api_token, pages_url):
    api_token.expired_at = timezone.now() - timedelta(days=1)
    api_token.save()
    assert api_key_client.get(pages_url).status_code in (401, 403)


def test_inactive_memberships_denied(api_key_client, pages_url, page_project, workspace, create_user):
    member = ProjectMember.objects.get(project=page_project, member=create_user)
    member.is_active = False
    member.save()
    assert api_key_client.get(pages_url).status_code == 403
    member.is_active = True
    member.save()
    workspace_member = workspace.workspace_member.get(member=create_user)
    workspace_member.is_active = False
    workspace_member.save()
    assert api_key_client.get(pages_url).status_code == 403


def test_project_and_workspace_scope(api_key_client, pages_url, workspace, create_user):
    data = create_page(api_key_client, pages_url)
    other = Project.objects.create(name="Other", identifier="OTHER", workspace=workspace)
    ProjectMember.objects.create(project=other, member=create_user, role=20)
    other_url = f"/api/v1/workspaces/{workspace.slug}/projects/{other.id}/pages/"
    assert api_key_client.get(f"{other_url}{data['id']}/").status_code == 403
    assert api_key_client.get(pages_url.replace(workspace.slug, "wrong-workspace")).status_code == 403
    assert api_key_client.get(other_url).data["results"] == []


def test_private_page_hidden(api_key_client, pages_url, page_project, workspace):
    other_owner = User.objects.create(email="owner@example.com", username="other-owner")
    page = Page.objects.create(name="Private", access=1, workspace=workspace, owned_by=other_owner)
    ProjectPage.objects.create(project=page_project, page=page, workspace=workspace)
    assert api_key_client.get(f"{pages_url}{page.id}/").status_code == 403
    assert api_key_client.get(pages_url).data["results"] == []


def test_guest_visibility_and_create_denied(api_key_client, pages_url, page_project, workspace, create_user):
    other_owner = User.objects.create(email="owner@example.com", username="other-owner")
    page = Page.objects.create(name="Public", workspace=workspace, owned_by=other_owner)
    ProjectPage.objects.create(project=page_project, page=page, workspace=workspace)
    member = ProjectMember.objects.get(project=page_project, member=create_user)
    member.role = 5
    member.save()
    page_project.guest_view_all_features = False
    page_project.save()
    assert api_key_client.get(pages_url).data["results"] == []
    assert api_key_client.get(f"{pages_url}{page.id}/").status_code == 404
    assert api_key_client.post(pages_url, {"name": "No", "description_html": ""}, format="json").status_code == 403


def test_deleted_link_denied(api_key_client, pages_url):
    data = create_page(api_key_client, pages_url)
    ProjectPage.objects.get(page_id=data["id"]).delete()
    assert api_key_client.get(f"{pages_url}{data['id']}/").status_code == 403
    assert api_key_client.get(pages_url).data["results"] == []


def test_atomic_page_and_project_link(api_key_client, pages_url):
    with patch("plane.api.views.page.ProjectPage.save", side_effect=RuntimeError("link failed")):
        response = api_key_client.post(pages_url, {"name": "Fail", "description_html": ""}, format="json")
    assert response.status_code == 500
    assert not Page.objects.exists()


def test_duplicate_external_id(api_key_client, pages_url):
    create_page(api_key_client, pages_url, external_id="runbook-1", external_source="docs")
    response = api_key_client.post(
        pages_url,
        {"name": "Duplicate", "description_html": "", "external_id": "runbook-1", "external_source": "docs"},
        format="json",
    )
    assert response.status_code == 409
    assert Page.objects.count() == 1


def test_patch_body_resets_editor_state(api_key_client, pages_url):
    data = create_page(api_key_client, pages_url)
    Page.objects.filter(id=data["id"]).update(description_binary=b"stale", description_json={"old": True})
    response = api_key_client.patch(
        f"{pages_url}{data['id']}/",
        {"description_html": "<h2>New content</h2>", "expected_updated_at": data["updated_at"]},
        format="json",
    )
    assert response.status_code == 200, response.data
    page = Page.objects.get(id=data["id"])
    assert page.description_binary is None
    assert page.description_json == {}
    assert "New content" in page.description_stripped
    stale = api_key_client.patch(
        f"{pages_url}{data['id']}/",
        {"name": "Stale overwrite", "expected_updated_at": data["updated_at"]},
        format="json",
    )
    assert stale.status_code == 409


def test_busy_editor_rejects_body_update(api_key_client, pages_url):
    data = create_page(api_key_client, pages_url)
    client = redis_instance()
    subscription = client.pubsub()
    subscription.subscribe(f"hocuspocus:{data['id']}")
    subscription.get_message(timeout=2)  # wait for Redis's subscription acknowledgement
    try:
        response = api_key_client.patch(f"{pages_url}{data['id']}/", {"description_html": "<p>No</p>"}, format="json")
        assert response.status_code == 409
        assert api_key_client.patch(f"{pages_url}{data['id']}/", {"name": "Metadata"}, format="json").status_code == 200
        assert Page.objects.get(id=data["id"]).description_html == "<p>Hello</p>"
    finally:
        subscription.close()


def test_redis_failure_fails_closed(api_key_client, pages_url):
    data = create_page(api_key_client, pages_url)
    with patch("plane.utils.page_document_lock.redis_instance", side_effect=RedisError("down")):
        response = api_key_client.patch(f"{pages_url}{data['id']}/", {"description_html": "<p>No</p>"}, format="json")
    assert response.status_code == 503
    assert Page.objects.get(id=data["id"]).description_html == "<p>Hello</p>"


def test_locked_page_and_owner_unlock(api_key_client, pages_url):
    data = create_page(api_key_client, pages_url, is_locked=True)
    url = f"{pages_url}{data['id']}/"
    assert api_key_client.patch(url, {"name": "No"}, format="json").status_code == 409
    assert api_key_client.patch(url, {"is_locked": False}, format="json").status_code == 200
    assert api_key_client.patch(url, {"name": "Yes"}, format="json").status_code == 200


def test_nonowner_cannot_change_access(api_key_client, pages_url, workspace, page_project):
    owner = User.objects.create(email="other@example.com", username="other-owner")
    page = Page.objects.create(name="Public", workspace=workspace, owned_by=owner)
    ProjectPage.objects.create(project=page_project, page=page, workspace=workspace)
    assert api_key_client.patch(f"{pages_url}{page.id}/", {"access": 1}, format="json").status_code == 403


def test_archive_restore_delete(api_key_client, pages_url):
    data = create_page(api_key_client, pages_url)
    url = f"{pages_url}{data['id']}/"
    assert api_key_client.delete(url).status_code == 409
    assert api_key_client.post(url + "archive/").status_code == 200
    assert api_key_client.get(pages_url).data["results"] == []
    assert len(api_key_client.get(pages_url + "?archived=true").data["results"]) == 1
    assert api_key_client.patch(url, {"name": "No"}, format="json").status_code == 409
    assert api_key_client.delete(url + "archive/").status_code == 200
    assert api_key_client.post(url + "archive/").status_code == 200
    assert api_key_client.delete(url).status_code == 204
    assert not Page.objects.filter(id=data["id"]).exists()


def test_delete_detaches_only_requested_project(api_key_client, pages_url, workspace):
    data = create_page(api_key_client, pages_url)
    other = Project.objects.create(name="Other", identifier="OTHER", workspace=workspace)
    ProjectPage.objects.create(project=other, page_id=data["id"], workspace=workspace)
    url = f"{pages_url}{data['id']}/"
    assert api_key_client.post(url + "archive/").status_code == 200
    assert api_key_client.delete(url).status_code == 204
    assert Page.objects.filter(id=data["id"]).exists()
    assert ProjectPage.objects.filter(project=other, page_id=data["id"]).exists()


def test_search_pagination_and_field_selection(api_key_client, pages_url):
    create_page(api_key_client, pages_url, name="First")
    create_page(api_key_client, pages_url, name="Second")
    response = api_key_client.get(pages_url + "?search=Second&per_page=1&fields=id,name")
    assert response.status_code == 200
    assert response.data["results"][0]["name"] == "Second"
    assert set(response.data["results"][0]) == {"id", "name"}
    assert api_key_client.get(pages_url + "?archived=bad").status_code == 400


def test_existing_binary_endpoint_uses_coordination(session_client, api_key_client, pages_url, workspace, page_project):
    data = create_page(api_key_client, pages_url)
    url = f"/api/workspaces/{workspace.slug}/projects/{page_project.id}/pages/{data['id']}/description/"
    response = session_client.get(url)
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b""
    with patch("plane.utils.page_document_lock.redis_instance", side_effect=RedisError("down")):
        assert session_client.get(url).status_code == 503
