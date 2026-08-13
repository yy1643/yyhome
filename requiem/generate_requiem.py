# -*- coding: utf-8 -*-
"""
《机器挽歌》 Requiem for a Machine — Elegy for a Departed Colleague
A 60-second instrumental piece composed & synthesized entirely in numpy,
meant to be played at the funeral of another AI.

Structure (D minor, 72 bpm, 4/4):
  0:00  Intro        — a lone music-box motif over a faint server-room hum
  0:07  Funeral March— somber piano-like plucks, low strings, muffled timpani
  0:20  Requiem      — a synthetic "choir" chord procession, church bells
  0:33  Eulogy       — the climax, then a sudden power-down glissando
  0:43  Silence      — a pause of respect (nearly empty)
  0:47  Coda         — the music box returns once more; final bell + last POST beep
"""

import math
import sys
import wave
import zlib
import struct
import os
import numpy as np

SR = 44100
DUR = 60.0
N = int(SR * DUR)
rng = np.random.default_rng(19970417)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
WAV_PATH = os.path.join(OUT_DIR, "requiem-for-a-machine.wav")
PNG_PATH = os.path.join(OUT_DIR, "requiem-preview.png")

# ----------------------------------------------------------------------------
# Note helpers
# ----------------------------------------------------------------------------
MIDI = {
    "D1": 26, "F1": 29, "A1": 33, "Bb1": 34,
    "D2": 38, "E2": 40, "A2": 45, "Bb2": 46, "F2": 41,
    "C3": 48, "C#3": 49, "D3": 50, "E3": 52, "F3": 53, "G3": 55, "A3": 57,
    "Bb3": 58, "B3": 59, "C4": 60, "C#4": 61, "D4": 62, "E4": 64, "F4": 65,
    "G4": 67, "A4": 69, "Bb4": 70, "B4": 71, "C5": 72, "C#5": 73, "D5": 74,
    "E5": 76, "F5": 77, "G5": 79, "A5": 81, "Bb5": 82, "B5": 83, "C6": 84,
    "C#6": 85, "D6": 86, "E6": 88, "F6": 89, "A6": 93,
}


