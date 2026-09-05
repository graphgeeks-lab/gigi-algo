# Gigi as a container: the registry, every backend, and the agent surface.
#
# Two stages. The builder makes a wheel and the runtime installs it, so the
# final image carries no build tooling, no source tree and no git history --
# only the package and its dependencies.
#
#   docker build -t gigi .
#   docker run --rm gigi verify          # check the registry against reality
#   docker run --rm gigi ask "which nodes matter most"
#   docker run --rm -i gigi              # an MCP server on stdio (the default)
#
# The default command is `mcp` because that is the case a container helps most:
# an agent runtime can start this without Python, uv, or six graph libraries
# installed on the host.
#
#   {"mcpServers": {"gigi": {"command": "docker",
#                            "args": ["run","-i","--rm","gigi","mcp"]}}}
#
# Swap `gigi` for ghcr.io/graphgeeks-lab/gigi-algo once a v* tag has published
# it and the package has been made public.

# --- build ---------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /src

# Only what the build needs. Copying the whole tree would rebuild the wheel on
# any change to docs or tests; .dockerignore keeps those out of the context too.
COPY pyproject.toml README.md ./
COPY gigi/ ./gigi/
COPY methods/ ./methods/
COPY datasets/ ./datasets/
COPY problems/ ./problems/
COPY families/ ./families/
COPY domains/ ./domains/
COPY semantics/ ./semantics/
COPY people/ ./people/

RUN pip install --no-cache-dir hatchling \
    && python -m hatchling build --target wheel

# --- runtime -------------------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="gigi" \
      org.opencontainers.image.description="An executable registry of graph algorithm semantics" \
      org.opencontainers.image.source="https://github.com/graphgeeks-lab/gigi-algo" \
      org.opencontainers.image.licenses="Apache-2.0"

# Unbuffered so MCP responses reach the client immediately rather than sitting
# in a pipe buffer -- a stdio protocol behind a block buffer looks like a hang.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# `[all]` rather than the bare package: an image that cannot run igraph and
# rustworkx cannot run `gigi verify`, and verification is the point. It costs
# size; the alternative costs the reason to have the image at all.
COPY --from=builder /src/dist/*.whl /tmp/
RUN set -eux; \
    pip install --no-cache-dir "$(ls /tmp/*.whl)[all]"; \
    rm -f /tmp/*.whl

# Nothing here needs root, and an agent runtime starting this unattended is
# exactly the case where that matters.
RUN useradd --create-home --uid 10001 gigi
USER gigi
WORKDIR /home/gigi

# A container that starts but cannot read its own registry is the failure worth
# catching, and it is not visible from `gigi --version`.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["gigi", "list"]

# `gigi` as the entrypoint means every subcommand works as an argument:
#   docker run --rm gigi verify
#   docker run --rm gigi ask "..."
# The default is the MCP server. Interactive stdio needs `-i`.
ENTRYPOINT ["gigi"]
CMD ["mcp"]

# A model is optional and none is baked in. To let `gigi ask` use one, pass the
# key through:
#
#   docker run --rm -e ANTHROPIC_API_KEY gigi ask "who are the influencers"
#
# For a local model, Ollama on the host is reachable from the container as:
#
#   docker run --rm -e OLLAMA_HOST=http://host.docker.internal:11434 gigi ask "..."
#
# To run against your own registry instead of the one baked in, mount it and
# point the environment variables at it:
#
#   docker run --rm \
#     -v "$PWD/methods:/registry/methods:ro" \
#     -v "$PWD/datasets:/registry/datasets:ro" \
#     -e GIGI_METHODS_DIR=/registry/methods \
#     -e GIGI_DATASETS_DIR=/registry/datasets \
#     gigi verify
#
# `gigi/paths.py` lists every content directory and the variable that overrides
# it.
