# Build and test plan: interview project folders

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/14
FR: `docs/feature-request-interview-project-folders-2026-09-21.md`

## Goals / non-goals

`projects/<slug>` is the render cwd. Headless `project new/list/import`. Explorer can stub Open if #13 is not merged yet, but CLI must work. Do not auto-delete legacy `interviewN/`.

## Phases

1. `python -m open_tts project new|list|import` writing `interview.yaml` + `project.json`.
2. Point `render_interview` default output at the project root.
3. Import partner YAML without wording changes; tests compare script texts.
4. Headless tests; Qt explorer is optional if #13 is in the same tree.

## Definition of done

Issue #14 acceptance green except studio Open if #13 is still open (then park that gap, do not block CLI). PR from `work/<job>`. Never push `main`. Never merge.
