# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only

import logging
from contextlib import contextmanager
from functools import wraps

from redis.exceptions import RedisError
from rest_framework.exceptions import APIException

from plane.settings.redis import redis_instance

logger = logging.getLogger("plane.api")


class PageDocumentBusy(APIException):
    status_code = 409
    default_detail = "Close this page in all editors, wait a moment, and retry the API update."
    default_code = "page_document_busy"


class PageDocumentUnavailable(APIException):
    status_code = 503
    default_detail = "The page editor coordination service is unavailable; retry later."
    default_code = "page_document_unavailable"


@contextmanager
def page_document_lock(page_id, require_idle=False):
    """Serialize REST replacement with Live's binary reads/writes.

    The companion fork's Live hook subscribes to hocuspocus:<id> before
    loading the database document. Existing subscribers make full-body replacement unsafe.
    A new subscriber arriving after this check cannot read stale state because
    the binary endpoint takes this same lock before fetching its bytes.
    """
    try:
        client = redis_instance()
        client.connection_pool.connection_kwargs.setdefault("socket_timeout", 5)
        client.connection_pool.connection_kwargs.setdefault("socket_connect_timeout", 3)
        lock = client.lock(f"plane:page-api:{page_id}", timeout=60, blocking_timeout=5)
        if not lock.acquire():
            raise PageDocumentBusy()
        try:
            if require_idle and any(count for _, count in client.pubsub_numsub(f"hocuspocus:{page_id}")):
                raise PageDocumentBusy()
            yield
        finally:
            try:
                lock.release()
            except RedisError:
                # Do not report a committed write as failed because cleanup lost
                # its connection. The bounded lease will expire automatically.
                logger.warning("Could not release page document lock; lease will expire.", exc_info=True)
    except RedisError as exc:
        raise PageDocumentUnavailable() from exc


def coordinate_page_document(view_method):
    """Apply the same coordination to the existing Live binary endpoints."""

    @wraps(view_method)
    def wrapped(self, request, slug, project_id, page_id, *args, **kwargs):
        with page_document_lock(page_id):
            return view_method(self, request, slug, project_id, page_id, *args, **kwargs)

    return wrapped
