FROM python:3.13-slim AS builder

WORKDIR /build
COPY . .
RUN pip install --no-cache-dir build && python -m build

FROM python:3.13-slim

LABEL org.opencontainers.image.title="driftscope"
LABEL org.opencontainers.image.description="Longitudinal AI code contribution quality monitor"

RUN useradd --create-home driftscope
USER driftscope

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

ENTRYPOINT ["driftscope"]
