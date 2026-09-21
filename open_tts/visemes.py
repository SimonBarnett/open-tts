"""G2P, phoneme-to-viseme mapping, and timed viseme intervals for lip sync."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import pronouncing

# Until #11 adds consonant mouth cells, sheet lookup maps these to pause.
SHEET_CONSONANT_STANDINS = frozenset({"mbp", "fv", "th", "l", "sz", "sh"})

SHEET_VISEMES = frozenset({"a", "e", "i", "o", "u", "pause"})

_VISEME_PHONES: dict[str, tuple[str, ...]] = {
    "i": ("IY", "IH", "Y", "EY"),
    "e": ("EH", "AE"),
    "a": ("AA", "AH", "AX", "AY"),
    "o": ("AO", "OW", "OY", "AW"),
    "u": ("UW", "UH", "W", "ER", "AXR"),
    "mbp": ("P", "B", "M", "EM"),
    "fv": ("F", "V"),
    "th": ("TH", "DH"),
    "l": ("L", "EL"),
    "sz": ("S", "Z", "T", "D", "N"),
    "sh": ("SH", "ZH", "CH", "JH"),
    "pause": ("HH",),
}

_PHONE_TO_VISEME: dict[str, str] = {}
for _vis, _phones in _VISEME_PHONES.items():
    for _ph in _phones:
        _PHONE_TO_VISEME[_ph] = _vis

_FALLBACK_PAUSE_PHONES = frozenset({"R", "K", "G", "NG"})

_STOPS = frozenset({"P", "B", "T", "D", "K", "G"})
_VOWEL_PHONES = frozenset(
    ph for vis, phones in _VISEME_PHONES.items() if vis in "aeiou" for ph in phones
)

# Diphthongs split in time (first viseme fraction, then second).
_DIPHTHONG_SPLIT: dict[str, tuple[tuple[str, float], tuple[str, float]]] = {
    "AY": (("a", 0.6), ("i", 0.4)),
    "OW": (("o", 0.6), ("u", 0.4)),
    "EY": (("e", 0.6), ("i", 0.4)),
    "OY": (("o", 0.6), ("i", 0.4)),
    "AW": (("a", 0.6), ("u", 0.4)),
}

_COARTICULATION_SEC = 0.04
_MBP_WEIGHT_SCALE = 0.65


def strip_stress(phone: str) -> str:
    return re.sub(r"\d+$", "", phone.upper())


def phone_to_viseme(phone: str) -> str:
    base = strip_stress(phone)
    if base in _PHONE_TO_VISEME:
        return _PHONE_TO_VISEME[base]
    if base in _FALLBACK_PAUSE_PHONES:
        return "pause"
    return "pause"


def sheet_viseme(viseme: str) -> str:
    key = viseme.lower()
    if key in SHEET_CONSONANT_STANDINS:
        return "pause"
    if key in SHEET_VISEMES:
        return key
    return "pause"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text)


@lru_cache(maxsize=1)
def _g2p_en():
    import nltk

    for resource in ("cmudict", "averaged_perceptron_tagger_eng"):
        nltk.download(resource, quiet=True)
    from g2p_en import G2p

    return G2p()


def word_to_phones(word: str) -> list[str]:
    lower = word.lower()
    candidates = pronouncing.phones_for_word(lower)
    if candidates:
        return candidates[0].split()
    g2p = _g2p_en()
    return [p for p in g2p(lower) if p and not p.isspace()]


def text_to_phones(text: str) -> list[str]:
    phones: list[str] = []
    for word in _tokenize(text):
        phones.extend(word_to_phones(word))
    return phones


@dataclass(frozen=True)
class _AlignUnit:
    phone: str
    viseme: str
    weight: float


def _alignment_weight(base: str, viseme: str) -> float:
    if base in _STOPS:
        return 0.5
    if base in _VOWEL_PHONES or viseme in "aeiou":
        return 2.0
    if viseme == "mbp":
        return 0.5 * _MBP_WEIGHT_SCALE
    return 1.0


def _expand_phone(phone: str) -> list[_AlignUnit]:
    base = strip_stress(phone)
    if base in _DIPHTHONG_SPLIT:
        (v0, f0), (v1, f1) = _DIPHTHONG_SPLIT[base]
        return [
            _AlignUnit(phone, v0, 1.0 * f0 * 2),
            _AlignUnit(phone, v1, 1.0 * f1 * 2),
        ]
    vis = phone_to_viseme(phone)
    return [_AlignUnit(phone, vis, _alignment_weight(base, vis))]


def _weighted_intervals(
    units: list[_AlignUnit], duration: float
) -> list[dict[str, float | str]]:
    if not units or duration <= 0:
        return []
    total_w = sum(u.weight for u in units)
    if total_w <= 0:
        return []
    t = 0.0
    out: list[dict[str, float | str]] = []
    for u in units:
        dt = duration * (u.weight / total_w)
        out.append(
            {
                "phone": strip_stress(u.phone),
                "viseme": u.viseme,
                "t0": round(t, 6),
                "t1": round(t + dt, 6),
            }
        )
        t += dt
    return out


def _align_from_tts_timestamps(
    units: list[_AlignUnit],
    duration: float,
    graph_chars: list,
    graph_times: list,
) -> list[dict[str, float | str]] | None:
    """Spread phone units across TTS character timestamps when lengths match."""
    if not graph_times or len(graph_chars) != len(graph_times):
        return None
    try:
        times = [float(x) for x in graph_times]
    except (TypeError, ValueError):
        return None
    if not times or times[-1] <= 0:
        return None
    scale = duration / times[-1] if times[-1] else 1.0
    char_boundaries = [t * scale for t in times]
    n_units = len(units)
    n_chars = len(char_boundaries)
    if n_chars < n_units:
        return None
    # Evenly assign character index ranges to each phone unit.
    out: list[dict[str, float | str]] = []
    for i, u in enumerate(units):
        c0 = int(i * n_chars / n_units)
        c1 = int((i + 1) * n_chars / n_units) - 1
        c1 = max(c0, min(c1, n_chars - 1))
        t0 = char_boundaries[c0 - 1] if c0 > 0 else 0.0
        t1 = char_boundaries[c1]
        if i == n_units - 1:
            t1 = duration
        out.append(
            {
                "phone": strip_stress(u.phone),
                "viseme": u.viseme,
                "t0": round(t0, 6),
                "t1": round(max(t1, t0), 6),
            }
        )
    return out


def build_phone_intervals(
    text: str,
    duration: float,
    *,
    graph_chars: list | None = None,
    graph_times: list | None = None,
) -> list[dict]:
    phones = text_to_phones(text)
    units: list[_AlignUnit] = []
    for ph in phones:
        units.extend(_expand_phone(ph))
    if not units:
        return [
            {
                "phone": "HH",
                "viseme": "pause",
                "t0": 0.0,
                "t1": round(max(duration, 0.0), 6),
            }
        ]
    if graph_chars is not None and graph_times is not None:
        aligned = _align_from_tts_timestamps(
            units, duration, graph_chars, graph_times
        )
        if aligned:
            return aligned
    return _weighted_intervals(units, duration)


def viseme_at_time(phones: list[dict], t: float) -> str:
    if not phones:
        return "pause"
    for i, seg in enumerate(phones):
        t0, t1 = float(seg["t0"]), float(seg["t1"])
        if t0 <= t < t1:
            vis = str(seg["viseme"])
            if i + 1 < len(phones) and t1 - t <= _COARTICULATION_SEC:
                vis = str(phones[i + 1]["viseme"])
            return vis
    if t >= float(phones[-1]["t1"]):
        return str(phones[-1]["viseme"])
    return str(phones[0]["viseme"])


def phones_for_line(line: dict) -> list[dict]:
    cached = line.get("phones")
    if cached is not None:
        return cached
    duration = float(line.get("duration") or 0.0)
    return build_phone_intervals(
        line.get("text") or "",
        duration,
        graph_chars=line.get("graph_chars"),
        graph_times=line.get("graph_times"),
    )


def attach_phones_to_segments(segments: list[dict]) -> None:
    for seg in segments:
        seg["phones"] = build_phone_intervals(
            seg.get("text") or "",
            float(seg.get("duration") or 0.0),
            graph_chars=seg.get("graph_chars"),
            graph_times=seg.get("graph_times"),
        )
