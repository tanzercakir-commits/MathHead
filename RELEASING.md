# Yayınlama (PyPI)

MathHead PyPI'ye yüklenmeye **hazır**. Yükleme adımı senin PyPI hesabını
gerektirir (bu yüzden otomatik yapılmadı — kimlik bilgisi paylaşılmaz).

## 1) Derle

```bash
pip install build twine
python -m build          # dist/mathhead-<sürüm>.whl ve .tar.gz üretir
twine check dist/*       # PyPI metadata doğrulaması
```

## 2) (Önerilir) Önce TestPyPI

```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ mathhead
```

## 3) Gerçek PyPI

```bash
twine upload dist/*
```

Bundan sonra herkes:

```bash
pip install mathhead
mathhead entail -p "p" -p "implies(p, q)" -c "q"
```

## Sürüm yükseltme

`pyproject.toml` ve `src/mathhead/__init__.py` içindeki sürümü artır,
`CHANGELOG.md`'ye giriş ekle, etiketle: `git tag v0.1.0 && git push --tags`.
