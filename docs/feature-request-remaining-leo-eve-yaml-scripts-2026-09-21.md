# Feature request: remaining Leo/Eve interviews as YAML scripts

Parked from MRB of https://github.com/SimonBarnett/open-tts/issues/1
(SHA 5b3358c34dc736b9918e1cedea42997bee53e702). Adjacent hole: issue #1
acceptance says existing Leo/Eve interviews can be expressed as script
files without changing wording. Only `interviews/partner-smart-catalogue.yaml`
(interview1 / interview_audio2 wording) landed.

## Summary

Express the three remaining Leo/Eve interviews as `interviews/*.yaml` plus
character ids. Do not change wording. Do not fork new `interviewN.py` /
`build_video.py`. Use `python -m open_tts render` once issue #1 is green.

## Gap vs current tree

| Legacy source | Topic | YAML today |
|---|---|---|
| `interview1/interview.py` → `interview_audio2/` | Partner Smart Catalogue | `interviews/partner-smart-catalogue.yaml` |
| `interview2/interview1.py` → `interview_audio1/` | Technical vault / deep-dive | missing |
| `interview_audio3/interview.py` → `interview3/` | White-label partner | missing |
| `interview_audio4/interview.py` → `interview4/` | Marketing door / three markets | missing |

## Out of scope

- Changing any spoken line.
- Replacing Grok TTS / API credentials.
- Audiotour JSON (`tts_play.py`).
- Implementing issue #1 required fixes (pause cue, dual-screen compose,
  `full_interview.wav` output path). Those stay on that MRB board.

## Acceptance

- [ ] Vault / technical interview wording lives in `interviews/*.yaml` and
      matches `interview2/interview1.py` `dialogue` tuples 1:1.
- [ ] White-label interview wording lives in `interviews/*.yaml` and matches
      `interview_audio3/interview.py` `dialogue` tuples 1:1.
- [ ] Marketing-door interview wording lives in `interviews/*.yaml` and
      matches `interview_audio4/interview.py` `dialogue` tuples 1:1.
- [ ] No new per-show Python mux script.
- [ ] Prior `interview*` folders stay intact.
