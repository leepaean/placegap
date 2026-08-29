# Continuous Integration

GitHub Actions runs `pytest -q` on pushes to `main` and on pull requests using Python 3.11.

CI validates code behavior only. Product validity still depends on the blind diagnostic comparison described in `evaluation.md`.
