# The exact official backend used by the existing v1.4.2 deployment.
FROM makeplane/plane-backend@sha256:90032ce088708889b60c00d491897916f4deb882facda27db59fd10fb68729ef AS runtime
# No dependency or database schema changes. Overlay the version-matched fork.
COPY apps/api/plane /code/plane
COPY deployments/pages-api/README.md /usr/share/doc/plane-pages-api/README.md

FROM runtime AS tests
USER root
RUN pip install --no-cache-dir pytest==9.0.3 pytest-django==4.12.0 pytest-mock==3.11.1 factory-boy==3.3.0 ruff==0.15.6 \
    && mkdir -p /code/plane/static-assets/collected-static
COPY apps/api/pytest.ini /code/pytest.ini
COPY apps/api/pyproject.toml /code/pyproject.toml
WORKDIR /code
CMD ["pytest", "plane/tests/contract/api/test_pages.py", "-q"]
