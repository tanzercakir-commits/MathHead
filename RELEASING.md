# Releasing (PyPI)

The recommended path is **automated, tag-triggered TRUSTED PUBLISHING** (OIDC) — no
long-lived API token stored anywhere. See `.github/workflows/release.yml`.

## One-time setup (maintainer)

1. **On PyPI** (project settings → Publishing): add a *Trusted Publisher* for this repo —
   owner `tanzercakir-commits`, repo `MathHead`, workflow `release.yml`, environment `pypi`.
   (Do the same on TestPyPI first if you want a dry run.)
2. **On GitHub** (Settings → Environments): create an environment named `pypi`
   (optionally require a manual reviewer before publish).
3. **Check the name is free** on PyPI (`mathhead`) before the first publish; the package
   metadata and README are bound to `pip install mathhead`.

## Cut a release

```bash
# 1) Bump the version in pyproject.toml AND src/mathhead/__init__.py (kept in sync by
#    tests/test_release.py), add a CHANGELOG entry, commit.
# 2) Tag and push — the Release workflow builds, validates, smoke-tests, and publishes.
git tag -a vX.Y.Z -m "MathHead vX.Y.Z"
git push origin vX.Y.Z
```

The `Release` workflow (on `v*` tags) builds the wheel + sdist on a clean runner, runs
`twine check`, smoke-tests the built wheel (`mathhead --version`, a CLI entailment), and then
publishes to PyPI via trusted publishing.

## Manual fallback (if you must publish by hand)

```bash
pip install build twine
python -m build          # dist/mathhead-<version>.whl and .tar.gz
twine check dist/*
twine upload --repository testpypi dist/*   # (recommended) TestPyPI first
twine upload dist/*                          # real PyPI
```

After publishing, anyone can:

```bash
pip install mathhead
# exact tested backend set (see ADR-0031):  pip install mathhead -c constraints.txt
mathhead entail -p "p" -p "implies(p, q)" -c "q"
```
