# Feature request: move/size model on initial still before clips

## Summary

After **New face**, the studio must let the operator **move and size** the
model on that still (drag + Size) **before** Approve face / generating
viseme VIDEO clips. Dual characters are **two halves of the screen**
(Left | Right) — there is no separate "split talking" mode.

## Locked

- Placement: `zoom` (1..4) + `pan_x` / `pan_y` (-1..1) in
  `open_tts/framing.py` (`Placement`, `apply_placement`).
- Saved beside the hero: `characters/heroes/<id>.placement.json`.
- Full / Left / Right previews update live from the placed still.
- Clip I2V uses the placed still as the reference image.
- Screen `split` = left half + right half. Not a talking mode.

## Acceptance

- [ ] Drag pans the still; Size / wheel zooms before Approve face.
- [ ] Approve face persists placement with the hero.
- [ ] Update this clip uses the placed hero.
- [ ] Left and Right are halves of the stage plate.
