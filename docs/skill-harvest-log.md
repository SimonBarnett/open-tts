# Skill harvest log

## 2026-09-22

Harvested session playbooks into `.grok/skills/open-tts-drive/SKILL.md` and added `.grok/skills/harvest-open-tts/SKILL.md`.

- Original faces: `characters/visemes/leo.png` (monologue close-up) and `eve.png` (half-screen interview), not the grey pause stub or drawn cartoons.
- Voice dropdown: live `GET /v1/tts/voices` (28 built-ins looked up 2026-09-22); fallback `open_tts/tts.py` `BUILTIN_TTS_VOICES`.
- Per-utterance Screen full/split; Left/Right cast overrides and Swap sides; attentive listener on the silent split side.
- Framing: `open_tts/framing.py` derives full monologue vs left/right half from the original cells.
- Windows studio launch via `%TEMP%\open-tts-studio.bat` + Explorer so Qt sees an audio device.
- Synced drive skill to `~/.grok/skills/open-tts-drive/SKILL.md`.
