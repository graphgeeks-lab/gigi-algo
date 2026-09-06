# Releasing

A release is a tag. Everything else is the workflow's job.

## The version lives in one place

`pyproject.toml`. `gigi.__version__` reads it from the installed metadata, and `CITATION.cff` is synced from it by a script. There is no third copy to forget.

## Cutting a release, in five commands

```bash
uv version --bump minor                 # 0.1.0 -> 0.2.0   (or: patch, major, or an explicit 0.2.0)
python scripts/sync-version.py          # CITATION.cff follows pyproject.toml
$EDITOR CHANGELOG.md                    # move [Unreleased] under ## [0.2.0] - YYYY-MM-DD
git commit -am "release: 0.2.0"
git tag v0.2.0 && git push && git push --tags
```

For a pre-release:

```bash
uv version --bump minor --bump alpha    # 0.1.0 -> 0.2.0a1
uv version --bump alpha                 # 0.2.0a1 -> 0.2.0a2
uv version --bump stable                # 0.2.0a2 -> 0.2.0
```

`uv version` refuses a bump that does not increase the version, so you cannot accidentally go backwards. Pre-releases publish to PyPI like anything else; `pip install gigi-algo` will not pick them up without `--pre`, and the GitHub Release is marked as a pre-release automatically.

## Release-day preflight

Run these from the release commit, before creating the tag:

```bash
uv run pytest -q
uv build
docker build -t gigi .
docker run --rm gigi verify
```

The tag workflows repeat these checks in clean GitHub runners. This local pass catches a missing dependency, a wheel that omits registry content, or a container issue while the release is still easy to correct.

## What the workflow then does

[`.github/workflows/release.yml`](../.github/workflows/release.yml) runs on the tag, in four jobs, each of which stops rather than guesses:

| job | it refuses to continue unless |
|---|---|
| **check** | tag, `pyproject.toml` and `CITATION.cff` name the same version; `CHANGELOG.md` has a `## [x.y.z]` section with real notes; the version is **not** already on PyPI; the suite passes with every backend and with NetworkX alone; `gigi verify` passes |
| **build** | the wheel installs clean and `gigi.__version__` reports the tagged version |
| **publish** | trusted publishing succeeds (no token exists anywhere) |
| **release** | PyPI confirms the version is installable — *then* a GitHub Release is created with the changelog section as notes and the published files attached |

The rule underneath all of it: **a Release page must describe something a reader can install.** So the page is created last, after reading PyPI back, never before.

## Before the first release: two things to set up once

1. **Trusted publishing on PyPI.** At <https://pypi.org/manage/account/publishing/>, add a *pending publisher* for project `gigi-algo`, owner `graphgeeks-lab`, repository `gigi-algo`, workflow `release.yml`, environment `pypi`. This is what lets the workflow publish without an API token. The first successful publish claims the project name.
2. **The `pypi` environment on GitHub.** Settings → Environments → new environment named `pypi`. Optional but recommended: add required reviewers, which turns `publish` into a human gate — the workflow checks everything, a person clicks approve, PyPI receives.
3. **The public container package.** The Docker workflow publishes `ghcr.io/graphgeeks-lab/gigi-algo` on the same `v*` tag. After its first successful run, open the package's *Package settings* on GitHub and set its visibility to public. It publishes `:major.minor.patch`, `:major.minor`, and `:latest`; leaving the package private is why an unauthenticated `docker pull` returns `denied`.

## If something goes wrong

- **`check` failed because the version is already on PyPI.** PyPI and the GitHub Release were not changed. The Docker workflow is independent and may
  already have published the image for that tag. Do not retry the same version: bump it, update the citation and changelog,
  then create a new tag.
- **Other `check` failures.** PyPI and the GitHub Release were not changed. Fix the issue, delete the tag
  (`git tag -d v0.2.0 && git push --delete origin v0.2.0`),
  then re-tag. Check the Docker workflow separately because it runs independently.
- **`publish` failed.** Nothing is on PyPI. Same as above.
- **`release` failed after `publish` succeeded.** The version is on PyPI and immutable, but has no Release page. Re-run only the `release` job from the Actions tab; it re-reads PyPI and picks up where it left off. It will not publish twice — `check` would refuse a version that already exists.
- **Wrong notes on a published Release.** Edit the Release by hand on GitHub. The workflow never overwrites an existing Release.

## What `uv version` does not do

It edits `pyproject.toml` and nothing else, on purpose. The changelog entry is the one part of a release a machine should not write for you — it is the sentence that tells a user whether to upgrade.
