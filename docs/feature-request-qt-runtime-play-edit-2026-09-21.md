# Feature request: Qt runtime play and edit in place

GitHub issue: https://github.com/SimonBarnett/open-tts/issues/13

## Summary

A Qt (PySide6) runtime for a rendered interview: play `interview.mp4` against `timings.json` + YAML, scrub the timeline, change a line / speaker / cue, and re-render only what changed.

#9 is the authoring wizard. This FR is the desk after `python -m open_tts render`. Same engine (`open_tts.render`, `open_tts.video`). Do not fork another `interviewN/build_video.py`.

## Gap

Render is fire-and-forget. Changing one cue means editing YAML in a text editor and rebuilding the whole show.

## Locked launch

`python -m open_tts.studio --edit <output-dir-or-yaml>`

Re-render actions call the existing engine: line / cues-only (`--skip-tts`) / full. Unchanged sentence MP3s are reused. Keys from the environment only.

## Out of scope

Image-LLM character bake (#9 flow A). Extra expressions (#10) or phoneme tables (#11/#12) beyond consuming them if present. Remaining interview wording dumps (#3). NLE features. Audiotour / `tts_play.py`.

## Acceptance

- [ ] `python -m open_tts.studio --edit <output-dir-or-yaml>` opens a player + line inspector.
- [ ] Playhead follows `timings.json`; next/prev line lands on sentence bounds.
- [ ] Changing speaker / text / cue on a line and Save updates YAML in #1 schema.
- [ ] Render line / render video call the existing engine; no new `build_video.py`.
- [ ] Unchanged sentence MP3s are reused.
- [ ] Works with partner-smart-catalogue output layout.
- [ ] Dirty-block helper is unit-tested without Qt.
