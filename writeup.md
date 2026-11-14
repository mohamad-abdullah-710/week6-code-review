# Week 6 — AI Code Review & Testing: Habit Tracker

**Student:** Mohamad Abdullah (2409115735)
**Repo:** https://github.com/mohamad-abdullah-710/week6-code-review
**Implementation agent:** Claude Code (Claude Opus 5.5)
**AI reviewer:** CodeRabbit

---

## 1. Guardrails (Part I)

### Setup
| File | Purpose |
|---|---|
| `requirements-dev.txt` | `black==26.10.1`, `ruff==0.17.5` (pinned so local and CI match) |
| `pyproject.toml` | black + ruff settings: line length 88, Python 3.12, ruff rules `E W F I B` (`E501` off because black owns line length) |
| `.github/workflows/ci.yml` | GitHub Actions: on every push and PR runs ruff → black → pytest; any failure fails the run |

### Commands
```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check .        # lint: unused imports, undefined names, import order, bug patterns
black --check .     # formatting: fails if any file is not black-formatted
black .             # auto-format
pytest              # tests
```

### What they caught
- On the untouched starter, `ruff check` passed, but `black --check` flagged `main.py`
  (a missing blank line after the docstring, plus `conn.execute(...)` and two long lines
  wrapped differently). I ran `black .` once and committed it (`6789ffb`).
- First CI run on `master`: **success**
  https://github.com/mohamad-abdullah-710/week6-code-review/actions/runs/43636416723

### Proof that a failing test fails the build
On a throwaway branch `demo-failing-test` I added `assert 2 + 2 == 5` (commit `e4ed330`).
CI result: **failure**. Ruff ✅, black ✅, **pytest ❌**
(`FAILED test_demo_failure.py::test_intentional_failure`, `1 failed, 3 passed`):
https://github.com/mohamad-abdullah-710/week6-code-review/actions/runs/43636602734
The branch was deleted afterwards; `master` was never touched.

Side note: CI showed a `StarletteDeprecationWarning` about `httpx` in the test client. It
comes from unpinned library versions in `requirements.txt`, not from our code.

---

## 2. Feature PRs (Part II)

### PR 1 — Streak (`feature/streak`)
- PR: https://github.com/mohamad-abdullah-710/week6-code-review/pull/1
- Commit: `4582ccb`
- CI: success, https://github.com/mohamad-abdullah-710/week6-code-review/actions/runs/43636775153
- One-shot prompt:
  > Add `GET /habits/{id}/streak` to the habit tracker. It returns the current run of
  > consecutive days, up to and including today, that have a check-in. Return 404 for an
  > unknown habit. A habit with no check-in today has a streak of 0. Count duplicate
  > check-ins on the same day once. Add pytest tests that don't depend on the real date.
- Tests added (6): consecutive days, gap, no check-in today, duplicates, future check-ins,
  unknown habit 404.

### PR 2 — Validation (`feature/validation`)
- PR: https://github.com/mohamad-abdullah-710/week6-code-review/pull/2
- Commit: `b4f2eb7`
- CI: success, https://github.com/mohamad-abdullah-710/week6-code-review/actions/runs/43636778738
- One-shot prompt:
  > Add input validation to the habit tracker. `POST /habits` must reject empty or
  > whitespace-only names, and `POST /habits/{id}/checkin` must reject any `day` that isn't
  > a real calendar date in `YYYY-MM-DD` format. Return 422 with a clear message. Use
  > Pydantic validators and add pytest tests for valid and invalid input.
- Tests added (15 cases): blank names, whitespace stripping, 7 malformed days, 3 impossible
  dates, leap day accepted.

---

## 3. My review vs. the AI's review

How I reviewed: I went through both diffs with Claude Code explaining what each part does,
then wrote down my own opinion on each point. The "Claude Code self-review" column was
written by the implementing agent, not by me.

### PR 1 — Streak
CodeRabbit result: 1 nitpick ("Trivial · Maintainability · Quick win"), merge risk "Minimal".
[Review](https://github.com/mohamad-abdullah-710/week6-code-review/pull/1#pullrequestreview-5907096325)

| My review | Claude Code self-review | CodeRabbit |
|---|---|---|
| — | Uses the **server's** date: a user in another time zone can see 0 around midnight. | Not mentioned |
| **Annoying for users.** If I checked in Monday and Tuesday, on Wednesday morning it should still say 2 until the day ends, because today isn't over yet. | Streak is 0 every morning until today's check-in; follows the task wording, but users may find it surprising. | Not mentioned |
| — | Invalid stored days are skipped silently (no log or error). | Not mentioned |
| **Agree, useful.** Tests should use a temporary database so fake habits don't accumulate in the real database and cause problems later. | Tests write to the real `habits.db` (inherited from the starter), so test data piles up in the dev database. | **Same finding, more concrete:** use a `tmp_path` database fixture (`main.DB_PATH` + `main.init_db()`); also noted the unknown-habit test assumes ID `99999` doesn't exist (`test_main.py` lines 39–41) |
| — | Conflicts with PR 2 (imports + end of `test_main.py`), checked with `git merge-tree`. | Not mentioned (it reviews one PR at a time) |

**Where the AI was better / worse:** CodeRabbit was better on the test database problem:
its comment was useful and told me exactly how to fix it. It was worse on user-facing
behaviour: it did not mention that the streak shows 0 in the morning, which I find annoying.

### PR 2 — Validation
CodeRabbit result: **"No actionable comments were generated"**, merge risk "Minimal". Its
walkthrough summarised the change correctly (trimmed names, ASCII `YYYY-MM-DD`, real
calendar dates, leap-day test).
[Comment](https://github.com/mohamad-abdullah-710/week6-code-review/pull/2#issuecomment-6883988749)

| My review | Claude Code self-review | CodeRabbit |
|---|---|---|
| — | Returns 422, not 400 (task allows either; 422 is FastAPI's standard). | Not mentioned |
| — | Names are now **stored stripped**, a small behavior change for existing clients. | Described in walkthrough, not flagged as a risk |
| **Real bug:** check-ins with future dates (e.g. `2030-01-01`) are still accepted. | Not covered: future dates, duplicate same-day check-ins, max name length. | Not mentioned |
| — | Bad body + unknown habit gives 422 before 404. | Not mentioned |
| — | Same merge conflict with PR 1. | Not mentioned |

**Where the AI was better / worse:** Worse. CodeRabbit said there were no issues but missed
a real bug (future dates are accepted). This makes me trust it less: CodeRabbit is helpful,
but its reviews shouldn't be trusted completely without manual testing.

Setup note: CodeRabbit first did not review either PR because it was installed on a
different GitHub account (`mohamdwork`) than the repo owner (`mohamad-abdullah-710`).
After installing it on the right account and commenting `@coderabbitai review`, both
reviews arrived within a few minutes.

---

## 4. What I learned

Black and ruff mainly check code style, formatting and common issues, so they could never
find a problem like the test database one: they don't understand the application's
behaviour or database logic the way CodeRabbit can. That is why the two work well together:
the guardrails catch the simple things automatically on every push, and the AI reviewer
looks at what the code actually does. But CodeRabbit also said "no issues" on a PR that
still accepts future dates, so I would not merge a PR just because it approved it. I would
still read the code myself, because automated tools can miss bugs and human review is
important before merging.
