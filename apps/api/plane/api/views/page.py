# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response

from plane.api.serializers.page import PageAPISerializer, PageListAPISerializer
from plane.api.views.base import BaseAPIView
from plane.app.permissions import ProjectPagePermission, ROLE
from plane.bgtasks.page_transaction_task import page_transaction
from plane.bgtasks.deletion_task import soft_delete_related_objects
from plane.db.models import Page, Project, ProjectMember, ProjectPage, WorkspaceMember, UserFavorite, UserRecentVisit
from plane.utils.page_document_lock import page_document_lock
from plane.utils.openapi import create_paginated_response


class PageConflict(APIException):
    status_code = 409
    default_detail = "The page cannot be changed in its current state."
    default_code = "page_conflict"


class ProjectPageAPIBase(BaseAPIView):
    permission_classes = [ProjectPagePermission]
    serializer_class = PageAPISerializer

    def get_project(self):
        project = get_object_or_404(
            Project, pk=self.kwargs["project_id"], workspace__slug=self.kwargs["slug"], archived_at__isnull=True
        )
        if not WorkspaceMember.objects.filter(
            workspace=project.workspace, member=self.request.user, is_active=True
        ).exists():
            raise PermissionDenied()
        self.project_role = get_object_or_404(
            ProjectMember, project=project, member=self.request.user, is_active=True
        ).role
        return project

    def get_queryset(self):
        project = self.get_project()
        queryset = Page.objects.filter(
            workspace=project.workspace,
            project_pages__project_id=project.id,
            project_pages__deleted_at__isnull=True,
        ).filter(Q(owned_by=self.request.user) | Q(access=Page.PUBLIC_ACCESS))
        if self.project_role == ROLE.GUEST.value and not project.guest_view_all_features:
            queryset = queryset.filter(owned_by=self.request.user)
        return queryset.distinct().order_by("-created_at", "id")

    def get_page(self, for_update=False):
        queryset = self.get_queryset()
        if for_update:
            # Avoid SELECT DISTINCT FOR UPDATE, which PostgreSQL disallows.
            ids = queryset.order_by().values_list("id", flat=True)
            queryset = Page.objects.select_for_update().filter(id__in=ids)
        return get_object_or_404(queryset, pk=self.kwargs["page_id"])

    @staticmethod
    def schedule_content_processing(page_id, new_html, old_html):
        transaction.on_commit(
            lambda: page_transaction.delay(
                page_id=str(page_id), new_description_html=new_html, old_description_html=old_html
            ),
            robust=True,
        )


class PageListCreateAPIEndpoint(ProjectPageAPIBase):
    @extend_schema(
        tags=["Pages"],
        operation_id="list_project_pages",
        responses={200: create_paginated_response(PageListAPISerializer, "PaginatedPageResponse")},
    )
    def get(self, request, slug, project_id):
        queryset = self.get_queryset()
        archived = request.query_params.get("archived", "false").lower()
        if archived not in {"true", "false", "all"}:
            raise ValidationError({"archived": "Use true, false, or all."})
        if archived != "all":
            queryset = queryset.filter(archived_at__isnull=archived == "false")
        if request.query_params.get("search"):
            queryset = queryset.filter(name__icontains=request.query_params["search"])
        return self.paginate(
            request=request,
            queryset=queryset,
            on_results=lambda pages: PageListAPISerializer(pages, many=True, fields=self.fields).data,
        )

    @extend_schema(
        tags=["Pages"],
        operation_id="create_project_page",
        request=PageAPISerializer,
        responses={201: PageAPISerializer},
    )
    def post(self, request, slug, project_id):
        project = self.get_project()
        serializer = PageAPISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if "expected_updated_at" in data:
            raise ValidationError({"expected_updated_at": "Only supported when updating a page."})
        with transaction.atomic():
            # Serialize optional integration IDs without requiring a schema migration.
            Project.objects.select_for_update().get(pk=project.id)
            if data.get("external_id") and data.get("external_source"):
                duplicate = Page.objects.filter(
                    workspace=project.workspace,
                    project_pages__project=project,
                    project_pages__deleted_at__isnull=True,
                    external_id=data["external_id"],
                    external_source=data["external_source"],
                ).exists()
                if duplicate:
                    raise PageConflict("A page with this external_id and external_source already exists.")
            page = Page(
                **data,
                workspace=project.workspace,
                owned_by=request.user,
                created_by=request.user,
                updated_by=request.user,
            )
            page.save(disable_auto_set_user=True)
            link = ProjectPage(
                project=project,
                page=page,
                workspace=project.workspace,
                created_by=request.user,
                updated_by=request.user,
            )
            link.save(disable_auto_set_user=True)
            self.schedule_content_processing(page.id, page.description_html, None)
        return Response(PageAPISerializer(page).data, status=status.HTTP_201_CREATED)


