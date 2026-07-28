# Releasing (PyPI)

MathHead is **ready** to be published to PyPI. The upload step requires your PyPI
account (which is why it wasn't automated — credentials aren't shared).

## 1) Build

```bash
pip install build twine
python -m build          # produces dist/mathhead-<version>.whl and .tar.gz
twine check dist/*       # PyPI metadata validation
```

## 2) (Recommended) TestPyPI first

```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ mathhead
```

## 3) Real PyPI

```bash
twine upload dist/*
```

After that, anyone can:

```bash
pip install mathhead
mathhead entail -p "p" -p "implies(p, q)" -c "q"
```

## Version bump

Bump the version in `pyproject.toml` and `src/mathhead/__init__.py`,
add an entry to `CHANGELOG.md`, and tag it: `git tag v0.1.0 && git push --tags`.