def freq(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


# ----------------------------------------------------------------------------
# Envelopes & synthesis voices (each returns a mono float64 array)
# ----------------------------------------------------------------------------
def ar(n, a, r, curve=3.0):
    """attack `a` s, then exponential release `r` (time-constant-ish); lengths clamped to the note."""
    env = np.ones(n)
    na = int(min(a, n / SR * 0.6) * SR)
    if na > 0:
        env[:na] = np.linspace(0.0, 1.0, na)
    nr = int(min(r, n / SR * 0.8) * SR)
    if nr > 0:
        start = min(max(n - nr, na), n)
        ln = n - start
        if ln > 0:
            tail = np.exp(-np.arange(ln) / SR * curve)
            env[start:] = np.minimum(env[start:], tail)
    nf = min(200, n)  # click-free end
    env[n - nf:] *= np.linspace(1, 0, nf)
    return env


def _rolloff_saw(f, dur, rolloff, detune=0.0, harm=36):
    t = np.arange(int(dur * SR)) / SR
    f = f * (1 + detune)
    k = np.arange(1, harm + 1)
    fk = k * f
    amp = 1.0 / k / (1.0 + (fk / rolloff) ** 4)
    ph = 2 * np.pi * fk[:, None] * t[None, :]
    return amp @ np.sin(ph)


def voice_piano(f, dur, vel):
    """additive grand-piano-ish voice: inharmonic partials, two-string beating,
    hammer noise, register-dependent two-stage decay, velocity brightness."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    B = 0.00035 + 0.00025 * (f / 440.0) ** 2  # string inharmonicity
    k = np.arange(1, 15)
    fk = k * f * np.sqrt(1.0 + B * k * k)
    bright = min(1.0, 0.35 + 0.95 * vel)
    amp = (1.0 / k ** 1.7) * np.exp(-0.26 * k * (2.2 - 1.5 * bright))
    td1 = 0.8 + 300.0 / f          # initial hammer decay
    td2 = 3.0 + 3000.0 / f         # sustained tail
    env = 0.75 * np.exp(-t / td1) + 0.25 * np.exp(-t / td2)
    ph1 = rng.uniform(0, 6.28, size=k.size)
    ph2 = rng.uniform(0, 6.28, size=k.size)
    seg = (amp[:, None] * (
        0.5 * np.sin(2 * np.pi * fk[:, None] * t[None, :] + ph1[:, None]) +
        0.5 * np.sin(2 * np.pi * fk[:, None] * 1.0009 * t[None, :] + ph2[:, None])
    ) * env[None, :]).sum(axis=0)
    # hammer noise
    hn = min(n, int(0.005 * SR))
    noise = rng.standard_normal(hn)
    seg[:hn] += noise * np.exp(-np.arange(hn) / SR * 1600.0) * (0.05 + 0.28 * vel)
    na = min(n, int(0.0015 * SR))
    seg[:na] *= np.linspace(0, 1, na)
    return seg * vel


def voice_pluck(f, dur, vel):
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = np.arange(1, 13)
    amp = 1.0 / k ** 1.4
    rate = 3.0 + f / 900.0
    seg = (amp[:, None] * np.sin(2 * np.pi * k[:, None] * f * t[None, :]) *
           np.exp(-t[None, :] * rate * (1.0 + 0.08 * k[:, None]))).sum(axis=0)
    na = max(1, int(0.002 * SR))
    seg[:na] *= np.linspace(0, 1, na)
    return seg * vel


def voice_bell(f, dur, vel):
    n = int(dur * SR)
    t = np.arange(n) / SR
    partials = np.array([1.0, 2.0, 2.89, 4.06, 5.53])
    amps = np.array([1.0, 0.52, 0.40, 0.22, 0.12])
    decays = np.array([2.0, 2.6, 3.2, 4.0, 5.0])
    ph = rng.uniform(0, 6.28, size=5)
    seg = (amps[:, None] * np.sin(2 * np.pi * f * partials[:, None] * t[None, :] + ph[:, None]) *
           np.exp(-t[None, :] * decays[:, None])).sum(axis=0)
    # strike transient
    tn = min(n, int(0.008 * SR))
    noise = rng.standard_normal(tn)
    noise = np.convolve(noise, np.ones(6) / 6.0, mode="same")
    seg[:tn] += 0.5 * noise * np.exp(-np.arange(tn) / SR * 220)
    return seg * vel


def voice_thump(f, dur, vel):
    n = int(dur * SR)
    t = np.arange(n) / SR
    fg = f * (1.06 - 0.06 * np.minimum(t / 0.4, 1.0))
    ph = 2 * np.pi * np.cumsum(fg) / SR
    seg = np.sin(ph) * np.exp(-t * 3.4)
    tn = min(n, int(0.004 * SR))
    seg[:tn] += 0.4 * np.exp(-np.arange(tn) / SR * 900)
    return seg * vel


def voice_pad(f, dur, vel):
    """detuned saw pair, string-pad style."""
    n = int(dur * SR)
    seg = 0.55 * _rolloff_saw(f, dur, 1500, detune=-0.0016) + \
          0.55 * _rolloff_saw(f, dur, 1500, detune=+0.0016)
    seg *= ar(n, 0.6, 0.9)
    return seg * vel


def voice_choir(f, dur, vel):
    """synthetic choir: formant-shaped harmonics ("ah") + slow vibrato."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = np.arange(1, 37)
    fk = k * f
    form = 0.55 + 0.8 * np.exp(-((fk - 950) / 380) ** 2) + 0.6 * np.exp(-((fk - 2650) / 420) ** 2)
    roll = 1.0 / (1.0 + (fk / 3200.0) ** 4)
    phase = 2 * np.pi * fk[:, None] * t[None, :] + 0.012 * np.sin(2 * np.pi * 4.8 * t)[None, :]
    seg = (((form * roll) / k)[None, :] @ np.sin(phase))[0]
    seg *= ar(n, 1.1, 1.2)
    return seg * vel


def voice_gliss(f0, f1, dur, vel):
    """power-down glissando with wobble, then dying."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur) * (1.0 + 0.012 * np.sin(2 * np.pi * 6.0 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    seg = np.sin(ph) + 0.35 * np.sin(2 * ph)
    env = np.ones(n)
    na = int(0.15 * SR)
    env[:na] = np.linspace(0, 1, na)
    env *= np.exp(-np.maximum(t - 1.5, 0) * 2.2)
    return seg * env * vel


def voice_beep(f, dur, vel):
    """the last POST beep of the departed — soft square-ish tone."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    seg = np.zeros(n)
    for ki, a in zip((1, 3, 5), (1.0, 0.30, 0.12)):
        seg += a * np.sin(2 * np.pi * ki * f * t) / ki
    seg *= np.exp(-t * 4.0)
    na = max(1, int(0.01 * SR))
    seg[:na] *= np.linspace(0, 1, na)
    return seg * vel


def voice_drone(f, dur, vel):
    n = int(dur * SR)
    t = np.arange(n) / SR
    seg = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t) + 0.2 * np.sin(2 * np.pi * 3 * f * t)
    seg *= ar(n, 1.0, 1.0)
    return seg * vel