class PageDetailAPIEndpoint(ProjectPageAPIBase):
    @extend_schema(tags=["Pages"], operation_id="retrieve_project_page", responses=PageAPISerializer)
    def get(self, request, slug, project_id, page_id):
        return Response(PageAPISerializer(self.get_page(), fields=self.fields).data)

    @extend_schema(
        tags=["Pages"], operation_id="update_project_page", request=PageAPISerializer, responses=PageAPISerializer
    )
    def patch(self, request, slug, project_id, page_id):
        self.get_project()
        serializer = PageAPISerializer(self.get_page(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected = data.pop("expected_updated_at", None)
        # Only content replacement needs an idle editor. Metadata edits remain usable
        # while a page is open. Body replacements discard stale derived Yjs state.
        with page_document_lock(page_id, require_idle="description_html" in data), transaction.atomic():
            page = self.get_page(for_update=True)
            if expected is not None and page.updated_at != expected:
                raise PageConflict("Page changed since expected_updated_at; fetch it again before retrying.")
            if page.archived_at is not None:
                raise PageConflict("Restore this archived page before updating it.")
            owner_only = {"access", "is_locked"} & data.keys()
            if owner_only and page.owned_by_id != request.user.id:
                raise PermissionDenied("Only the page owner can change access or locking.")
            if page.is_locked and not (data == {"is_locked": False} and page.owned_by_id == request.user.id):
                raise PageConflict("Unlock this page before updating it.")
            old_html = page.description_html
            for field, value in data.items():
                setattr(page, field, value)
            if "description_html" in data:
                page.description_binary = None
                page.description_json = {}
            page.updated_by = request.user
            page.save(disable_auto_set_user=True)
            if "description_html" in data:
                self.schedule_content_processing(page.id, page.description_html, old_html)
        return Response(PageAPISerializer(page).data)

    @extend_schema(tags=["Pages"], operation_id="delete_project_page", responses={204: None})
    def delete(self, request, slug, project_id, page_id):
        with page_document_lock(page_id, require_idle=True), transaction.atomic():
            page = self.get_page(for_update=True)
            if page.is_locked or page.archived_at is None:
                raise PageConflict("The page must be unlocked and archived before deletion.")
            links = ProjectPage.objects.filter(page=page)
            if links.count() == 1 and Page.objects.filter(parent=page).exists():
                raise PageConflict("Remove child pages before deleting their parent.")
            links.filter(project_id=project_id).delete()
            if not ProjectPage.objects.filter(page=page).exists():
                Page.objects.filter(pk=page.pk).update(
                    deleted_at=timezone.now(), updated_at=timezone.now(), updated_by=request.user
                )
                transaction.on_commit(lambda: soft_delete_related_objects.delay("db", "page", page.pk), robust=True)
            UserFavorite.objects.filter(
                workspace__slug=slug, project_id=project_id, entity_type="page", entity_identifier=page_id
            ).delete()
            UserRecentVisit.objects.filter(
                workspace__slug=slug, project_id=project_id, entity_name="page", entity_identifier=page_id
            ).delete(soft=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PageArchiveAPIEndpoint(ProjectPageAPIBase):
    @extend_schema(tags=["Pages"], operation_id="archive_project_page", request=None, responses=PageAPISerializer)
    def post(self, request, slug, project_id, page_id):
        return self.change_archive(request, page_id, timezone.localdate())

    @extend_schema(tags=["Pages"], operation_id="restore_project_page", responses=PageAPISerializer)
    def delete(self, request, slug, project_id, page_id):
        return self.change_archive(request, page_id, None)

    def change_archive(self, request, page_id, archived_at):
        with page_document_lock(page_id, require_idle=True), transaction.atomic():
            page = self.get_page(for_update=True)
            if page.is_locked:
                raise PageConflict("Unlock this page before archiving or restoring it.")
            if Page.objects.filter(parent=page).exists():
                raise PageConflict("Archive or restore nested pages using the web UI.")
            page.archived_at = archived_at
            page.updated_by = request.user
            page.save(disable_auto_set_user=True)
        return Response(PageAPISerializer(page).data)
