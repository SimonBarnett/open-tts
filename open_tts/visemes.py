"""G2P, phoneme-to-viseme mapping, and timed phone tracks for lip-sync."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

# ARPAbet phone → viseme id (vowels row 0, consonants row 1 in sprite sheet).
_PHONE_TO_VISEME: dict[str, str] = {}
for _phones, _vis in (
    (("P", "B", "M", "EM"), "mbp"),
    (("F", "V"), "fv"),
    (("TH", "DH"), "th"),
    (("L", "EL"), "l"),
    (("S", "Z", "T", "D", "N"), "sz"),
    (("SH", "ZH", "CH", "JH"), "sh"),
    (("IY", "IH", "Y", "EY"), "i"),
    (("EH", "AE"), "e"),
    (("AA", "AH", "AX"), "a"),
    (("AO", "OW", "OY", "AW"), "o"),
    (("UW", "UH", "W", "ER", "AXR"), "u"),
    (("HH",), "pause"),
):
    for _p in _phones:
        _PHONE_TO_VISEME[_p] = _vis

_DIPHTHONG_EXPAND: dict[str, list[str]] = {
    "AY": ["AA", "IY"],
    "AW": ["AA", "UH"],
    "OY": ["AO", "IY"],
    "OW": ["AO", "UW"],
}

_COART_SEC = 0.04

_VOWEL_BASES = frozenset({"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW", "AX", "AXR"})


def _strip_stress(phone: str) -> str:
    return phone.rstrip("012")


def phone_to_viseme(phone: str) -> str:
    base = _strip_stress(phone)
    return _PHONE_TO_VISEME.get(base, "pause")


def expand_phones(phones: list[str]) -> list[str]:
    out: list[str] = []
    for p in phones:
        base = _strip_stress(p)
        if base in _DIPHTHONG_EXPAND:
            out.extend(_DIPHTHONG_EXPAND[base])
        else:
            out.append(base)
    return out


@lru_cache(maxsize=1)
def _load_cmudict() -> dict[str, list[str]]:
    path = Path(__file__).resolve().parent / "data" / "cmudict-0.7b.txt"
    lexicon: dict[str, list[str]] = {}
    if not path.is_file():
        return lexicon
    with path.open(encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";;;"):
                continue
            if "(" in line:
                word_part, _, remainder = line.partition("(")
                pron = remainder.split(")", 1)[-1].strip()
                word = word_part.strip().upper()
            else:
                parts = line.split(maxsplit=1)
                if len(parts) < 2:
                    continue
                word, pron = parts[0].upper(), parts[1]
            phones = [_strip_stress(p) for p in pron.split()]
            if word not in lexicon:
                lexicon[word] = phones
    return lexicon


def _g2p_fallback(word: str) -> list[str]:
    """Minimal deterministic fallback when CMUdict has no entry."""
    w = re.sub(r"[^A-Za-z']", "", word).upper()
    if not w:
        return []
    if len(w) <= 2:
        return ["AH"]
    return ["AH"] * max(1, len(w) // 2)


def g2p_word(word: str) -> list[str]:
    clean = re.sub(r"[^A-Za-z']", "", word)
    if not clean:
        return []
    key = clean.upper()
    lex = _load_cmudict()
    phones = lex.get(key)
    if phones is None and key.endswith("'S") and len(key) > 2:
        phones = lex.get(key[:-2])
        if phones:
            phones = phones + ["Z"]
    if phones is None:
        phones = _g2p_fallback(clean)
    return expand_phones(phones)


def g2p_text(text: str) -> list[str]:
    phones: list[str] = []
    for token in text.split():
        phones.extend(g2p_word(token))
    return phones


def _phone_weight(phone: str) -> float:
    base = _strip_stress(phone)
    if base in _VOWEL_BASES:
        return 2.0
    return 1.0


def build_phone_track(text: str, duration_sec: float) -> list[dict]:
    """
    Map text to timed viseme intervals over [0, duration_sec).
    t0/t1 are relative to the start of the sentence.
    """
    phones = g2p_text(text)
    if not phones or duration_sec <= 0:
        return []
    weights = [_phone_weight(p) for p in phones]
    total = sum(weights)
    t = 0.0
    track: list[dict] = []
    for phone, w in zip(phones, weights):
        dt = duration_sec * (w / total)
        vis = phone_to_viseme(phone)
        track.append(
            {
                "phone": phone,
                "viseme": vis,
                "t0": round(t, 6),
                "t1": round(t + dt, 6),
            }
        )
        t += dt
    if track:
        track[-1]["t1"] = round(duration_sec, 6)
    return track


def viseme_at_time(track: list[dict], t: float) -> str:
    if not track:
        return "pause"
    for i, seg in enumerate(track):
        t0, t1 = seg["t0"], seg["t1"]
        if t < t0:
            return "pause"
        if t0 <= t < t1:
            if i + 1 < len(track) and t1 - t <= _COART_SEC:
                return track[i + 1]["viseme"]
            return seg["viseme"]
    return track[-1]["viseme"]
