# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only

from collections.abc import Mapping

from rest_framework import serializers

from plane.api.serializers.base import BaseSerializer
from plane.db.models import Page
from plane.utils.content_validator import validate_html_content


class PageAPISerializer(BaseSerializer):
    name = serializers.CharField(max_length=255)
    description_html = serializers.CharField(allow_blank=True, trim_whitespace=False)
    expected_updated_at = serializers.DateTimeField(required=False, write_only=True)
    parent_id = serializers.UUIDField(read_only=True, allow_null=True)
    writable_fields = {
        "name",
        "description_html",
        "access",
        "color",
        "view_props",
        "logo_props",
        "external_id",
        "external_source",
        "is_locked",
        "expected_updated_at",
    }

    class Meta:
        model = Page
        fields = [
            "id",
            "name",
            "description_html",
            "access",
            "color",
            "view_props",
            "logo_props",
            "external_id",
            "external_source",
            "is_locked",
            "archived_at",
            "parent_id",
            "workspace",
            "owned_by",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "expected_updated_at",
        ]
        read_only_fields = [
            "id",
            "archived_at",
            "workspace",
            "owned_by",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)
        unknown = set(data) - self.writable_fields
        if unknown:
            raise serializers.ValidationError({key: "This field is not writable." for key in sorted(unknown)})
        return super().to_internal_value(data)

    def validate_description_html(self, value):
        valid, error, sanitized = validate_html_content(value)
        if not valid:
            raise serializers.ValidationError(error)
        return sanitized if sanitized is not None else value

    def validate_view_props(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Expected a JSON object.")
        return value

    def validate_logo_props(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Expected a JSON object.")
        return value


class PageListAPISerializer(PageAPISerializer):
    class Meta(PageAPISerializer.Meta):
        fields = [field for field in PageAPISerializer.Meta.fields if field != "description_html"]
