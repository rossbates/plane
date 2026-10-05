# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from plane.license.api.views.instance import InstanceEndpoint
from plane.license.models import Instance

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, False), ("0", False), ("false", False), ("1", True), ("true", True), ("TRUE", True), ("yes", True)],
)
def test_promotional_ui_is_a_public_boolean_preference(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("HIDE_PROMOTIONAL_UI", raising=False)
    else:
        monkeypatch.setenv("HIDE_PROMOTIONAL_UI", value)
    Instance.objects.create(
        instance_name="Test",
        instance_id="test-ui-preference",
        current_version="1.4.2",
        last_checked_at=timezone.now(),
    )
    cache.clear()
    response = InstanceEndpoint.as_view()(APIRequestFactory().get("/api/instances/"))
    assert response.status_code == 200
    assert response.data["config"]["hide_promotional_ui"] is expected
    assert "secret_key" not in response.data["config"]
    assert "live_server_secret_key" not in response.data["config"]