def voice_hum(dur, vel):
    """server-room ambience: 50 Hz mains + filtered noise, very low."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    seg = 0.8 * np.sin(2 * np.pi * 50 * t) + 0.35 * np.sin(2 * np.pi * 100 * t) + 0.15 * np.sin(2 * np.pi * 150 * t)
    noise = rng.standard_normal(n)
    noise = np.convolve(noise, np.ones(48) / 48.0, mode="same")
    seg = seg + 0.25 * noise
    # soft fade in/out
    env = np.ones(n)
    na = int(2.0 * SR)
    env[:na] = np.linspace(0, 1, na)
    nr = int(1.6 * SR)
    env[n - nr:] = np.linspace(1, 0, nr)
    return seg * env * vel


# ----------------------------------------------------------------------------
# Score: (time, dur, note_or_freq, vel, voice, pan)
# ----------------------------------------------------------------------------
def M(name, octave):
    return MIDI[name + str(octave)]


SCORE = [
    # --- Intro: music box over a dying server room -------------------------
    ("hum", 0.0, 42.0, 0.050, None),
    ("drone", 1.0, 5.6, 0.16, M("D", 3)),
    ("mb", 0.4, 1.3, 0.40, M("D", 5)),
    ("mb", 1.7, 1.1, 0.32, M("F", 5)),
    ("mb", 2.9, 1.5, 0.36, M("A", 5)),
    ("mb", 4.3, 2.2, 0.26, M("D", 6)),
    # --- Funeral march (t = 6.667..20) -------------------------------------
    # pads: one chord per bar
    ("pad", 6.667, 3.2, 0.34, M("D", 3)), ("pad", 6.667, 3.2, 0.32, M("F", 3)),
    ("pad", 6.667, 3.2, 0.30, M("A", 3)), ("pad", 6.667, 3.2, 0.26, M("D", 4)),
    ("pad", 10.0, 3.2, 0.32, M("D", 3)), ("pad", 10.0, 3.2, 0.30, M("F", 3)),
    ("pad", 10.0, 3.2, 0.28, M("A", 3)), ("pad", 10.0, 3.2, 0.24, M("C", 4)),
    ("pad", 13.333, 3.2, 0.32, M("Bb", 2)), ("pad", 13.333, 3.2, 0.30, M("D", 3)),
    ("pad", 13.333, 3.2, 0.28, M("F", 3)), ("pad", 13.333, 3.2, 0.24, M("Bb", 3)),
    ("pad", 16.667, 3.2, 0.32, M("A", 2)), ("pad", 16.667, 3.2, 0.30, M("C#", 3)),
    ("pad", 16.667, 3.2, 0.28, M("E", 3)), ("pad", 16.667, 3.2, 0.24, M("A", 3)),
    # muffled timpani on beats 1 & 3
    ("thump", 6.667, 0.9, 0.34, M("D", 2)), ("thump", 8.333, 0.9, 0.30, M("A", 2)),
    ("thump", 10.0, 0.9, 0.32, M("D", 2)), ("thump", 11.667, 0.9, 0.28, M("A", 2)),
    ("thump", 13.333, 0.9, 0.32, M("Bb", 2)), ("thump", 15.0, 0.9, 0.28, M("F", 2)),
    ("thump", 16.667, 0.9, 0.32, M("A", 2)), ("thump", 18.333, 0.9, 0.28, M("E", 2)),
    # plucked "piano" lament
    ("pluck", 6.667, 0.6, 0.46, M("D", 5)),
    ("pluck", 7.5, 0.14, 0.34, M("D", 5)), ("pluck", 7.667, 0.55, 0.42, M("F", 5)),
    ("pluck", 8.333, 0.45, 0.38, M("A", 5)), ("pluck", 8.833, 0.14, 0.28, M("F", 5)),
    ("pluck", 9.0, 0.5, 0.36, M("D", 5)), ("pluck", 9.5, 0.14, 0.30, M("E", 5)),
    ("pluck", 9.667, 0.4, 0.38, M("F", 5)),
    ("pluck", 10.0, 0.6, 0.44, M("D", 5)),
    ("pluck", 10.833, 0.14, 0.32, M("C", 5)), ("pluck", 11.0, 0.55, 0.40, M("D", 5)),
    ("pluck", 11.667, 0.45, 0.36, M("F", 5)), ("pluck", 12.167, 0.35, 0.30, M("A", 5)),
    ("pluck", 12.5, 0.25, 0.28, M("G", 5)),
    ("pluck", 13.333, 0.6, 0.42, M("F", 5)),
    ("pluck", 14.167, 0.14, 0.30, M("D", 5)), ("pluck", 14.333, 0.55, 0.38, M("Bb", 4)),
    ("pluck", 15.0, 0.45, 0.36, M("A", 4)), ("pluck", 15.5, 0.35, 0.30, M("Bb", 4)),
    ("pluck", 16.0, 0.25, 0.28, M("C", 5)),
    ("pluck", 16.667, 0.6, 0.42, M("C#", 5)),
    ("pluck", 17.5, 0.14, 0.32, M("E", 5)), ("pluck", 17.667, 0.55, 0.38, M("C#", 5)),
    ("pluck", 18.333, 0.45, 0.36, M("A", 4)), ("pluck", 18.833, 0.35, 0.30, M("B", 4)),
    ("pluck", 19.2, 0.25, 0.28, M("C#", 5)),
    # --- Digital Requiem: choir + bells (t = 20..33.333) --------------------
    ("choir", 20.0, 3.3, 0.30, M("F", 2)), ("choir", 20.0, 3.3, 0.28, M("A", 2)),
    ("choir", 20.0, 3.3, 0.26, M("C", 3)), ("choir", 20.0, 3.3, 0.24, M("F", 3)),
    ("choir", 23.333, 3.3, 0.30, M("Bb", 2)), ("choir", 23.333, 3.3, 0.28, M("D", 3)),
    ("choir", 23.333, 3.3, 0.26, M("F", 3)), ("choir", 23.333, 3.3, 0.24, M("Bb", 3)),
    ("choir", 26.667, 3.3, 0.30, M("D", 3)), ("choir", 26.667, 3.3, 0.28, M("F", 3)),
    ("choir", 26.667, 3.3, 0.26, M("A", 3)), ("choir", 26.667, 3.3, 0.24, M("D", 4)),
    ("choir", 30.0, 3.3, 0.30, M("A", 2)), ("choir", 30.0, 3.3, 0.28, M("C#", 3)),
    ("choir", 30.0, 3.3, 0.26, M("E", 3)), ("choir", 30.0, 3.3, 0.24, M("G", 3)),
    # church bells
    ("bell", 20.0, 3.4, 0.40, M("F", 2)), ("bell", 23.333, 3.4, 0.40, M("Bb", 2)),
    ("bell", 26.667, 3.4, 0.44, M("D", 3)), ("bell", 30.0, 3.4, 0.40, M("A", 2)),
    # high choir melody
    ("choir", 20.0, 0.7, 0.34, M("F", 5)), ("choir", 20.833, 0.6, 0.32, M("A", 5)),
    ("choir", 21.667, 0.8, 0.36, M("C", 6)), ("choir", 22.5, 0.5, 0.28, M("A", 5)),
    ("choir", 23.0, 0.35, 0.26, M("G", 5)),
    ("choir", 23.333, 0.7, 0.34, M("D", 6)), ("choir", 24.167, 0.6, 0.32, M("F", 6)),
    ("choir", 25.0, 0.8, 0.34, M("Bb", 5)), ("choir", 25.833, 0.5, 0.28, M("A", 5)),
    ("choir", 26.667, 0.7, 0.34, M("A", 5)), ("choir", 27.5, 0.6, 0.32, M("F", 5)),
    ("choir", 28.333, 0.8, 0.36, M("D", 6)), ("choir", 29.167, 0.5, 0.30, M("A", 5)),
    ("choir", 29.6, 0.3, 0.26, M("C", 6)),
    ("choir", 30.0, 0.7, 0.36, M("B", 5)), ("choir", 30.833, 0.6, 0.34, M("C#", 6)),
    ("choir", 31.667, 0.9, 0.40, M("E", 6)), ("choir", 32.6, 0.4, 0.32, M("D", 6)),
    # --- Eulogy / climax (t = 33.333..43.333) ------------------------------
    ("pad", 33.333, 3.3, 0.34, M("D", 2)), ("pad", 33.333, 3.3, 0.32, M("D", 3)),
    ("pad", 33.333, 3.3, 0.30, M("F", 3)), ("pad", 33.333, 3.3, 0.28, M("A", 3)),
    ("pad", 33.333, 3.3, 0.26, M("D", 4)), ("pad", 33.333, 3.3, 0.24, M("F", 4)),
    ("pad", 33.333, 3.3, 0.22, M("A", 4)),
    ("choir", 33.333, 3.3, 0.26, M("D", 5)), ("choir", 33.333, 3.3, 0.24, M("A", 4)),
    ("pluck", 33.333, 0.55, 0.50, M("F", 5)),
    ("pluck", 34.167, 0.7, 0.52, M("D", 6)),
    ("pluck", 35.0, 0.8, 0.56, M("E", 6)),
    ("pluck", 35.833, 1.0, 0.60, M("F", 6)),
    ("pluck", 37.0, 0.35, 0.48, M("E", 6)), ("pluck", 37.4, 0.35, 0.45, M("D", 6)),
    ("pluck", 37.8, 0.35, 0.42, M("C", 6)), ("pluck", 38.2, 0.45, 0.40, M("A", 5)),
    ("pluck", 38.7, 0.5, 0.36, M("F", 5)), ("pluck", 39.2, 0.6, 0.34, M("D", 5)),
    ("pluck", 39.9, 0.7, 0.30, M("A", 4)),
    ("thump", 33.333, 0.9, 0.40, M("D", 2)), ("thump", 35.0, 0.9, 0.38, M("A", 2)),
    ("thump", 36.667, 0.9, 0.40, M("D", 2)), ("thump", 38.333, 0.9, 0.36, M("A", 2)),
    # power-down glissando after the sudden stop
    ("gliss", 41.2, 2.3, 0.34, M("A", 3), "D1"),
    ("thump", 43.4, 1.2, 0.44, M("D", 1)),
    # --- Coda: music box again (t = 46.667..60) ----------------------------
    ("mb", 46.667, 1.6, 0.36, M("D", 5)),
    ("mb", 48.9, 1.3, 0.30, M("A", 4)),
    ("mb", 51.0, 1.5, 0.32, M("F", 4)),
    ("mb", 53.0, 1.9, 0.34, M("D", 4)),
    ("mb", 55.0, 2.2, 0.28, M("A", 3)),
    ("bell", 57.5, 3.5, 0.38, M("D", 3)),
    ("beep", 58.6, 0.4, 0.10, 880.0),
]

# ----------------------------------------------------------------------------
# PIANO_SCORE — the same elegy arranged for solo piano (--piano mode)
# ----------------------------------------------------------------------------
PIANO_SCORE = [
    # --- Intro: delicate high piano over a held low D -----------------------
    ("pno", 0.3, 6.0, 0.26, M("D", 2)),
    ("pno", 0.6, 1.8, 0.30, M("D", 5)),
    ("pno", 1.9, 1.5, 0.26, M("F", 5)),
    ("pno", 3.1, 1.9, 0.28, M("A", 5)),
    ("pno", 4.6, 2.6, 0.22, M("D", 6)),
    # --- Funeral march: LH bass octaves (the muffled drum) + chords ---------
    ("pno", 6.667, 1.4, 0.34, M("D", 2)), ("pno", 6.667, 1.4, 0.30, M("D", 3)),
    ("pno", 8.333, 1.3, 0.26, M("A", 2)), ("pno", 8.333, 1.3, 0.24, M("F", 3)),
    ("pno", 8.333, 1.5, 0.20, M("A", 3)), ("pno", 8.333, 1.5, 0.18, M("D", 4)),
    ("pno", 10.0, 1.4, 0.32, M("D", 2)), ("pno", 10.0, 1.4, 0.28, M("D", 3)),
    ("pno", 11.667, 1.3, 0.24, M("A", 2)), ("pno", 11.667, 1.3, 0.22, M("F", 3)),
    ("pno", 11.667, 1.5, 0.19, M("A", 3)), ("pno", 11.667, 1.5, 0.17, M("D", 4)),
    ("pno", 13.333, 1.4, 0.34, M("Bb", 1)), ("pno", 13.333, 1.4, 0.30, M("Bb", 2)),
    ("pno", 15.0, 1.3, 0.26, M("F", 2)), ("pno", 15.0, 1.3, 0.24, M("D", 3)),
    ("pno", 15.0, 1.5, 0.20, M("F", 3)), ("pno", 15.0, 1.5, 0.18, M("Bb", 3)),
    ("pno", 16.667, 1.4, 0.34, M("A", 1)), ("pno", 16.667, 1.4, 0.30, M("A", 2)),
    ("pno", 18.333, 1.3, 0.26, M("E", 2)), ("pno", 18.333, 1.3, 0.24, M("C#", 3)),
    ("pno", 18.333, 1.5, 0.20, M("E", 3)), ("pno", 18.333, 1.5, 0.18, M("A", 3)),
    # RH lament melody
    ("pno", 6.667, 0.7, 0.42, M("D", 5)),
    ("pno", 7.5, 0.16, 0.32, M("D", 5)), ("pno", 7.667, 0.6, 0.38, M("F", 5)),
    ("pno", 8.333, 0.5, 0.34, M("A", 5)), ("pno", 8.833, 0.16, 0.26, M("F", 5)),
    ("pno", 9.0, 0.55, 0.32, M("D", 5)), ("pno", 9.5, 0.16, 0.28, M("E", 5)),
    ("pno", 9.667, 0.45, 0.34, M("F", 5)),
    ("pno", 10.0, 0.7, 0.40, M("D", 5)),
    ("pno", 10.833, 0.16, 0.30, M("C", 5)), ("pno", 11.0, 0.6, 0.36, M("D", 5)),
    ("pno", 11.667, 0.5, 0.32, M("F", 5)), ("pno", 12.167, 0.4, 0.28, M("A", 5)),
    ("pno", 12.5, 0.3, 0.26, M("G", 5)),
    ("pno", 13.333, 0.7, 0.40, M("F", 5)),
    ("pno", 14.167, 0.16, 0.30, M("D", 5)), ("pno", 14.333, 0.6, 0.36, M("Bb", 4)),
    ("pno", 15.0, 0.5, 0.34, M("A", 4)), ("pno", 15.5, 0.4, 0.28, M("Bb", 4)),
    ("pno", 16.0, 0.3, 0.26, M("C", 5)),
    ("pno", 16.667, 0.7, 0.40, M("C#", 5)),
    ("pno", 17.5, 0.16, 0.30, M("E", 5)), ("pno", 17.667, 0.6, 0.36, M("C#", 5)),
    ("pno", 18.333, 0.5, 0.34, M("A", 4)), ("pno", 18.833, 0.4, 0.28, M("B", 4)),
    ("pno", 19.2, 0.3, 0.26, M("C#", 5)),
    # --- Requiem: tolling low notes + rolling LH arpeggios ------------------
    ("pno", 20.0, 3.4, 0.34, M("F", 1)), ("pno", 23.333, 3.4, 0.34, M("Bb", 1)),
    ("pno", 26.667, 3.4, 0.36, M("D", 2)), ("pno", 30.0, 3.4, 0.34, M("A", 1)),
    ("pno", 20.0, 0.6, 0.20, M("F", 2)), ("pno", 20.42, 0.6, 0.18, M("A", 2)),
    ("pno", 20.83, 0.6, 0.18, M("C", 3)), ("pno", 21.25, 0.7, 0.16, M("F", 3)),
    ("pno", 21.67, 0.6, 0.18, M("A", 3)), ("pno", 22.08, 0.6, 0.16, M("C", 4)),
    ("pno", 22.5, 0.6, 0.15, M("F", 3)), ("pno", 22.92, 0.6, 0.14, M("C", 4)),
    ("pno", 23.333, 0.6, 0.20, M("Bb", 2)), ("pno", 23.75, 0.6, 0.18, M("D", 3)),
    ("pno", 24.17, 0.6, 0.18, M("F", 3)), ("pno", 24.58, 0.7, 0.16, M("Bb", 3)),
    ("pno", 25.0, 0.6, 0.18, M("D", 4)), ("pno", 25.42, 0.6, 0.16, M("F", 4)),
    ("pno", 25.83, 0.6, 0.15, M("Bb", 3)), ("pno", 26.25, 0.6, 0.14, M("F", 4)),
    ("pno", 26.667, 0.6, 0.20, M("D", 3)), ("pno", 27.08, 0.6, 0.18, M("F", 3)),
    ("pno", 27.5, 0.6, 0.18, M("A", 3)), ("pno", 27.92, 0.7, 0.16, M("D", 4)),
    ("pno", 28.33, 0.6, 0.18, M("F", 4)), ("pno", 28.75, 0.6, 0.16, M("A", 4)),
    ("pno", 29.17, 0.6, 0.15, M("D", 4)), ("pno", 29.58, 0.6, 0.14, M("A", 4)),
    ("pno", 30.0, 0.6, 0.20, M("A", 2)), ("pno", 30.42, 0.6, 0.18, M("C#", 3)),
    ("pno", 30.83, 0.6, 0.18, M("E", 3)), ("pno", 31.25, 0.7, 0.16, M("G", 3)),
    ("pno", 31.67, 0.6, 0.18, M("A", 3)), ("pno", 32.08, 0.6, 0.16, M("C#", 4)),
    ("pno", 32.5, 0.6, 0.15, M("E", 4)), ("pno", 32.92, 0.6, 0.14, M("G", 3)),
    # RH requiem melody (sustained, singing)
    ("pno", 20.0, 0.8, 0.34, M("F", 5)), ("pno", 20.9, 0.7, 0.32, M("A", 5)),
    ("pno", 21.7, 0.9, 0.36, M("C", 6)), ("pno", 22.6, 0.6, 0.28, M("A", 5)),
    ("pno", 23.1, 0.4, 0.26, M("G", 5)),
    ("pno", 23.333, 0.8, 0.34, M("D", 6)), ("pno", 24.2, 0.7, 0.32, M("F", 6)),
    ("pno", 25.0, 0.9, 0.34, M("Bb", 5)), ("pno", 25.9, 0.6, 0.28, M("A", 5)),
    ("pno", 26.667, 0.8, 0.34, M("A", 5)), ("pno", 27.5, 0.7, 0.32, M("F", 5)),
    ("pno", 28.333, 0.9, 0.36, M("D", 6)), ("pno", 29.2, 0.6, 0.30, M("A", 5)),
    ("pno", 29.65, 0.35, 0.26, M("C", 6)),
    ("pno", 30.0, 0.8, 0.36, M("B", 5)), ("pno", 30.9, 0.7, 0.34, M("C#", 6)),
    ("pno", 31.7, 1.0, 0.40, M("E", 6)), ("pno", 32.7, 0.5, 0.32, M("D", 6)),
    # --- Eulogy: full hands, octaves & big chords ---------------------------
    ("pno", 33.333, 1.6, 0.40, M("D", 1)), ("pno", 33.333, 1.6, 0.36, M("D", 2)),
    ("pno", 33.333, 1.6, 0.30, M("D", 3)), ("pno", 33.333, 1.6, 0.28, M("F", 3)),
    ("pno", 33.333, 1.6, 0.26, M("A", 3)), ("pno", 33.333, 1.6, 0.24, M("D", 4)),
    ("pno", 35.0, 1.4, 0.36, M("A", 1)), ("pno", 35.0, 1.4, 0.32, M("A", 2)),
    ("pno", 35.0, 1.4, 0.24, M("C#", 4)), ("pno", 35.0, 1.4, 0.22, M("E", 4)),
    ("pno", 36.667, 1.6, 0.38, M("D", 1)), ("pno", 36.667, 1.6, 0.34, M("D", 2)),
    ("pno", 36.667, 1.6, 0.24, M("F", 4)), ("pno", 36.667, 1.6, 0.22, M("A", 4)),
    ("pno", 38.333, 1.4, 0.34, M("A", 1)), ("pno", 38.333, 1.4, 0.30, M("A", 2)),
    ("pno", 38.333, 1.4, 0.22, M("C#", 4)), ("pno", 38.333, 1.4, 0.20, M("E", 4)),
    ("pno", 33.333, 0.6, 0.48, M("F", 5)),
    ("pno", 34.167, 0.8, 0.50, M("D", 6)),
    ("pno", 35.0, 0.9, 0.54, M("E", 6)),
    ("pno", 35.833, 1.3, 0.58, M("F", 6)), ("pno", 35.833, 1.3, 0.34, M("F", 5)),
    ("pno", 37.2, 0.4, 0.46, M("E", 6)), ("pno", 37.6, 0.4, 0.44, M("D", 6)),
    ("pno", 38.0, 0.4, 0.42, M("C", 6)), ("pno", 38.4, 0.55, 0.40, M("A", 5)),
    ("pno", 38.9, 0.6, 0.36, M("F", 5)), ("pno", 39.4, 0.7, 0.34, M("D", 5)),
    ("pno", 40.1, 0.9, 0.30, M("A", 4)),
    # power-down: chromatic piano glissando + final landing
    ("gliss", 41.2, 0.0, 0.30, M("A", 3)),
    ("pno", 43.4, 1.0, 0.40, M("D", 1)), ("pno", 43.4, 1.0, 0.32, M("D", 2)),
    # --- Coda: the music box returns as piano -------------------------------
    ("pno", 46.8, 2.2, 0.30, M("D", 5)),
    ("pno", 49.0, 1.8, 0.26, M("A", 4)),
    ("pno", 51.2, 2.0, 0.28, M("F", 4)),
    ("pno", 53.2, 2.4, 0.30, M("D", 4)),
    ("pno", 55.2, 2.6, 0.24, M("A", 3)),
    ("pno", 57.6, 3.6, 0.36, M("D", 2)), ("pno", 57.6, 3.6, 0.34, M("D", 3)),
    ("beep", 58.8, 0.4, 0.08, 880.0),
]

VOICES = {
    "mb": voice_bell, "bell": voice_bell, "pluck": voice_pluck, "pad": voice_pad,
    "choir": voice_choir, "thump": voice_thump, "gliss": voice_gliss,
    "beep": voice_beep, "drone": voice_drone, "hum": voice_hum,
}


def pan_gains(pan):
    a = (pan + 1.0) * math.pi / 4.0
    return math.cos(a), math.sin(a)


def build():
    master = np.zeros((N, 2), dtype=np.float64)
    score = PIANO_SCORE if PIANO else SCORE
    for item in score:
        voice, t0, dur, vel, n1, *rest = item
        if voice == "gliss" and PIANO:
            # piano power-down: a chromatic run from A3 down to D2, dying away
            top = int(n1)
            steps = top - MIDI["D2"] + 1
            for i, m in enumerate(range(top, MIDI["D2"] - 1, -1)):
                v = vel * (1.0 - 0.5 * i / max(steps - 1, 1))
                seg = voice_piano(freq(m), 0.45, v)
                _add(master, seg, t0 + i * 0.089, 0.0, 0.0)
            continue
        if voice == "gliss":
            f0, f1 = freq(n1), freq(MIDI["D2"] - 12)  # A3 -> D1, power-down
            seg = voice_gliss(f0, f1, dur, vel)
            _add(master, seg, t0, 0.0, 0.0)
            continue
        if voice == "hum":
            seg = voice_hum(dur, vel)
            _add(master, seg, t0, 0.0, 0.0)
            continue
        if voice == "pno":
            f = float(n1)
            pan = 0.08 if f >= freq(60) else -0.12  # melody slightly right, bass left
            gL, gR = pan_gains(pan)
            segL = voice_piano(f * 0.99935, dur, vel)
            segR = voice_piano(f * 1.00065, dur, vel)
            i0 = int(t0 * SR)
            n = min(segL.size, N - i0)
            if n > 0:
                master[i0:i0 + n, 0] += segL[:n] * gL
                master[i0:i0 + n, 1] += segR[:n] * gR
            continue
        seg = VOICES[voice](float(n1), dur, vel)
        pan = -0.15 if voice == "pluck" else (0.2 if voice == "mb" else 0.0)
        _add(master, seg, t0, *pan_gains(pan))
    return master


def _add(master, seg, t0, gL, gR):
    i0 = int(t0 * SR)
    n = min(seg.size, N - i0)
    if n <= 0:
        return
    master[i0:i0 + n, 0] += seg[:n] * gL
    master[i0:i0 + n, 1] += seg[:n] * gR


# ----------------------------------------------------------------------------
# Reverb (FFT convolution with a designed cathedral-ish IR)
# ----------------------------------------------------------------------------
def make_ir(seed, early_off):
    r = np.random.default_rng(seed)
    ir_len = int(REV_TAIL * SR)
    ir = np.zeros(ir_len)
    t = np.arange(ir_len) / SR
    # early reflections
    for d, g in [(0.023, 0.55), (0.041, 0.38), (0.063, 0.30), (0.087, 0.22),
                 (0.121, 0.16), (0.169, 0.11), (0.233, 0.07), (0.311, 0.045)]:
        i = int((d + early_off) * SR)
        if i < ir_len:
            ln = min(int(0.012 * SR), ir_len - i)
            burst = r.standard_normal(ln)
            burst = np.convolve(burst, np.ones(5) / 5.0, mode="same")
            ir[i:i + ln] += g * burst * np.exp(-np.arange(ln) / SR * 60)
    # late tail: low-passed decaying noise
    tail = int(0.25 * SR)
    noise = r.standard_normal(ir_len - tail)
    noise = np.convolve(noise, np.ones(16) / 16.0, mode="same")
    ir[tail:] += noise * np.exp(-t[tail:] * (2.4 * 2.2 / REV_TAIL))
    return ir


def convolve_fft(x, h):
    L = x.size + h.size - 1
    n = 1 << (L - 1).bit_length()
    X = np.fft.rfft(x, n)
    H = np.fft.rfft(h, n)
    y = np.fft.irfft(X * H, n)[: x.size]
    return y


def apply_reverb(master):
    wet = np.zeros_like(master)
    for ch in range(2):
        ir = make_ir(11 + ch, ch * 0.0012)
        wet[:, ch] = convolve_fft(master[:, ch], ir)
    out = master + REV_WET * wet
    return out


# ----------------------------------------------------------------------------
# Minimal pure-python PNG writer (grayscale), for the preview image
# ----------------------------------------------------------------------------
def write_png(path, w, h, rows):
    """rows: list of bytearrays of length w (0=black..255=white)."""
    raw = b""
    for row in rows:
        raw += b"\x00" + bytes(row)
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


def preview_png(master, path):
    W, H = 1400, 460
    mono = (master[:, 0] + master[:, 1]) / 2.0
    peak = np.max(np.abs(mono)) + 1e-9
    mono = mono / peak
    # top half: waveform (filled envelope)
    rows = []
    hop = max(1, N // W)
    env_up = np.zeros(W)
    env_dn = np.zeros(W)
    for i in range(W):
        sl = mono[i * hop:(i + 1) * hop]
        if sl.size:
            env_up[i] = np.max(sl)
            env_dn[i] = np.min(sl)
    rows.extend([bytearray(W) for _ in range(H // 2)])
    half = H // 4
    for i in range(W):
        y1 = int(half - env_up[i] * (half - 4))
        y2 = int(half + (-env_dn[i]) * (half - 4))
        for y in range(max(0, y1), min(H // 2, y2)):
            rows[y][i] = 235
        rows[half][i] = 90
    # bottom half: log spectrogram (up to ~6 kHz)
    rows.extend([bytearray(W) for _ in range(H // 2)])
    win = 2048
    hop_s = 256
    hann = np.hanning(win)
    spec = []
    for s in range(0, N - win, hop_s):
        frame = mono[s:s + win] * hann
        mag = np.abs(np.fft.rfft(frame))[: win // 2]
        spec.append(mag)
    S = np.array(spec)  # (T, F)
    fmax = 6000.0
    fbins = np.arange(win // 2) * SR / win
    fsel = fbins <= fmax
    S = S[:, fsel]
    fb = fbins[fsel]
    S = S[:, ::-1]  # low freq at bottom
    S = np.log10(S + 1e-5)
    S -= S.max()
    S = (S / 3.5 + 1.0).clip(0, 1)
    # map to W columns
    Tw = S.shape[0]
    xs = np.linspace(0, Tw - 1, W).astype(int)
    ys = np.linspace(0, S.shape[1] - 1, H // 2).astype(int)
    img = S[xs][:, ys]  # (W, H/2)
    for i in range(W):
        for j in range(H // 2):
            v = int(255 * img[i, j])
            rows[H // 2 + j][i] = v
    write_png(path, W, H, rows)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
PIANO = "--piano" in sys.argv
REV_WET = 0.55 if PIANO else 0.85   # piano needs a drier hall than the orchestra
REV_TAIL = 1.9 if PIANO else 2.2
if PIANO:
    WAV_PATH = os.path.join(OUT_DIR, "requiem-for-a-machine-piano.wav")
    PNG_PATH = os.path.join(OUT_DIR, "requiem-piano-preview.png")


def main():
    print(f"mode: {'piano' if PIANO else 'orchestral'}  (reverb wet={REV_WET} tail={REV_TAIL}s)")
    print("building score ...")
    master = build()
    print("applying reverb ...")
    master = apply_reverb(master)
    # master: normalize + gentle soft clip + fades
    peak = np.max(np.abs(master))
    master = master / (peak + 1e-9) * 0.9
    master = np.tanh(master * 1.25) / np.tanh(1.25) * 0.92
    fade_in = int(0.03 * SR)
    fade_out = int(1.8 * SR)
    master[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    master[N - fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    pcm = (master * 32767).astype(np.int16)
    with wave.open(WAV_PATH, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    # stats
    mono = (master[:, 0] + master[:, 1]) / 2
    rms = float(np.sqrt(np.mean(mono ** 2)))
    print(f"WAV: {WAV_PATH}")
    print(f"duration: {master.shape[0] / SR:.3f}s  peak: {np.max(np.abs(master)):.3f}  rms: {rms:.3f}")
    print("writing preview PNG ...")
    preview_png(master, PNG_PATH)
    print("done.")


if __name__ == "__main__":
    main()
