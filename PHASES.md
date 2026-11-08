# PHASES

## Phase 0 — Scaffold
- [x] `uv init --lib`, Python 3.12, `uv_build`, ruff `ALL`, pytest, branch coverage config
- [x] CLAUDE.md, PHASES.md, README.md, LICENSE
- [x] PyPI name searched: no `pyordering` found (confirm before publishing)

## Phase 1 — Design (written only)
- [x] Design written into README.md instead of `docs/DESIGN.md`: API (`Key`, `Ordering`, `>>`, `~`, `nulls`), JSON shape, error messages, ORM `clauses()` with SQLAlchemy, Django and MySQL render functions, pagination rule
- [x] Author asked to build it (gate for Phase 2)

## Phase 2 — Core
- [x] `Key`, `Ordering`, multi-pass sort, `nulls`, `>>`, `~`, `repr`
- [x] `OrderingRegistry` on `pyvocabulary.Vocabulary`

## Phase 3 — Compiler, schema and ORM clauses
- [x] `OrderingCompiler` with JSON-path errors; JSON Schema
- [x] `Ordering.clauses(subject, render)`; render may return a tuple (MySQL)
- [x] README recipes for SQLAlchemy and Django, tested against both ORMs

## Phase 4 — Release
- [ ] GitHub repository, CI, PyPI
