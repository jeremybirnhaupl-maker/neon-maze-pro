#!/usr/bin/env python3
"""
N E O N   M A Z E  -  P R O
===========================
Flucht aus dem Neon-Labyrinth. Zwei Modi:
  VIRUS  - sammle 20 Kristalle, lege Drohnen mit EMP / Fallen / Koedern lahm, finde das Portal.
  SCHILD - pro Level 1 Virus mehr: bleib 8 s in der Naehe eines Virus, dann startet seine Loeschung
           (30 s). Sind alle Viren geloescht, oeffnet sich das Portal.
Dazu: Skins (36 Farben, 3 Stile), PC- und Handy-Steuerung, selbst erzeugte Musik und Sounds.

Installation:   pip install pygame
Start:          python neon_maze_pro.py        (Handy-Steuerung: --handy  oder in den Einstellungen)

Steuerung PC  (alle Tasten auch im Menue unter STEUERUNG)
    WASD / Pfeiltasten   bewegen          LEERTASTE / SHIFT / RECHTSKLICK   Dash
    LINKSKLICK / E / F   Schuss           Q  EMP-Puls (Schildwelle)         R  Falle         C  Koeder
    P / ESC Pause   TAB / M Karte   N Ton an/aus   F11 Vollbild   F1 Admin-Konsole
Steuerung HANDY: Joystick links (Finger halten + ziehen), grosse Buttons rechts, Schuss zielt automatisch.
"""
import array
import colorsys
import itertools
import json
import math
import os
import random
import subprocess
import sys
import threading
import time
from collections import deque


def pause():
    """Fenster offen halten, damit man Fehlermeldungen lesen kann."""
    try:
        input("\nDrücke ENTER zum Schließen ...")
    except Exception:
        pass


def _install_pygame():
    import importlib
    for pkg in ("pygame", "pygame-ce"):
        print(f"Installiere {pkg} ...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            importlib.invalidate_caches()
            import pygame as _pg  # noqa: F401
            return True
        except Exception as exc:
            print(f"  {pkg} fehlgeschlagen: {exc}")
    return False


try:
    import pygame
except ImportError:
    print("pygame ist nicht installiert - versuche automatische Installation ...")
    if _install_pygame():
        import pygame
    else:
        print("\nFEHLER: pygame konnte nicht installiert werden.")
        print(f"Dein Python: {sys.version}")
        print("Tipp: Für sehr neue Python-Versionen (3.13 / 3.14) gibt es oft noch kein")
        print("pygame. Installiere dann Python 3.12 von python.org (Haken bei")
        print("'Add Python to PATH' setzen) und starte das Spiel erneut.")
        pause()
        sys.exit(1)

# ============================================================== Konstanten
W, H = 1280, 720
TS = 44                       # Kachelgröße in Pixeln
FPS = 60
BG = (4, 4, 12)
AMBIENT = (20, 20, 34)        # Grundhelligkeit im Dunkeln
SPEED, DASH_SPEED = 235.0, 700.0
DASH_TIME, DASH_CD = 0.18, 0.9
START_LIVES = 3
MAX_LIVES = 4                 # mehr als 4 Herzen kann man nie haben
SHOT_CD, DISABLE_TIME = 10.0, 15.0   # Schuss-Abklingzeit / Dauer der Lahmlegung
CRYSTAL_GOAL = 20            # so viele Kristalle braucht man, bevor das Portal aufgeht
REPAIR_TIME = 60.0           # Drohnen mit REBOOT FAILURE reparieren sich nach dieser Zeit selbst
EMP_CD, EMP_RADIUS, EMP_TIME = 18.0, 6.5 * TS, 10.0          # EMP-Puls: Abklingzeit, Reichweite, Lahmlegung
TRAP_CD, TRAP_MAX, TRAP_TIME, TRAP_RADIUS = 4.0, 3, 12.0, 2.4 * TS   # EMP-Fallen
DECOY_CD, DECOY_TIME = 22.0, 9.0                             # Koeder-Hologramm
ENERGY_MAX, BLOCK_COST, ENERGY_REGEN = 100.0, 30.0, 6.0      # Schild-Modus: Energie
SCAN_TIME, SCAN_RADIUS, DELETE_TIME = 8.0, 3.0 * TS, 30.0    # Schild-Modus: Scan-Dauer, Reichweite, Löschdauer
IS_MOBILE = ("ANDROID_ARGUMENT" in os.environ or sys.platform == "android"
             or "--handy" in sys.argv or "--mobile" in sys.argv)
MENU_ITEMS = (("SPIELEN", "play"), ("SKINS", "skins"), ("STEUERUNG", "keys"),
              ("EINSTELLUNGEN", "settings"), ("BESTENLISTE", "board"), ("BEENDEN", "quit"))
SKIN_STYLES = ("KLASSISCH", "STERN", "KRAKE")
SKIN_COLORS = (
    ("ROT", (225, 40, 55)), ("KARMIN", (190, 20, 70)), ("BLUTORANGE", (255, 80, 25)),
    ("ORANGE", (255, 125, 30)), ("BERNSTEIN", (255, 175, 30)), ("GOLD", (255, 205, 45)),
    ("GELB", (255, 240, 70)), ("LIMETTE", (170, 255, 60)), ("NEON-GRÜN", (57, 255, 20)),
    ("GRÜN", (50, 230, 90)), ("OLIV", (150, 170, 40)), ("MINT", (90, 255, 180)),
    ("TÜRKIS", (30, 220, 200)), ("PETROL", (20, 140, 150)), ("CYAN", (60, 225, 255)),
    ("HIMMELBLAU", (90, 170, 255)), ("BLAU", (50, 100, 255)), ("MARINE", (40, 70, 150)),
    ("INDIGO", (90, 60, 230)), ("VIOLETT", (150, 70, 240)), ("LILA", (190, 90, 255)),
    ("MAGENTA", (240, 60, 220)), ("PINK", (255, 95, 170)), ("ROSA", (255, 160, 200)),
    ("KORALLE", (255, 110, 100)), ("LACHS", (255, 150, 120)), ("BRAUN", (160, 95, 50)),
    ("WEISS", (240, 245, 255)), ("SILBER", (180, 190, 205)), ("GRAU", (110, 115, 135)),
    ("EISBLAU", (170, 220, 255)), ("RUBIN", (220, 20, 90)), ("SMARAGD", (20, 200, 120)),
    ("REGENBOGEN", None), ("FEUER", None), ("EIS-PULS", None),
)
SKIN_SHORT = {"REGENBOGEN": "RGB", "FEUER": "FEUER", "EIS-PULS": "EIS"}
# Tastenbelegung (eigene Kategorie im Menue): Gruppen -> (Tasten, Beschreibung)
KEYS_PC = (
    ("BEWEGUNG", (110, 230, 255), ((["W", "A", "S", "D"], "Bewegen"), (["PFEILE"], "Bewegen"),
                                   (["SPACE"], "Dash"), (["SHIFT"], "Dash"),
                                   (["RECHTSKLICK"], "Dash zur Maus"))),
    ("KAMPF & GADGETS", (255, 205, 90), ((["LINKSKLICK"], "Schuss zur Maus"), (["E"], "Schuss"),
                                         (["F"], "Schuss"), (["Q"], "EMP / Welle"),
                                         (["R"], "Falle legen"), (["C"], "Köder legen"))),
    ("SPIEL & MENÜ", (255, 130, 230), ((["P", "ESC"], "Pause"), (["TAB", "M"], "Große Karte"),
                                       (["N"], "Ton an/aus"), (["F11"], "Vollbild"),
                                       (["ALT", "ENTER"], "Vollbild"), (["F1"], "Admin-Konsole"))),
)
# Touch-Buttons: Name, Mitte x, Mitte y, Radius, Beschriftung, Farbe
TOUCH_BTNS = (("dash", W - 120, H - 130, 70, "DASH", (90, 255, 255)),
              ("shoot", W - 270, H - 90, 52, "SCHUSS", (255, 120, 230)),
              ("emp", W - 100, H - 290, 46, "EMP", (255, 205, 90)),
              ("trap", W - 235, H - 225, 46, "FALLE", (255, 170, 70)),
              ("decoy", W - 370, H - 170, 46, "KÖDER", (90, 230, 255)),
              ("pause", 376, 44, 26, "II", (170, 175, 255)),
              ("map", 904, 44, 26, "MAP", (170, 175, 255)))
PICKUP_INFO = {                     # Power-Ups: Name, Farbe
    "shield": ("SCHILD", (90, 220, 255)),
    "magnet": ("MAGNET", (255, 100, 225)),
    "overclock": ("OVERCLOCK", (255, 225, 70)),
    "heart": ("HERZ", (255, 80, 130)),
}
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "neon_maze_highscore.json")          # alter Rekord (wird noch gelesen)
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "neon_maze_data.json")               # Einstellungen + Bestenliste
MAX_DRONES = 150
SPREAD_CAP = 40       # Schild-Modus: so viele Viren breiten sich maximal von selbst aus
REBOOT_FAIL = 0.25    # Chance: Drohne bleibt nach dem Reboot dauerhaft offline
LIFE_EVERY = 5000     # Extraleben alle X Punkte

MAP_SIZES = [("Klein", 0.7), ("Normal", 1.0), ("Groß", 1.4), ("Riesig", 1.9)]
# Schwierigkeitsstufen: count = Drohnen-Menge, speed = Tempo, sight = Sichtweite,
# lives = Start-Leben, fail = Chance auf Reboot-Defekt, heart = Chance auf Herz-Item pro Karte,
# life_every = Extraleben alle X Punkte, spread = Sekunden bis ein neuer Virus (Schild-Modus),
# score = Punkte-Faktor
DIFFICULTIES = [
    dict(name="Einfach", count=0.6, speed=0.85, sight=0.80, lives=4, fail=0.40, heart=0.95,
         life_every=4000, spread=45.0, score=0.75, col=(120, 255, 160),
         info="Wenig & langsame Drohnen, 4 Leben, viele Herzen"),
    dict(name="Mittel", count=1.0, speed=1.0, sight=1.0, lives=3, fail=0.25, heart=0.70,
         life_every=5000, spread=32.0, score=1.0, col=(120, 200, 255),
         info="Ausgewogen: 3 Leben, normale Drohnen"),
    dict(name="Schwer", count=1.5, speed=1.15, sight=1.15, lives=3, fail=0.15, heart=0.50,
         life_every=6500, spread=22.0, score=1.25, col=(255, 190, 90),
         info="Mehr & schnellere Drohnen, weniger Herzen, 3 Leben"),
    dict(name="HARDCORE", count=2.1, speed=1.30, sight=1.30, lives=1, fail=0.05, heart=0.30,
         life_every=9000, spread=14.0, score=2.0, col=(255, 70, 90),
         info="Drohnen-Schwarm, sehr schnell, nur 1 Leben, kaum Herzen"),
]
MODES = [("VIRUS", (255, 90, 100)), ("SCHILD", (90, 220, 255))]
DEFAULT_OPT = {"name": "SPIELER", "volume": 70, "mapsize": 2, "difficulty": 1, "mode": 0,
               "bloom": True, "scanlines": True, "shake": True, "fullscreen": False,
               "music": 55, "mute": False, "control": 1 if IS_MOBILE else 0, "skin_color": 0, "skin_style": 0}
SETTING_KEYS = ["name", "control", "music", "volume", "mute", "mapsize", "difficulty", "bloom",
                "scanlines", "shake", "fullscreen", "back"]
SETTING_LABELS = {"name": "Spielername", "volume": "Effekte", "music": "Musik", "mute": "Alles stumm",
                  "control": "Steuerung", "mapsize": "Kartengröße",
                  "difficulty": "Schwierigkeit", "bloom": "Bloom-Glow",
                  "scanlines": "Scanlines", "shake": "Screenshake",
                  "fullscreen": "Vollbild", "back": "ZURÜCK"}

# Paletten: Virus = (Körper, Stacheln, Rand, Kern)   Schild = (Füllung, Rand, Innen, Innenrand)
PAL_VIRUS_P = ((225, 30, 45), (255, 85, 95), (255, 150, 150), (100, 0, 18))
PAL_VIRUS_DASH = ((255, 120, 70), (255, 175, 130), (255, 150, 150), (100, 0, 18))
PAL_VIRUS_E = ((215, 35, 55), (255, 95, 105), (255, 160, 160), (90, 0, 18))
PAL_VIRUS_E_CHASE = ((255, 60, 75), (255, 140, 120), (255, 200, 190), (130, 0, 25))
PAL_VIRUS_H = ((175, 40, 215), (225, 120, 255), (240, 180, 255), (70, 0, 100))
PAL_VIRUS_H_CHASE = ((220, 60, 250), (255, 150, 255), (255, 210, 255), (100, 0, 140))
PAL_SHIELD_E = ((40, 110, 230), (215, 240, 255), (18, 55, 150), (120, 200, 255))
PAL_SHIELD_E_CHASE = ((75, 175, 255), (215, 240, 255), (18, 55, 150), (120, 200, 255))
PAL_SHIELD_H = ((130, 70, 235), (225, 215, 255), (45, 20, 120), (190, 150, 255))
PAL_SHIELD_H_CHASE = ((170, 110, 255), (235, 225, 255), (45, 20, 120), (205, 170, 255))
PAL_SHIELD_P = ((70, 225, 255), (235, 255, 255), (10, 80, 130), (150, 240, 255))
PAL_SHIELD_P_DASH = ((255, 215, 100), (255, 250, 220), (130, 80, 10), (255, 230, 150))

# Admin-Konsole
CMD_ALIAS = {"unsterblich": "god", "gott": "god", "drohnen": "spawn", "flut": "endlos",
             "lahm": "disable", "lahmlegen": "disable", "wecken": "enable", "weg": "kill",
             "killall": "kill", "einfrieren": "freeze", "lives": "leben", "shield": "schild",
             "overclock": "oc", "tempo": "speed", "geist": "noclip", "light": "licht",
             "karte": "reveal", "crystals": "kristalle", "score": "punkte",
             "teleport": "tp", "weiter": "skip", "slowmo": "zeit", "cls": "clear",
             "keincd": "nocd", "nocooldown": "nocd", "cooldown": "nocd",
             "schusscd": "noshot", "dashcd": "nodash", "herz": "leben", "herzen": "leben",
             "help": "hilfe", "?": "hilfe", "close": "exit", "quit": "exit"}
CMD_NAMES = ["god", "spawn", "endlos", "disable", "enable", "kill", "freeze", "leben",
             "schild", "magnet", "oc", "alle", "speed", "nocd", "noshot", "nodash", "noclip", "licht",
             "reveal", "kristalle", "punkte", "tp", "skip", "level", "zeit", "status", "portal",
             "reset", "clear", "hilfe", "exit"]
CMD_SAFE = ("hilfe", "status", "clear", "exit")
HELP_LINES = (
    "god [an/aus]      unsterblich            spawn [n]       n Drohnen spawnen",
    "endlos [an/aus]   Drohnen spawnen endlos  disable [s]     alle Drohnen lahmlegen",
    "enable            wecken + reparieren     kill            alle Drohnen löschen",
    "freeze [an/aus]   Drohnen dauerhaft lahm  leben [n]       Leben setzen (max 4)",
    "schild | magnet [s] | oc [s] | alle       Power-Ups geben",
    "nocd [an/aus]     KEIN Cooldown (Dash + Schuss)",
    "noshot [an/aus]   nur Schuss-Cooldown aus  nodash [an/aus] nur Dash-Cooldown aus",
    "speed [x]         Spielertempo (0.2-6)    noclip [an/aus] durch Wände laufen",
    "licht [an/aus]    Vollhelligkeit          reveal          Karte aufdecken",
    "kristalle         alle einsammeln         punkte [n]      Punkte addieren",
    "portal            Portal sofort öffnen (ohne die 20 Kristalle)",
    "tp exit|start|x y teleportieren            skip            Level überspringen",
    "level [n]         zu Level n springen     zeit [x]        Zeitlupe (0.1-1.5)",
    "status | reset | clear | exit",
    "Aliase: unsterblich, drohnen, lahm, wecken, weg, geist, karte, keincd ...  (TAB = ergänzen)",
    "ACHTUNG: Nach einem Befehl zählt der Lauf nicht für die Bestenliste.",
)


def hsv(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return int(r * 255), int(g * 255), int(b * 255)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def mix(a, b, f):
    """Mischt zwei Farben (f = 0 -> a, f = 1 -> b)."""
    return tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))


# ============================================================== Sound
RATE = 22050
TAU = math.pi * 2


def _osc(kind, ph):
    """Oszillator: ph = Phase in Umdrehungen."""
    if kind == "sine":
        return math.sin(TAU * ph)
    x = ph % 1.0
    if kind == "saw":
        return 2.0 * x - 1.0
    if kind == "square":
        return 1.0 if x < 0.5 else -1.0
    if kind == "tri":
        return 4.0 * abs(x - 0.5) - 1.0
    if kind == "fm":
        return math.sin(TAU * ph + 2.2 * math.sin(TAU * ph * 2.0))
    return math.sin(TAU * ph)


def synth(notes, vol=0.4, wave="sine", noise=0.0, attack=0.004, decay=1.3,
          echo=0.0, vib=0.0, sub=0.0, nlp=None):
    """Rendert Toene zu 16-Bit-Samples. notes = [(Hz_start, Hz_ende, Sekunden), ...]"""
    buf, ph, lpv = [], 0.0, 0.0
    na = max(1, int(RATE * attack))
    for f0, f1, dur in notes:
        n = max(1, int(RATE * dur))
        for i in range(n):
            k = i / n
            f = f0 + (f1 - f0) * k
            if vib:
                f *= 1.0 + vib * math.sin(i * 0.0125)
            ph += f / RATE
            s = _osc(wave, ph)
            if sub:
                s += sub * math.sin(TAU * ph * 0.5)
            if noise:
                r = random.uniform(-1, 1)
                if nlp:                                   # Rauschen mit wandernder Filterung
                    lpv += (r - lpv) * (nlp[0] + (nlp[1] - nlp[0]) * k)
                    r = lpv * 2.4
                s = s * (1 - noise) + r * noise
            buf.append(vol * s * min(1.0, i / na) * (1 - k) ** decay)
    if echo:
        d = int(RATE * 0.11)
        out = buf + [0.0] * (2 * d)
        for i, v in enumerate(buf):
            out[i + d] += v * echo
            out[i + 2 * d] += v * echo * echo
        buf = out
    return array.array("h", [int(32767 * max(-1.0, min(1.0, v))) for v in buf])


def _hz(n):
    return 440.0 * 2.0 ** ((n - 69) / 12.0)


def render_track(kind):
    """Rendert einen nahtlos loopenden 16-Takte-Song (reines Python, laeuft im Hintergrund).
    kind = "game": treibender Synthwave-Beat   |   "menu": ruhige Glocken-Atmosphaere"""
    game = kind == "game"
    bpm = 120 if game else 84
    spb = int(RATE * 60.0 / bpm / 4)                   # Samples pro 16tel-Schritt
    total = spb * 256                                  # 16 Takte
    bar = spb * 16
    sine = math.sin
    mix = [0.0] * total                                # Klangbett: Pad, Bass, Arpeggio
    fx = [0.0] * total                                 # Lead / Glocken (bekommen Echo)
    drums = [0.0] * total
    chords = ((45, (57, 60, 64)), (41, (53, 57, 60)), (48, (55, 60, 64)), (43, (55, 59, 62)),
              (45, (57, 60, 64)), (38, (57, 62, 65)), (41, (53, 57, 60)), (40, (56, 59, 64)))

    # ---- Pad (je 2 Takte ein Akkord, zwei leicht verstimmte Sinus pro Ton)
    a = r = int(RATE * 0.5)
    pv = 0.055 if game else 0.085
    for ci, (_root, tones) in enumerate(chords):
        st, ln = ci * 2 * bar, 2 * bar
        for tn in tones:
            hz = _hz(tn)
            i1, i2 = hz / RATE, hz * 1.005 / RATE
            p1 = p2 = 0.0
            for i in range(ln):
                p1 += i1
                p2 += i2
                e = i / a if i < a else 1.0
                if ln - i < r:
                    e = min(e, (ln - i) / r)
                mix[(st + i) % total] += (sine(TAU * p1) + sine(TAU * p2)) * pv * e

    # ---- Bass
    def bass_note(st, ln, hz, vol):
        inc, ph = hz / RATE, 0.0
        for i in range(ln):
            ph += inc
            s = sine(TAU * ph) * 0.75 + ((ph % 1.0) * 2 - 1) * 0.22
            e = 1.0 - 0.5 * i / ln
            if i < 120:
                e *= i / 120
            if ln - i < 220:
                e *= (ln - i) / 220
            mix[(st + i) % total] += s * e * vol

    for b in range(16):
        root = chords[b // 2][0]
        if game:
            for k, iv in enumerate((0, 0, 12, 0, 0, 12, 7, 0)):
                bass_note(b * bar + k * 2 * spb, int(spb * 1.8), _hz(root + iv), 0.20)
        else:
            bass_note(b * bar, bar - 400, _hz(root), 0.16)

    # ---- Arpeggio (Game: Square-Pluck) / Glocken (Menue)
    def pluck(buf, st, ln, hz, vol, duty=0.4, half=0.07):
        inc, ph, e = hz / RATE, 0.0, 1.0
        kk = 0.5 ** (1.0 / (RATE * half))
        for i in range(ln):
            ph += inc
            buf[(st + i) % total] += (1.0 if (ph % 1.0) < duty else -1.0) * e * vol
            e *= kk

    def bell(buf, st, ln, hz, vol):
        inc, ph, e = hz / RATE, 0.0, 1.0
        kk = 0.5 ** (1.0 / (RATE * 0.45))
        for i in range(ln):
            ph += inc
            buf[(st + i) % total] += (sine(TAU * ph) + 0.4 * sine(TAU * ph * 2.76)
                                      + 0.2 * sine(TAU * ph * 5.4)) * e * vol
            e *= kk

    for step in range(256):
        tones = chords[step // 32][1]
        if game:
            seq = (tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 24)
            pat = (0, 1, 2, 3, 2, 1, 3, 2)
            acc = 1.5 if step % 4 == 0 else 1.0
            pluck(mix, step * spb, int(spb * 2.5), _hz(seq[pat[step % 8]]), 0.040 * acc)
        elif step % 2 == 0:
            seq = (tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 24, tones[2] + 24)
            pat = (0, 1, 2, 3, 2, 4, 3, 1)
            bell(fx, step * spb, int(spb * 6), _hz(seq[pat[(step // 2) % 8]]), 0.030)

    # ---- Lead-Melodie (Phrasen je 2 Takte: Schritt, MIDI-Note, Laenge in 16teln)
    phrases = (
        ((0, 76, 4), (4, 72, 2), (6, 74, 2), (8, 76, 4), (12, 79, 4), (16, 76, 4), (20, 74, 2), (22, 72, 2), (24, 69, 8)),
        ((0, 77, 4), (4, 74, 2), (6, 72, 2), (8, 74, 4), (12, 77, 4), (16, 81, 4), (20, 79, 2), (22, 77, 2), (24, 74, 8)),
        ((0, 76, 4), (4, 79, 2), (6, 76, 2), (8, 72, 4), (12, 76, 4), (16, 79, 4), (20, 76, 2), (22, 74, 2), (24, 72, 8)),
        ((0, 74, 4), (4, 71, 2), (6, 74, 2), (8, 79, 4), (12, 74, 4), (16, 71, 4), (20, 74, 2), (22, 71, 2), (24, 67, 4), (28, 71, 4)),
        ((0, 76, 4), (4, 72, 2), (6, 74, 2), (8, 76, 4), (12, 81, 4), (16, 79, 4), (20, 76, 2), (22, 74, 2), (24, 72, 8)),
        ((0, 74, 4), (4, 77, 2), (6, 76, 2), (8, 74, 4), (12, 81, 4), (16, 77, 4), (20, 76, 2), (22, 74, 2), (24, 72, 8)),
        ((0, 81, 4), (4, 77, 2), (6, 79, 2), (8, 77, 4), (12, 72, 4), (16, 77, 4), (20, 74, 2), (22, 72, 2), (24, 69, 8)),
        ((0, 76, 4), (4, 80, 2), (6, 83, 2), (8, 80, 4), (12, 76, 4), (16, 71, 4), (20, 76, 2), (22, 80, 2), (24, 83, 8)),
    )

    def lead(buf, st, ln, hz, vol):
        ph = ph2 = 0.0
        for i in range(ln):
            f = hz * (1.0 + (0.004 * sine(i * 0.0016) if i > 3000 else 0.0))
            ph += f / RATE
            ph2 += f * 1.004 / RATE
            s = ((ph % 1.0) * 2 - 1) * 0.5 + (0.25 if (ph2 % 1.0) < 0.5 else -0.25)
            e = 1.0 - 0.35 * i / ln
            if i < 90:
                e *= i / 90
            if ln - i < 300:
                e *= (ln - i) / 300
            buf[(st + i) % total] += s * e * vol

    for pi, ph_notes in enumerate(phrases):
        for s0, note, ln in ph_notes:
            st = (pi * 32 + s0) * spb
            if game:
                lead(fx, st, int(ln * spb * 0.93), _hz(note), 0.075 if pi in (0, 1, 4) else 0.115)
            else:
                bell(fx, st, int(spb * 5), _hz(note - 12), 0.042)

    # ---- Schlagzeug
    def kick(st, vol):
        n, ph = int(RATE * 0.22), 0.0
        for i in range(n):
            k = i / n
            ph += (48 + 110 * (1 - k) ** 3) / RATE
            drums[(st + i) % total] += sine(TAU * ph) * vol * (1 - k) ** 1.5

    def snare(st, vol):
        n, ph = int(RATE * 0.16), 0.0
        for i in range(n):
            k = i / n
            ph += 190.0 / RATE
            drums[(st + i) % total] += (random.uniform(-1, 1) * 0.7 + sine(TAU * ph) * 0.5) * vol * (1 - k) ** 1.8

    def hat(st, vol, dur=0.04):
        n, prev = int(RATE * dur), 0.0
        for i in range(n):
            k = i / n
            r = random.uniform(-1, 1)
            drums[(st + i) % total] += (r - prev) * vol * (1 - k) ** 2
            prev = r

    if game:
        dn = int(RATE * 0.2)                                   # Sidechain-Pumpen auf jeden Schlag
        for b in range(64):
            st = b * 4 * spb
            for j in range(dn):
                mix[(st + j) % total] *= 0.45 + 0.55 * (j / dn) ** 1.5
            kick(st, 0.50)
        for b in range(16):
            snare(b * bar + 4 * spb, 0.17)
            snare(b * bar + 12 * spb, 0.17)
            for s in range(16):
                if s % 4 == 2:
                    hat(b * bar + s * spb, 0.045, 0.05 if s != 14 else 0.12)
                elif (b % 8) >= 4 and s % 2 == 1:
                    hat(b * bar + s * spb, 0.022)
    else:
        for b in range(16):
            kick(b * bar, 0.22)
            kick(b * bar + 8 * spb, 0.14)

    # ---- Mischen (Echo auf Lead/Glocken, punktierte Achtel) und in 16 Bit wandeln
    d = 3 * spb
    peak = 0.001
    for i in range(total):
        v = mix[i] + drums[i] + fx[i] + 0.38 * fx[i - d] + 0.2 * fx[i - 2 * d] + 0.1 * fx[i - 3 * d]
        mix[i] = v
        if v > peak:
            peak = v
        elif -v > peak:
            peak = -v
    sc = 0.86 / peak
    return array.array("h", [int(32767 * max(-1.0, min(1.0, v * sc))) for v in mix])


class Sfx:
    """Synthetisiert alle Sounds und die Musik selbst - keine Dateien noetig."""

    def __init__(self, volume=0.7, music=0.55, mute=False):
        self.ok = False
        self.volume, self.music_vol, self.mute = volume, music, mute
        self.snd, self.tracks, self._raw, self._last = {}, {}, {}, {}
        self.want, self.cur, self.duck, self.cur_vol = "menu", None, 1.0, 0.0
        self.music_ch = None
        self.chans = 1
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            self.chans = pygame.mixer.get_init()[2]
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(1)
            self.music_ch = pygame.mixer.Channel(0)
            self.ok = True
            self._build()
            threading.Thread(target=self._gen_music, daemon=True).start()
        except Exception:
            self.ok = False

    def _mk(self, arr):
        if self.chans == 2:
            st = array.array("h", [0]) * (len(arr) * 2)
            st[0::2] = arr
            st[1::2] = arr
            arr = st
        return pygame.mixer.Sound(buffer=arr.tobytes())

    def _build(self):
        S, mk = self.snd, lambda *a, **k: self._mk(synth(*a, **k))
        S["pickup"] = mk([(880, 1320, 0.07), (1320, 1760, 0.14)], 0.26, "fm", echo=0.35, decay=1.6)
        for i, f in enumerate((659, 740, 880, 988, 1109)):      # Kristall-Tonleiter: Combo klingt hoeher
            S[f"crystal{i + 1}"] = mk([(f, f * 1.5, 0.05), (f * 1.5, f * 2, 0.17)], 0.25, "fm", echo=0.32, decay=1.5)
        S["dash"] = mk([(900, 180, 0.2)], 0.30, "saw", noise=0.7, nlp=(0.55, 0.08), decay=1.0)
        S["hit"] = mk([(190, 40, 0.5)], 0.50, "square", noise=0.45, decay=1.2, sub=0.5)
        S["win"] = mk([(523, 523, 0.09), (659, 659, 0.09), (784, 784, 0.09), (1047, 1047, 0.09),
                       (784, 784, 0.06), (1047, 1047, 0.38)], 0.28, "tri", echo=0.4, decay=0.7)
        S["lose"] = mk([(392, 330, 0.25), (330, 262, 0.25), (262, 196, 0.25), (196, 98, 0.7)],
                       0.36, "saw", echo=0.3, decay=0.9)
        S["blip"] = mk([(660, 880, 0.045)], 0.20, "square", decay=0.8)
        S["select"] = mk([(660, 660, 0.05), (990, 990, 0.12)], 0.24, "square", decay=0.9)
        S["shoot"] = mk([(2200, 260, 0.22)], 0.26, "saw", noise=0.12, echo=0.2)
        S["emp"] = mk([(300, 1100, 0.18)], 0.28, "fm", noise=0.25, echo=0.3)
        S["emp_big"] = mk([(70, 1400, 0.5)], 0.45, "fm", noise=0.35, echo=0.45, decay=1.0, sub=0.6)
        S["power"] = mk([(500, 800, 0.08), (800, 1500, 0.14)], 0.30, "fm", echo=0.3)
        S["fail"] = mk([(420, 30, 0.9)], 0.38, "saw", noise=0.55)
        S["reboot"] = mk([(300, 520, 0.07), (520, 820, 0.09)], 0.20, "square")
        S["repair"] = mk([(440, 440, 0.07), (554, 554, 0.07), (659, 659, 0.07), (880, 880, 0.22)],
                         0.22, "tri", echo=0.3, decay=0.8)
        S["heart"] = mk([(600, 900, 0.10), (900, 1300, 0.10), (1300, 1700, 0.16)], 0.28, "fm", echo=0.3)
        S["bash"] = mk([(200, 50, 0.22)], 0.50, "square", noise=0.45, sub=0.5)
        S["block"] = mk([(1400, 500, 0.25)], 0.30, "fm", noise=0.1, echo=0.3)
        S["unlock"] = mk([(392, 392, 0.1), (494, 494, 0.1), (587, 587, 0.1), (784, 784, 0.1),
                          (988, 988, 0.1), (1175, 1175, 0.45)], 0.30, "fm", echo=0.5, decay=0.9)
        S["locked"] = mk([(160, 160, 0.09), (120, 120, 0.15)], 0.30, "square", decay=0.6)
        S["trap_set"] = mk([(1200, 600, 0.05), (500, 900, 0.08)], 0.22, "square")
        S["trap"] = mk([(1800, 120, 0.35)], 0.38, "saw", noise=0.5, nlp=(0.6, 0.1), echo=0.25)
        S["decoy"] = mk([(500, 900, 0.08), (900, 500, 0.08), (500, 900, 0.08), (900, 1200, 0.14)],
                        0.22, "fm", vib=0.02)
        S["alert"] = mk([(600, 900, 0.07), (900, 600, 0.09)], 0.18, "square")
        S["heartbeat"] = mk([(75, 40, 0.1), (60, 35, 0.14)], 0.55, "sine", decay=1.0)
        S["delete_start"] = mk([(300, 900, 0.1), (900, 300, 0.14), (300, 1200, 0.2)], 0.28, "fm", echo=0.35)
        S["delete_done"] = mk([(392, 392, 0.07), (523, 523, 0.07), (659, 659, 0.07), (784, 784, 0.07),
                               (1047, 1047, 0.3)], 0.30, "tri", echo=0.5, decay=0.8)

    def _gen_music(self):
        for name in ("menu", "game"):
            try:
                self._raw[name] = render_track(name)
            except Exception:
                pass

    def play(self, name, vol=1.0):
        if not self.ok or self.mute or self.volume <= 0 or name not in self.snd:
            return
        now = time.time()
        if now - self._last.get(name, 0.0) < 0.04:               # gleichen Sound nicht spammen
            return
        self._last[name] = now
        s = self.snd[name]
        s.set_volume(clamp(self.volume * vol, 0.0, 1.0))
        s.play()

    def set_mute(self, v):
        self.mute = v

    def update(self, dt):
        """Hauptthread: fertige Musik uebernehmen, Lied wechseln, Lautstaerke weich anpassen."""
        if not self.ok:
            return
        for name, raw in list(self._raw.items()):
            if name not in self.tracks:
                try:
                    self.tracks[name] = self._mk(raw)
                except Exception:
                    self.tracks[name] = None
        if self.want != self.cur and self.tracks.get(self.want):
            try:
                self.music_ch.play(self.tracks[self.want], loops=-1, fade_ms=900)
            except Exception:
                pass
            self.cur = self.want
        target = 0.0 if self.mute else self.music_vol * 0.6 * self.duck
        self.cur_vol += (target - self.cur_vol) * min(1.0, dt * 5.0)
        try:
            self.music_ch.set_volume(clamp(self.cur_vol, 0.0, 1.0))
        except Exception:
            pass


# ============================================================== Level
class Level:
    DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

    def __init__(self, number, populate=True, size=1.0, enemy_mult=1.0, heart_chance=0.0):
        self.n = number
        self.cols = clamp(int((14 + 3 * number) * size), 6, 50)
        self.rows = clamp(int((9 + 2 * number) * size), 5, 34)
        self.tw, self.th = 2 * self.cols + 1, 2 * self.rows + 1
        self.grid = [[1] * self.tw for _ in range(self.th)]
        self.hue0 = (0.5 + number * 0.17) % 1.0
        self._fc = {}
        self._carve()
        self._braid()
        self.start = (1, 1)
        self.dist = self.bfs_all(self.start)
        cells = [(x, y) for x in range(1, self.tw, 2) for y in range(1, self.th, 2)]
        self.cells = cells
        self.exit = max(cells, key=lambda c: self.dist.get(c, 0))
        self.crystal_tiles, self.enemy_tiles, self.item_tiles = [], [], []
        self.need = 0              # so viele Kristalle braucht man fuers Portal
        if populate:
            cand = [c for c in cells if self.dist.get(c, 0) > 4 and c != self.exit]
            count = clamp(max(self.cols * self.rows // 8, CRYSTAL_GOAL + 6), 6, 80)
            self.crystal_tiles = random.sample(cand, min(count, len(cand)))
            self.need = min(CRYSTAL_GOAL, len(self.crystal_tiles))
            far = [c for c in cells if self.dist.get(c, 0) >= 12] or \
                  [c for c in cells if self.dist.get(c, 0) >= 6]
            ne = (1 + number) * max(1.0, size) * enemy_mult
            if number >= 1:             # ab der zweiten Karte deutlich mehr Drohnen (Karte 1 bleibt wie sie war)
                ne *= min(2.4, 1.5 + 0.08 * number)
            ne = max(1, min(int(ne + 0.5), 48))
            self.enemy_tiles = random.sample(far, min(ne, len(far)))
            taken = set(self.crystal_tiles) | set(self.enemy_tiles)
            free = [c for c in cells if self.dist.get(c, 0) > 3 and c != self.exit and c not in taken]
            kinds = [k for k in PICKUP_INFO if k != "heart"]
            random.shuffle(kinds)
            picks = random.sample(free, min(2 + number // 2 + int(size * 2), 9, len(free)))
            self.item_tiles = [(c, kinds[i % len(kinds)]) for i, c in enumerate(picks)]
            if self.item_tiles and random.random() < heart_chance:      # Herz zum Aufladen
                self.item_tiles[-1] = (self.item_tiles[-1][0], "heart")

    # --- Erzeugung
    def _carve(self):
        self.grid[1][1] = 0
        stack = [(1, 1)]
        while stack:
            x, y = stack[-1]
            opts = []
            for dx, dy in self.DIRS4:
                nx, ny = x + dx * 2, y + dy * 2
                if 0 < nx < self.tw and 0 < ny < self.th and self.grid[ny][nx] == 1:
                    opts.append((nx, ny, dx, dy))
            if opts:
                nx, ny, dx, dy = random.choice(opts)
                self.grid[y + dy][x + dx] = 0
                self.grid[ny][nx] = 0
                stack.append((nx, ny))
            else:
                stack.pop()

    def _braid(self):
        """Ein paar Wände entfernen -> Schleifen, Gegner können dich umzingeln."""
        for y in range(1, self.th - 1):
            for x in range(1, self.tw - 1):
                if self.grid[y][x] == 1 and random.random() < 0.07:
                    horiz = x % 2 == 0 and y % 2 == 1
                    vert = x % 2 == 1 and y % 2 == 0
                    if horiz or vert:
                        self.grid[y][x] = 0

    # --- Abfragen
    def is_wall(self, x, y):
        return x < 0 or y < 0 or x >= self.tw or y >= self.th or self.grid[y][x] == 1

    def floor_neighbors(self, x, y):
        for dx, dy in self.DIRS4:
            if not self.is_wall(x + dx, y + dy):
                yield (x + dx, y + dy)

    def bfs_all(self, start):
        dist, q = {start: 0}, deque([start])
        while q:
            c = q.popleft()
            for n in self.floor_neighbors(*c):
                if n not in dist:
                    dist[n] = dist[c] + 1
                    q.append(n)
        return dist

    def bfs_path(self, start, goal, max_nodes=500):
        if start == goal:
            return [start]
        prev, q = {start: None}, deque([start])
        while q:
            c = q.popleft()
            for n in self.floor_neighbors(*c):
                if n not in prev:
                    prev[n] = c
                    if n == goal:
                        path = [n]
                        while prev[path[-1]] is not None:
                            path.append(prev[path[-1]])
                        return path[::-1]
                    q.append(n)
            if len(prev) > max_nodes:
                return None
        return None

    def floor_cols(self, x, y):
        v = self._fc.get((x, y))
        if v is None:
            h = (self.hue0 + 0.12 * (x / self.tw + y / self.th)) % 1.0
            base = 0.09 + (0.02 if (x + y) % 2 else 0.0)
            v = (hsv(h, 0.7, base), hsv(h, 0.8, base + 0.06))
            self._fc[(x, y)] = v
        return v


# ============================================================== Entitäten
class Crystal:
    def __init__(self, tx, ty):
        self.x, self.y = (tx + 0.5) * TS, (ty + 0.5) * TS
        self.ph = random.random() * 6.28
        self.alive = True


class Pickup:
    def __init__(self, tile, kind):
        self.x, self.y = (tile[0] + 0.5) * TS, (tile[1] + 0.5) * TS
        self.kind, self.ph, self.alive = kind, random.random() * 6.28, True


class Player:
    R = 11

    def __init__(self, tile):
        self.x, self.y = (tile[0] + 0.5) * TS, (tile[1] + 0.5) * TS
        self.vx = self.vy = 0.0
        self.face = (1.0, 0.0)
        self.dash_t = self.dash_cd = self.inv = self.dash_buf = 0.0
        self.dash_dir = (1.0, 0.0)
        self.lives = START_LIVES
        self.shoot_cd = 0.0
        self.shield, self.magnet_t, self.oc_t = False, 0.0, 0.0
        self.energy = ENERGY_MAX
        self.emp_cd = self.trap_cd = self.decoy_cd = 0.0
        self.trail = []

    def try_dash(self, g):
        if self.dash_cd <= 0 and self.dash_t <= 0:
            self.dash_t, self.dash_cd, self.dash_buf = DASH_TIME, DASH_CD, 0.0
            self.dash_dir = self.face
            g.sfx.play("dash")
        else:
            self.dash_buf = 0.2          # Eingabe-Zwischenspeicher: Dash startet, sobald er bereit ist

    def update(self, dt, keys, lv, g):
        ax = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        ay = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        ax, ay = ax + g.tax, ay + g.tay                 # Handy: Joystick-Eingabe
        mag = math.hypot(ax, ay)
        if mag:
            ax, ay = ax / mag, ay / mag
            self.face = (ax, ay)
        sm = g.cheat["speed"]
        if self.dash_t > 0:
            self.dash_t -= dt
            self.vx, self.vy = self.dash_dir[0] * DASH_SPEED * sm, self.dash_dir[1] * DASH_SPEED * sm
            g.burst(self.x, self.y, (110, 200, 255) if g.mode == 1 else (255, 110, 90), 2, 50, 0.35, 6)
        else:
            k = min(1.0, dt * (22 if (ax or ay) else 30))     # direkteres Anfahren/Stoppen
            self.vx += (ax * SPEED * sm - self.vx) * k
            self.vy += (ay * SPEED * sm - self.vy) * k
        rate = 3.0 if self.oc_t > 0 else 1.0           # Overclock: Cooldowns 3x schneller
        self.dash_cd = max(0.0, self.dash_cd - dt * rate)
        self.shoot_cd = max(0.0, self.shoot_cd - dt * rate)
        self.emp_cd = max(0.0, self.emp_cd - dt * rate)
        self.trap_cd = max(0.0, self.trap_cd - dt * rate)
        self.decoy_cd = max(0.0, self.decoy_cd - dt * rate)
        self.oc_t = max(0.0, self.oc_t - dt)
        self.magnet_t = max(0.0, self.magnet_t - dt)
        self.inv = max(0.0, self.inv - dt)
        if g.cheat["nocd"] or g.cheat["noshot"]:
            self.shoot_cd = 0.0
        if g.cheat["nocd"]:
            self.emp_cd = self.trap_cd = self.decoy_cd = 0.0
        if g.cheat["nocd"] or g.cheat["nodash"]:
            self.dash_cd = 0.0
        self.dash_buf = max(0.0, self.dash_buf - dt)
        if self.dash_buf > 0 and self.dash_cd <= 0 and self.dash_t <= 0:
            self.try_dash(g)
        self.move(self.vx * dt, 0.0, lv, g)
        self.move(0.0, self.vy * dt, lv, g)
        # Schweif
        self.trail.append([self.x, self.y, 0.30])
        for t in self.trail:
            t[2] -= dt
        self.trail = [t for t in self.trail if t[2] > 0]
        if mag and random.random() < 0.35:
            g.burst(self.x, self.y, hsv(lv.hue0 + random.random() * 0.2, 0.5, 1.0), 1, 25, 0.5, 3)

    def move(self, dx, dy, lv, g=None):
        if g is not None and g.cheat["noclip"]:
            self.x = clamp(self.x + dx, self.R, lv.tw * TS - self.R)
            self.y = clamp(self.y + dy, self.R, lv.th * TS - self.R)
            return
        n = int(max(abs(dx), abs(dy)) // 12) + 1       # kleine Teilschritte gegen Durchtunneln
        for _ in range(n):
            self._step(dx / n, dy / n, lv)

    def _step(self, dx, dy, lv):
        self.x += dx
        self.y += dy
        r = self.R
        tx0, tx1 = int((self.x - r) // TS), int((self.x + r) // TS)
        ty0, ty1 = int((self.y - r) // TS), int((self.y + r) // TS)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                if not lv.is_wall(tx, ty):
                    continue
                if dx > 0:
                    self.x = tx * TS - r - 0.01
                    self.vx = 0.0
                elif dx < 0:
                    self.x = (tx + 1) * TS + r + 0.01
                    self.vx = 0.0
                if dy > 0:
                    self.y = ty * TS - r - 0.01
                    self.vy = 0.0
                elif dy < 0:
                    self.y = (ty + 1) * TS + r + 0.01
                    self.vy = 0.0


class Trap:
    """EMP-Falle: legt Drohnen in der Naehe lahm, sobald eine drueberlaeuft."""
    R = 24

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.arm, self.life, self.alive = 1.0, 60.0, True


class Decoy:
    """Koeder-Hologramm: lockt Drohnen von dir weg."""

    def __init__(self, x, y):
        self.x, self.y, self.life = x, y, DECOY_TIME


class Bolt:
    """Durchschlagender Energieschuss: legt jede getroffene Drohne lahm."""
    SPEED = 820.0

    def __init__(self, x, y, dx, dy):
        self.x, self.y, self.dx, self.dy = x, y, dx, dy
        self.life, self.alive, self.hit = 1.1, True, set()
        self.hist = []

    def update(self, dt, lv, g):
        dist = self.SPEED * dt
        n = int(dist // 10) + 1
        step = dist / n
        for _ in range(n):
            self.x += self.dx * step
            self.y += self.dy * step
            if lv.is_wall(int(self.x // TS), int(self.y // TS)):
                g.burst(self.x - self.dx * 6, self.y - self.dy * 6, (120, 230, 255), 14, 160, 0.4, 3)
                self.alive = False
                return
            for e in g.enemies:
                if id(e) not in self.hit and math.hypot(e.x - self.x, e.y - self.y) < e.R + 8:
                    self.hit.add(id(e))
                    g.disable_drone(e)
        self.hist.append((self.x, self.y))
        del self.hist[:-8]
        self.life -= dt
        if self.life <= 0:
            self.alive = False
        g.burst(self.x, self.y, (140, 240, 255), 2, 30, 0.3, 4)


class Drone:
    R = 12
    _ids = itertools.count(1)

    def __init__(self, tile, level_no, mult=1.0, sight=1.0, fail=REBOOT_FAIL, hunter=False):
        self.uid = next(Drone._ids)
        self.hunter = hunter     # Jäger: schneller, sieht weiter
        self.tile, self.prev, self.next = tile, None, None
        self.x, self.y = (tile[0] + 0.5) * TS, (tile[1] + 0.5) * TS
        self.patrol_speed = min(85 + 6 * level_no, 125) * mult * (1.10 if hunter else 1.0)
        self.chase_speed = min(135 + 8 * level_no, 195) * mult * (1.15 if hunter else 1.0)
        self.chasing = False
        self.sight = (9 if hunter else 7) * TS * sight
        self.rf = fail           # Chance auf Defekt nach dem Reboot
        self.off_age = 0.0
        self.stun = 0.0          # >0: lahmgelegt (harmlos)
        self.stun_max = DISABLE_TIME
        self.offline = False     # REBOOT FAILURE: dauerhaft ausgefallen
        self.near_t = 0.0        # Sperre für Knapp-Bonus
        self.alert_t = 0.0
        self.boot = 0.0          # >0: frisch repariert, faehrt hoch (harmlos)
        self.repaired = False
        self.lured = False       # folgt gerade einem Koeder
        self.scan = 0.0          # Schild-Modus: Scan-Fortschritt (Sekunden in deiner Naehe)
        self.delete_t = 0.0      # >0: Loeschung laeuft (harmlos)
        self.dead = False        # geloescht
        self.ph = random.random() * 6.28

    def update(self, dt, lv, p, decoy=None):
        self.alert_t = max(0.0, self.alert_t - dt)
        self.near_t = max(0.0, self.near_t - dt)
        if self.delete_t > 0:                    # Loeschung laeuft: steht still, harmlos
            self.chasing = False
            self.delete_t -= dt
            if self.delete_t <= 0:
                self.delete_t, self.dead = 0.0, True
            return
        if self.offline:                         # REBOOT FAILURE: nach REPAIR_TIME repariert sie sich selbst
            self.chasing = False
            self.off_age += dt
            if self.off_age >= REPAIR_TIME:
                self.offline, self.off_age = False, 0.0
                self.boot, self.repaired = 1.4, True
            return
        if self.boot > 0:                        # frisch repariert: faehrt kurz hoch
            self.boot -= dt
            self.chasing = False
            return
        if self.stun > 0:
            self.stun -= dt
            self.chasing = False
            if self.stun <= 0:                      # Reboot-Moment
                self.stun = 0.0
                if random.random() < self.rf:
                    self.offline = True
            return
        if self.next is None:
            self.pick(lv, p, decoy)
        if self.next is None:
            return
        tx, ty = (self.next[0] + 0.5) * TS, (self.next[1] + 0.5) * TS
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        step = (self.chase_speed if self.chasing else self.patrol_speed) * dt
        if d <= step:
            self.x, self.y = tx, ty
            self.prev, self.tile, self.next = self.tile, self.next, None
        else:
            self.x += dx / d * step
            self.y += dy / d * step

    def pick(self, lv, p, decoy=None):
        was_chasing = self.chasing
        self.chasing = False
        self.lured = False
        if decoy is not None:                       # Koeder hat Vorrang, ausser du stehst direkt daneben
            dd = math.hypot(decoy.x - self.x, decoy.y - self.y)
            pd = math.hypot(p.x - self.x, p.y - self.y)
            if dd < 11 * TS and (pd > 3 * TS or dd < pd):
                dtile = (int(decoy.x // TS), int(decoy.y // TS))
                if dtile == self.tile:
                    self.lured = True
                    opts = list(lv.floor_neighbors(*self.tile))     # kreist um das Hologramm
                    if opts:
                        self.next = random.choice(opts)
                    return
                path = lv.bfs_path(self.tile, dtile, 500)
                if path and len(path) > 1:
                    self.next, self.chasing, self.lured = path[1], True, True
                    return
        ptile = (int(p.x // TS), int(p.y // TS))
        if math.hypot(p.x - self.x, p.y - self.y) < self.sight:
            path = lv.bfs_path(self.tile, ptile, 400)
            if path and 1 < len(path) <= 14:
                self.next, self.chasing = path[1], True
                if not was_chasing:
                    self.alert_t = 0.7
                return
        opts = list(lv.floor_neighbors(*self.tile))
        if not opts:
            return
        forward = [o for o in opts if o != self.prev]
        self.next = random.choice(forward or opts)

# ============================================================== Spiel
class Game:
    def __init__(self):
        self.load_data()
        self.reset_cheats()
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED, vsync=1)
        except Exception:
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("NEON MAZE PRO")
        self.clock = pygame.time.Clock()
        self.fullscreen = False
        if "--vollbild" in sys.argv or "-f" in sys.argv or self.opt["fullscreen"]:
            self.toggle_fullscreen()
        names = "consolas,dejavusansmono,couriernew,monospace"
        self.f_title = pygame.font.SysFont(names, 120, bold=True)
        self.f_big = pygame.font.SysFont(names, 52, bold=True)
        self.f_mid = pygame.font.SysFont(names, 26, bold=True)
        self.f_small = pygame.font.SysFont(names, 18, bold=True)
        self.f_tiny = pygame.font.SysFont(names, 14, bold=True)
        self.f_key = pygame.font.SysFont(names, 12, bold=True)
        self.f_num = pygame.font.SysFont(names, 34, bold=True)
        self._tc = {}
        self._pc = {}

        self.scene = pygame.Surface((W, H)).convert()
        self.dark = pygame.Surface((W, H)).convert()
        self.light = {
            "player": self.make_light(340, (255, 205, 190)),
            "player_blue": self.make_light(340, (185, 215, 255)),
            "exit": self.make_light(150, (60, 255, 150)),
            "crystal": self.make_light(70, (255, 70, 200)),
            "enemy": self.make_light(95, (70, 140, 255)),
            "enemy_red": self.make_light(95, (255, 70, 90)),
            "off": self.make_light(60, (80, 130, 210)),
            "bolt": self.make_light(90, (120, 230, 255)),
            "pickup": self.make_light(80, (200, 225, 255)),
            "exit_locked": self.make_light(120, (255, 60, 70)),
            "trap": self.make_light(70, (255, 160, 60)),
            "decoy": self.make_light(110, (90, 230, 255)),
        }
        self.glow = {                       # Glow-Sprites: werden additiv auf die Szene gezeichnet
            "cry_p": self.make_light(30, (200, 60, 170)), "cry_c": self.make_light(30, (50, 170, 200)),
            "dr_b": self.make_light(34, (40, 90, 200)), "dr_r": self.make_light(34, (200, 40, 55)),
            "dr_h": self.make_light(34, (150, 50, 210)), "pl_r": self.make_light(46, (170, 60, 50)),
            "pl_c": self.make_light(46, (50, 130, 200)), "exit_g": self.make_light(60, (40, 220, 130)),
            "exit_r": self.make_light(60, (220, 50, 70)), "trap": self.make_light(40, (200, 120, 40)),
            "decoy": self.make_light(46, (50, 180, 210)),
        }
        self.vignette = self.make_vignette()
        self.danger_vig = self.make_vignette((255, 20, 40), 230)
        self.scanlines = self.make_scanlines()
        self.menu_overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        self.menu_overlay.fill((0, 0, 12, 150))
        self.flash_surf = pygame.Surface((W, H)).convert()
        self.flash_surf.fill((255, 30, 50))
        self.flash = 0.0
        self.bolts = []

        self.stars = [(random.uniform(0, W), random.uniform(0, H), random.uniform(0.05, 0.35),
                       random.choice((1, 1, 2, 3)), random.random()) for _ in range(170)]
        self.sfx = Sfx(self.opt["volume"] / 100, self.opt["music"] / 100, self.opt["mute"])
        self.mode = self.opt["mode"]                  # 0 = Virus-Modus, 1 = Schild-Modus
        self.stats = dict(disabled=0, crystals=0, time=0.0)
        self.spread_t = 0.0
        self.t = 0.0
        self.shake = 0.0
        self.particles, self.popups = [], []
        self.state = "menu"
        self.score, self.level_no, self.lives = 0, 0, START_LIVES
        self.cheated, self.submitted, self.last_rank = False, True, None
        self.console_open, self.con_buf, self.hist, self.hist_i = False, "", [], 0
        self.con_lines = [("ADMIN-KONSOLE bereit. 'hilfe' zeigt alle Befehle, TAB ergänzt.",
                           (120, 255, 200))]
        self.editing_name, self.sel, self.settings_from = False, 0, "menu"
        self.bigmap, self.spawn_t, self.next_life = False, 0.0, LIFE_EVERY
        self.demo = Level(5, populate=False)
        self.level = self.demo
        self.camx = self.camy = 0.0
        self.rings, self.traps, self.decoy = [], [], None
        self.need, self.portal_open, self.lock_msg_t, self.unlock_t = 0, False, 0.0, 0.0
        self.chain, self.chain_t, self.disp_score, self.hb_t = 0, 0.0, 0.0, 0.0
        self.toast_s, self.toast_t = "", 0.0
        self.embers = [[random.uniform(0, W), random.uniform(0, H), random.uniform(10, 40),
                        random.uniform(1, 3), random.random()] for _ in range(60)]
        self.virus_total, self.virus_done = 0, 0
        self.msel, self.quit_req, self.keys_tab = 0, False, 0
        self.touches, self.stick, self.tax, self.tay, self.btn_flash = {}, None, 0.0, 0.0, {}
        self.finger_seen = False
        self.build_menu_art()

    # ---------- Hilfsgrafiken
    @staticmethod
    def make_light(radius, color):
        s = pygame.Surface((radius * 2, radius * 2))
        for r in range(radius, 0, -2):
            f = (1 - r / radius) ** 1.6
            pygame.draw.circle(s, (int(color[0] * f), int(color[1] * f), int(color[2] * f)),
                               (radius, radius), r)
        return s

    @staticmethod
    def make_vignette(color=(0, 0, 0), strength=210):
        v = pygame.Surface((64, 36), pygame.SRCALPHA)
        for y in range(36):
            for x in range(64):
                d = min(1.0, math.hypot((x - 31.5) / 32, (y - 17.5) / 18) / 1.25)
                v.set_at((x, y), (color[0], color[1], color[2], int(strength * d ** 3)))
        return pygame.transform.smoothscale(v, (W, H))

    @staticmethod
    def make_scanlines():
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            pygame.draw.line(s, (0, 0, 0, 38), (0, y), (W, y))
        return s

    def text(self, surf, s, font, color, pos, anchor="center", glow=True):
        color = tuple(color)
        key = (id(font), s, color)
        ent = self._tc.get(key)
        if ent is None:                                  # gerenderte Texte zwischenspeichern
            if len(self._tc) > 700:
                self._tc.clear()
            ent = self._tc[key] = (font.render(s, True, color),
                                   font.render(s, True, tuple(int(c * 0.40) for c in color)))
        img, g = ent
        r = img.get_rect(**{anchor: pos})
        if glow:
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                surf.blit(g, (r.x + ox, r.y + oy))
        surf.blit(img, r)

    # ---------- Vollbild
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.opt["fullscreen"] = self.fullscreen
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.fullscreen else 0)
        try:
            self.screen = pygame.display.set_mode((W, H), flags, vsync=1)
        except Exception:
            try:
                self.screen = pygame.display.set_mode((W, H), flags)
            except Exception:
                try:
                    pygame.display.toggle_fullscreen()
                except Exception:
                    pass

    # ---------- Einstellungen / Bestenliste
    def load_data(self):
        self.opt = dict(DEFAULT_OPT)
        self.board = []
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                d = json.load(f)
            for k, v in d.get("settings", {}).items():
                if k in self.opt and type(v) == type(self.opt[k]):
                    self.opt[k] = v
            self.board = [e for e in d.get("leaderboard", [])
                          if isinstance(e, dict) and isinstance(e.get("score"), int)]
        except Exception:
            pass
        o = self.opt
        o["name"] = (o["name"].strip() or "SPIELER")[:12]
        o["volume"] = int(clamp(o["volume"], 0, 100))
        o["music"] = int(clamp(o["music"], 0, 100))
        o["control"] = int(clamp(o["control"], 0, 1))
        o["skin_color"] = int(clamp(o["skin_color"], 0, len(SKIN_COLORS) - 1))
        o["skin_style"] = int(clamp(o["skin_style"], 0, len(SKIN_STYLES) - 1))
        o["mapsize"] = int(clamp(o["mapsize"], 0, len(MAP_SIZES) - 1))
        o["difficulty"] = int(clamp(o["difficulty"], 0, len(DIFFICULTIES) - 1))
        o["mode"] = int(clamp(o["mode"], 0, len(MODES) - 1))
        old = 0
        try:
            with open(SAVE_FILE) as f:
                old = int(json.load(f).get("best", 0))
        except Exception:
            pass
        self.best = max([e["score"] for e in self.board] + [old])

    def save_data(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"settings": self.opt, "leaderboard": self.board}, f,
                          ensure_ascii=False, indent=1)
        except Exception:
            pass

    def submit_score(self):
        """Trägt den Lauf einmalig in die Bestenliste ein (Admin-Läufe zählen nicht)."""
        if self.submitted:
            return
        self.submitted = True
        self.last_rank = None
        if self.cheated or self.score <= 0:
            return
        entry = {"name": self.opt["name"], "score": int(self.score), "level": self.level_no + 1,
                 "date": time.strftime("%d.%m.%Y"),
                 "map": MAP_SIZES[self.opt["mapsize"]][0],
                 "diff": self.diff()["name"], "mode": MODES[self.mode][0]}
        self.board.append(entry)
        self.board.sort(key=lambda e: -e["score"])
        del self.board[50:]
        self.last_rank = next((i + 1 for i, e in enumerate(self.board) if e is entry), None)
        self.best = max(self.best, self.score)
        self.save_data()

    def end_run(self):
        self.submit_score()

    def diff(self):
        return DIFFICULTIES[self.opt["difficulty"]]

    def diff_speed(self):
        return self.diff()["speed"]

    def add_score(self, n):
        """Punkte mit Schwierigkeits-Faktor (Einfach weniger, HARDCORE doppelt)."""
        n = int(round(n * self.diff()["score"]))
        self.score += n
        return n

    def pick_name(self, kind):
        if kind == "shield" and self.mode == 1:
            return "PANZERUNG"
        return PICKUP_INFO[kind][0]

    def ecol(self):
        """Farbe der Gegner auf den Karten."""
        return (255, 90, 105) if self.mode == 1 else (90, 170, 255)

    def make_drone(self, tile):
        d = self.diff()
        hunter = False
        if self.level_no >= 2:                          # ab Karte 3 gibt es schnelle Jäger
            hunter = random.random() < min(0.5, 0.07 * self.level_no + 0.08 * self.opt["difficulty"])
        return Drone(tile, self.level_no, d["speed"], d["sight"], d["fail"], hunter)

    def reset_cheats(self):
        self.cheat = dict(god=False, endless=False, freeze=False, nocd=False,
                          noshot=False, nodash=False,
                          noclip=False, light=False, speed=1.0, timescale=1.0)

    # ---------- Spielfluss
    def start_game(self):
        self.level_no, self.score = 0, 0
        self.mode = self.opt["mode"]
        self.lives = min(MAX_LIVES, self.diff()["lives"])
        self.stats = dict(disabled=0, crystals=0, time=0.0)
        self.reset_cheats()
        self.cheated, self.submitted, self.last_rank = False, False, None
        self.next_life = self.diff()["life_every"]
        self.load_level()

    def load_level(self):
        self.level = Level(self.level_no, True, MAP_SIZES[self.opt["mapsize"]][1],
                           self.diff()["count"], self.diff()["heart"])
        lv = self.level
        self.player = Player(lv.start)
        self.player.lives = getattr(self, "lives", START_LIVES)
        self.crystals = [Crystal(*c) for c in lv.crystal_tiles]
        self.pickups = [Pickup(c, k) for c, k in lv.item_tiles]
        self.enemies = [self.make_drone(c) for c in lv.enemy_tiles]
        self.collected, self.level_time = 0, 0.0
        self.bigmap, self.spawn_t = False, 0.0
        self.spread_t = self.diff()["spread"]
        self.combo, self.combo_t = 0, 0.0
        self.explored, self.last_tile = set(), None
        self.particles, self.popups = [], []
        self.bolts, self.flash = [], 0.0
        self.rings, self.traps, self.decoy = [], [], None
        self.need = lv.need if self.mode == 0 else 0
        self.portal_open = self.mode == 0 and self.need <= 0
        self.virus_total = self.virus_done = 0
        if self.mode == 1:                              # Schild-Modus: pro Level 1 Virus mehr
            far = ([c for c in lv.cells if lv.dist.get(c, 0) >= 12] or
                   [c for c in lv.cells if lv.dist.get(c, 0) >= 6] or lv.cells)
            tiles = random.sample(far, min(self.level_no + 1, 12, len(far)))
            self.enemies = [self.make_drone(c) for c in tiles]
            self.virus_total = len(self.enemies)
        self.lock_msg_t = self.unlock_t = 0.0
        self.chain, self.chain_t, self.disp_score = 0, 0.0, float(self.score)
        self.banner = 2.2
        self.camx = self.player.x - W / 2
        self.camy = self.player.y - H / 2
        self.state = "play"
        self.sfx.play("blip")

    def complete_level(self):
        lv, p = self.level, self.player
        par = lv.dist[lv.exit] * TS / SPEED * 2.4
        tb = max(0, int(par - self.level_time)) * 10
        cb = 500 if self.collected == len(self.crystals) else 0
        tb, cb = self.add_score(tb), self.add_score(cb)
        self.lives = p.lives
        self.summary = dict(time=self.level_time, col=self.collected,
                            total=len(self.crystals), tb=tb, cb=cb)
        ex, ey = (lv.exit[0] + 0.5) * TS, (lv.exit[1] + 0.5) * TS
        self.burst(ex, ey, (80, 255, 170), 70, 260, 1.0, 5)
        self.sfx.play("win")
        if not self.cheated:
            self.best = max(self.best, self.score)
        self.state = "levelclear"

    def hit_player(self):
        p = self.player
        if p.shield:                                   # Schild zerbricht -> Schockwelle
            p.shield, p.inv = False, 1.2
            self.shake = 9
            self.burst(p.x, p.y, (100, 230, 255), 50, 280, 0.8, 5)
            self.ring(p.x, p.y, 5 * TS, (100, 230, 255), 0.6)
            self.popups.append([p.x, p.y - 26, self.pick_name("shield") + " ZERBRICHT", 1.3, (120, 230, 255)])
            self.sfx.play("emp")
            for e in self.enemies:
                if math.hypot(e.x - p.x, e.y - p.y) < 5 * TS:
                    self.disable_drone(e)
            return
        if self.mode == 1 and p.energy >= BLOCK_COST:  # Schild-Modus: Energie blockt den Treffer
            p.energy -= BLOCK_COST
            p.inv = 1.0
            self.shake = max(self.shake, 8)
            self.burst(p.x, p.y, (110, 230, 255), 36, 260, 0.7, 4)
            self.ring(p.x, p.y, 3.2 * TS, (110, 230, 255), 0.5)
            self.popups.append([p.x, p.y - 28, "BLOCK!", 1.1, (130, 235, 255)])
            self.sfx.play("block")
            for e in self.enemies:
                if math.hypot(e.x - p.x, e.y - p.y) < 3.2 * TS:
                    self.disable_drone(e, 4.0, quiet=True)
            return
        p.lives -= 1
        p.inv = 1.6
        self.shake = 14
        self.flash = 0.3
        self.burst(p.x, p.y, (255, 60, 80), 40, 240, 0.8, 5)
        self.sfx.play("hit")
        if p.lives <= 0:
            self.sfx.play("lose")
            self.submit_score()
            self.state = "gameover"

    # ---------- Schießen
    def shoot(self, dx, dy):
        p = self.player
        if self.state != "play" or p.shoot_cd > 0:
            return
        m = math.hypot(dx, dy)
        if m < 1e-6:
            dx, dy = p.face
            m = 1.0
        dx, dy = dx / m, dy / m
        p.shoot_cd = SHOT_CD
        self.bolts.append(Bolt(p.x, p.y, dx, dy))
        self.shake = max(self.shake, 3)
        self.burst(p.x + dx * 14, p.y + dy * 14, (150, 240, 255), 12, 140, 0.3, 3)
        self.sfx.play("shoot")

    def apply_pickup(self, it):
        p = self.player
        name, col = self.pick_name(it.kind), PICKUP_INFO[it.kind][1]
        if it.kind == "shield":
            p.shield = True
            if self.mode == 1:
                p.energy = ENERGY_MAX
        elif it.kind == "magnet":
            p.magnet_t = 10.0
        elif it.kind == "heart":
            p.lives = min(MAX_LIVES, p.lives + 1)
        else:                                           # Overclock
            p.oc_t, p.dash_cd, p.shoot_cd = 10.0, 0.0, 0.0
        self.add_score(25)
        self.burst(it.x, it.y, col, 36, 220, 0.8, 4)
        self.popups.append([it.x, it.y - 18, name + "!", 1.4, col])
        self.sfx.play("heart" if it.kind == "heart" else "power")

    # ---------- Gadgets: EMP-Puls, Fallen, Koeder
    def ring(self, x, y, maxr, col, life=0.6):
        self.rings.append([x, y, maxr, life, life, col])

    def use_emp(self):
        p = self.player
        if self.state != "play" or p.emp_cd > 0:
            return
        shield = self.mode == 1
        p.emp_cd = EMP_CD
        col = (110, 230, 255) if shield else (255, 205, 90)
        self.ring(p.x, p.y, EMP_RADIUS, col, 0.75)
        self.ring(p.x, p.y, EMP_RADIUS * 0.6, (255, 255, 255), 0.5)
        self.burst(p.x, p.y, col, 60, 340, 0.8, 5)
        self.shake = max(self.shake, 9)
        self.sfx.play("emp_big")
        n = 0
        for e in self.enemies:
            if math.hypot(e.x - p.x, e.y - p.y) < EMP_RADIUS and self.disable_drone(e, EMP_TIME, quiet=True):
                n += 1
        label = ("SCHILDWELLE" if shield else "EMP-PULS") + (f"  x{n}" if n else "")
        self.popups.append([p.x, p.y - 36, label, 1.4, col])
        if n >= 2:
            self.add_score(30 * n)
        if shield:
            p.energy = min(ENERGY_MAX, p.energy + 8 * n)

    def place_trap(self):
        p = self.player
        if self.state != "play" or p.trap_cd > 0:
            return
        if len(self.traps) >= TRAP_MAX:
            self.popups.append([p.x, p.y - 30, f"MAX. {TRAP_MAX} FALLEN", 1.0, (255, 170, 120)])
            return
        p.trap_cd = TRAP_CD
        self.traps.append(Trap(p.x, p.y))
        self.burst(p.x, p.y, (255, 170, 60), 14, 120, 0.4, 3)
        self.popups.append([p.x, p.y - 30, "FALLE GELEGT", 1.0, (255, 190, 90)])
        self.sfx.play("trap_set")

    def trigger_trap(self, tr):
        tr.alive = False
        self.ring(tr.x, tr.y, TRAP_RADIUS, (255, 170, 60), 0.6)
        self.burst(tr.x, tr.y, (255, 170, 60), 40, 280, 0.7, 4)
        self.shake = max(self.shake, 6)
        self.sfx.play("trap")
        n = 0
        for e in self.enemies:
            if math.hypot(e.x - tr.x, e.y - tr.y) < TRAP_RADIUS and self.disable_drone(e, TRAP_TIME, quiet=True):
                n += 1
        gain = self.add_score(40 * max(1, n))
        self.popups.append([tr.x, tr.y - 30, f"FALLE!  x{n}  +{gain}", 1.3, (255, 190, 90)])

    def place_decoy(self):
        p = self.player
        if self.state != "play" or p.decoy_cd > 0:
            return
        p.decoy_cd = DECOY_CD
        self.decoy = Decoy(p.x, p.y)
        self.ring(p.x, p.y, 2 * TS, (90, 230, 255), 0.5)
        self.burst(p.x, p.y, (90, 230, 255), 20, 150, 0.5, 3)
        self.popups.append([p.x, p.y - 30, "KÖDER AKTIV", 1.2, (110, 235, 255)])
        self.sfx.play("decoy")

    def open_portal(self):
        lv, p = self.level, self.player
        self.portal_open = True
        self.unlock_t = 3.0
        ex, ey = (lv.exit[0] + 0.5) * TS, (lv.exit[1] + 0.5) * TS
        self.ring(ex, ey, 4 * TS, (80, 255, 170), 1.0)
        self.burst(ex, ey, (80, 255, 170), 60, 260, 1.0, 5)
        self.popups.append([p.x, p.y - 44, "PORTAL OFFEN!", 2.0, (90, 255, 170)])
        self.shake = max(self.shake, 6)
        self.sfx.play("unlock")

    def drone_repaired(self, e):
        p = self.player
        self.burst(e.x, e.y, (120, 255, 200), 30, 200, 0.8, 4)
        self.ring(e.x, e.y, 1.6 * TS, (120, 255, 200), 0.6)
        self.popups.append([e.x, e.y - 30, "REPARIERT", 1.4, (120, 255, 200)])
        if math.hypot(e.x - p.x, e.y - p.y) < 14 * TS:
            self.sfx.play("repair")

    def toggle_mute(self):
        self.opt["mute"] = not self.opt["mute"]
        self.sfx.set_mute(self.opt["mute"])
        self.toast_s, self.toast_t = ("TON AUS" if self.opt["mute"] else "TON AN"), 1.4
        self.save_data()
        if not self.opt["mute"]:
            self.sfx.play("select")

    def set_volume(self, key, v):
        o = self.opt
        o[key] = int(clamp(v, 0, 100))
        if key == "volume":
            self.sfx.volume = o["volume"] / 100
        else:
            self.sfx.music_vol = o["music"] / 100
        self.sfx.play("blip")
        self.save_data()

    def music_scene(self, dt):
        st = self.state
        menu = st in ("menu", "leaderboard", "modeselect") or (st == "settings" and self.settings_from == "menu")
        duck = {"pause": 0.35, "levelclear": 0.5, "gameover": 0.3}.get(st, 1.0)
        if self.console_open:
            duck = 0.3
        self.sfx.want = "menu" if menu else "game"
        self.sfx.duck = duck
        self.sfx.update(dt)

    # ---------- Skins
    def skin_rgb(self, idx=None):
        idx = self.opt["skin_color"] if idx is None else idx
        name, c = SKIN_COLORS[idx]
        if c is not None:
            return c
        t = self.t
        if name == "REGENBOGEN":
            return hsv(t * 0.25, 0.85, 1.0)
        if name == "FEUER":
            return mix((255, 50, 20), (255, 215, 50), 0.5 + 0.5 * math.sin(t * 4))
        return mix((50, 190, 255), (235, 250, 255), 0.5 + 0.5 * math.sin(t * 3))

    def skin_pal(self, base=None, dash=False):
        base = self.skin_rgb() if base is None else base
        if dash:
            base = mix(base, (255, 215, 140), 0.5)
        return (base, mix(base, (255, 255, 255), 0.35), mix(base, (255, 255, 255), 0.65),
                mix(base, (0, 0, 0), 0.68))

    # ---------- Schild-Modus: Scannen & Loeschen
    def update_scan(self, dt):
        p = self.player
        for e in self.enemies:
            if e.delete_t > 0 or e.dead:
                continue
            if math.hypot(e.x - p.x, e.y - p.y) < SCAN_RADIUS:
                old = e.scan
                e.scan = min(SCAN_TIME, e.scan + dt)
                if int(e.scan) != int(old):
                    self.sfx.play("blip", 0.45)
                if e.scan >= SCAN_TIME:
                    self.start_delete(e)
            else:
                e.scan = max(0.0, e.scan - dt * 1.5)
        dead = [e for e in self.enemies if e.dead]
        for e in dead:
            self.virus_deleted(e)
        if dead:
            self.enemies = [e for e in self.enemies if not e.dead]

    def start_delete(self, e):
        p = self.player
        e.delete_t, e.scan = DELETE_TIME, 0.0
        e.stun, e.offline, e.off_age, e.boot, e.chasing = 0.0, False, 0.0, 0.0, False
        self.ring(e.x, e.y, 2.2 * TS, (90, 255, 200), 0.7)
        self.burst(e.x, e.y, (90, 255, 200), 40, 240, 0.8, 4)
        self.popups.append([e.x, e.y - 34, "LÖSCHUNG GESTARTET", 1.6, (90, 255, 200)])
        p.energy = min(ENERGY_MAX, p.energy + 20)
        self.add_score(100)
        self.shake = max(self.shake, 5)
        self.sfx.play("delete_start")

    def virus_deleted(self, e):
        self.virus_done += 1
        self.ring(e.x, e.y, 3 * TS, (90, 255, 200), 0.9)
        self.burst(e.x, e.y, (90, 255, 200), 70, 300, 1.0, 5)
        gain = self.add_score(300)
        self.popups.append([e.x, e.y - 34, f"VIRUS GELÖSCHT  +{gain}", 1.8, (120, 255, 215)])
        self.shake = max(self.shake, 7)
        self.sfx.play("delete_done")

    def goal(self):
        """(erreicht, benoetigt) fuer das Portal-Ziel des aktuellen Modus."""
        if self.mode == 1:
            return self.virus_done, self.virus_total
        return min(self.collected, self.need), self.need

    # ---------- Zeiger (Maus + Touch) und Klick-Steuerung der Menues
    def touch_mode(self):
        return self.opt["control"] == 1

    def touch_reset(self):
        self.touches, self.stick, self.tax, self.tay = {}, None, 0.0, 0.0

    def pointer_down(self, pid, pos):
        if self.console_open:
            return
        if self.state == "play":
            if self.touch_mode():
                self.touch_down(pid, pos)
            else:
                self.on_click(pos)
            return
        self.ui_click(pos)

    def pointer_move(self, pid, pos):
        if self.state == "play" and pid in self.touches:
            self.touch_move(pid, pos)

    def pointer_up(self, pid):
        if pid in self.touches:
            self.touch_up(pid)

    def right_click(self, pos):
        if self.state != "play" or self.console_open or self.touch_mode():
            return
        pl = self.player                                  # Rechtsklick: Dash Richtung Maus
        mdx, mdy = pos[0] - (pl.x - self.camx), pos[1] - (pl.y - self.camy)
        md = math.hypot(mdx, mdy)
        if md > 8:
            pl.face = (mdx / md, mdy / md)
        pl.try_dash(self)

    def hover(self, pos):
        if self.state == "menu":
            for i in range(len(MENU_ITEMS)):
                if self.menu_btn(i).collidepoint(pos) and self.msel != i:
                    self.msel = i
                    self.sfx.play("blip", 0.5)

    def touch_down(self, pid, pos):
        for name, cx, cy, r, label, col in TOUCH_BTNS:
            if math.hypot(pos[0] - cx, pos[1] - cy) <= r + 12:
                self.touches[pid] = name
                self.btn_flash[name] = 0.18
                self.touch_btn(name)
                return
        if self.stick is None and pos[0] < W * 0.55:       # schwebender Joystick links
            self.stick = [pid, pos[0], pos[1], pos[0], pos[1]]
            self.touches[pid] = "stick"

    def touch_move(self, pid, pos):
        st = self.stick
        if self.touches.get(pid) != "stick" or st is None:
            return
        R = 80.0
        dx, dy = pos[0] - st[1], pos[1] - st[2]
        d = math.hypot(dx, dy)
        if d > R:                                          # Joystick folgt dem Finger
            st[1] += dx / d * (d - R)
            st[2] += dy / d * (d - R)
            dx, dy, d = pos[0] - st[1], pos[1] - st[2], R
        st[3], st[4] = pos[0], pos[1]
        if d < 0.2 * R:
            self.tax = self.tay = 0.0
        else:
            self.tax, self.tay = dx / R, dy / R

    def touch_up(self, pid):
        role = self.touches.pop(pid, None)
        if role == "stick":
            self.stick, self.tax, self.tay = None, 0.0, 0.0

    def touch_btn(self, name):
        p = self.player
        if name == "dash":
            p.try_dash(self)
        elif name == "shoot":
            self.auto_shoot()
        elif name == "emp":
            self.use_emp()
        elif name == "trap":
            self.place_trap()
        elif name == "decoy":
            self.place_decoy()
        elif name == "pause":
            self.state = "pause"
        elif name == "map":
            self.bigmap = not self.bigmap

    def auto_shoot(self):
        """Handy: zielt automatisch auf die naechste aktive Drohne (sonst in Laufrichtung)."""
        p = self.player
        best, bd = None, 9 * TS
        for e in self.enemies:
            if e.offline or e.delete_t > 0 or e.stun > 0:
                continue
            d = math.hypot(e.x - p.x, e.y - p.y)
            if d < bd:
                best, bd = e, d
        if best is not None:
            self.shoot(best.x - p.x, best.y - p.y)
        else:
            self.shoot(p.face[0], p.face[1])

    def menu_btn(self, i):
        return pygame.Rect(90, 262 + i * 66, 380, 54)

    def back_rect(self):
        return pygame.Rect(24, 20, 150, 40)

    def pause_btn(self, i):
        return pygame.Rect(W // 2 - 170, H // 2 - 100 + i * 62, 340, 50)

    def menu_action(self, i):
        act = MENU_ITEMS[i][1]
        self.sfx.play("select")
        if act == "play":
            self.state = "modeselect"
        elif act == "skins":
            self.state = "skins"
        elif act == "keys":
            self.state = "keys"
        elif act == "settings":
            self.open_settings("menu")
        elif act == "board":
            self.state = "leaderboard"
        elif act == "quit":
            self.quit_req = True
            return True
        return False

    def ui_click(self, pos):
        st = self.state
        if st == "menu":
            for i in range(len(MENU_ITEMS)):
                if self.menu_btn(i).collidepoint(pos):
                    self.msel = i
                    self.menu_action(i)
                    return
        elif st == "modeselect":
            o = self.opt
            if self.back_rect().collidepoint(pos):
                self.state = "menu"
            elif self.start_rect().collidepoint(pos):
                self.save_data()
                self.start_game()
            elif self.diff_rect(0).collidepoint(pos):
                o["difficulty"] = (o["difficulty"] - 1) % len(DIFFICULTIES)
                self.sfx.play("blip")
                self.save_data()
            elif self.diff_rect(1).collidepoint(pos):
                o["difficulty"] = (o["difficulty"] + 1) % len(DIFFICULTIES)
                self.sfx.play("blip")
                self.save_data()
            else:
                self.modeselect_click(pos)
        elif st == "leaderboard":
            self.state = "menu"
        elif st == "settings":
            if not self.editing_name:
                self.settings_click(pos)
        elif st == "skins":
            self.skins_click(pos)
        elif st == "keys":
            self.keys_click(pos)
        elif st == "pause":
            for i in range(3):
                if self.pause_btn(i).collidepoint(pos):
                    self.sfx.play("select")
                    if i == 0:
                        self.state = "play"
                    elif i == 1:
                        self.open_settings("pause")
                    else:
                        self.end_run()
                        self.state = "menu"
                    return
        elif st == "levelclear":
            self.level_no += 1
            self.load_level()
        elif st == "gameover":
            self.state = "menu"

    # ---------- Skin-Menue
    def skin_cell(self, i):
        return pygame.Rect(642 + (i % 6) * 94, 150 + (i // 6) * 78, 88, 70)

    def style_btn(self, i):
        return pygame.Rect(110 if i == 0 else 470, 530, 60, 46)

    def skins_key(self, k):
        o = self.opt
        n = len(SKIN_COLORS)
        if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_BACKSPACE, pygame.K_SPACE):
            self.save_data()
            self.state = "menu"
            return
        i = o["skin_color"]
        if k in (pygame.K_LEFT, pygame.K_a):
            i = (i - 1) % n
        elif k in (pygame.K_RIGHT, pygame.K_d):
            i = (i + 1) % n
        elif k in (pygame.K_UP, pygame.K_w):
            i = (i - 6) % n
        elif k in (pygame.K_DOWN, pygame.K_s):
            i = (i + 6) % n
        elif k in (pygame.K_TAB, pygame.K_q, pygame.K_e):
            o["skin_style"] = (o["skin_style"] + 1) % len(SKIN_STYLES)
            self.sfx.play("blip")
            self.save_data()
            return
        else:
            return
        o["skin_color"] = i
        self.sfx.play("blip")
        self.save_data()

    def skins_click(self, pos):
        o = self.opt
        if self.back_rect().collidepoint(pos):
            self.save_data()
            self.state = "menu"
            return
        for i, d in ((0, -1), (1, 1)):
            if self.style_btn(i).collidepoint(pos):
                o["skin_style"] = (o["skin_style"] + d) % len(SKIN_STYLES)
                self.sfx.play("blip")
                self.save_data()
                return
        for i in range(len(SKIN_COLORS)):
            if self.skin_cell(i).collidepoint(pos):
                o["skin_color"] = i
                self.sfx.play("blip")
                self.save_data()
                return

    def draw_back_button(self):
        r = self.back_rect()
        hov = r.collidepoint(pygame.mouse.get_pos())
        self.hud_panel(r.x, r.y, r.w, r.h, (255, 240, 130) if hov else (110, 120, 255), cut=10, alpha=200)
        self.text(self.screen, "< ZURÜCK", self.f_small, (255, 255, 255), r.center, glow=hov)

    def draw_button(self, r, label, sel, col=(110, 230, 255), sub=None, shift=True):
        sc = self.screen
        off = 14 if (sel and shift) else 0
        x, y, w, h = r.x + off, r.y, r.w, r.h
        self.hud_panel(x, y, w, h, col if sel else (90, 100, 190), cut=14, alpha=225 if sel else 150)
        if sel:
            pygame.draw.polygon(sc, self.dim(col, 0.16 + 0.08 * math.sin(self.t * 6)),
                                self.poly(x + 5, y + 5, w - 11, h - 11, 11))
            pygame.draw.polygon(sc, col, [(x - 20, y + h // 2 - 9), (x - 20, y + h // 2 + 9), (x - 6, y + h // 2)])
        self.text(sc, label, self.f_mid, (255, 255, 255) if sel else (190, 195, 235), (x + 26, y + h // 2),
                  "midleft", glow=sel)
        if sub:
            self.text(sc, sub, self.f_tiny, self.dim(col, 0.9) if sel else (130, 140, 200),
                      (x + w - 18, y + h // 2), "midright", glow=False)

    def draw_skins(self):
        sc, o, t = self.screen, self.opt, self.t
        self.draw_back_button()
        self.text(sc, "SKINS", self.f_big, (255, 240, 150), (W // 2, 50))
        base = self.skin_rgb()
        self.hud_panel(60, 90, 520, 570, base, cut=22, alpha=215)
        self.text(sc, "DEIN VIRUS", self.f_small, (170, 175, 230), (320, 122), glow=False)
        cx, cy = 320, 320
        for i in range(3):
            pygame.draw.circle(sc, self.dim(base, 0.30 - i * 0.08), (cx, cy),
                               118 + i * 20 + int(4 * math.sin(t * 2 + i)), 1)
        self.draw_virus(sc, cx, cy + math.sin(t * 2) * 6, 62, self.skin_pal(base), ext=26, style=o["skin_style"])
        self.text(sc, SKIN_COLORS[o["skin_color"]][0], self.f_big, base, (cx, 455))
        self.text(sc, f"Stil: {SKIN_STYLES[o['skin_style']]}", self.f_mid, (220, 225, 255), (cx, 553), glow=False)
        for i in range(2):
            r = self.style_btn(i)
            hov = r.collidepoint(pygame.mouse.get_pos())
            self.hud_panel(r.x, r.y, r.w, r.h, (255, 240, 130) if hov else (110, 120, 255), cut=8, alpha=200)
            cxx, cyy = r.center
            d = -1 if i == 0 else 1
            pygame.draw.polygon(sc, (255, 255, 255), [(cxx + d * 9, cyy - 11), (cxx + d * 9, cyy + 11), (cxx - d * 9, cyy)])
        self.text(sc, "Gilt im VIRUS-Modus   |   TAB: Stil wechseln", self.f_tiny, (150, 155, 210), (cx, 618),
                  glow=False)
        self.hud_panel(620, 90, 600, 570, (110, 120, 255), cut=22, alpha=215)
        self.text(sc, "FARBE WÄHLEN", self.f_small, (170, 175, 230), (920, 122), glow=False)
        for i, (nm, c) in enumerate(SKIN_COLORS):
            r = self.skin_cell(i)
            col = self.skin_rgb(i)
            pygame.draw.rect(sc, self.dim(col, 0.5), r)
            pygame.draw.rect(sc, col, (r.x + 4, r.y + 4, r.w - 8, r.h - 8))
            if c is None:
                self.text(sc, SKIN_SHORT[nm], self.f_key, (10, 10, 30), r.center, glow=False)
            if i == o["skin_color"]:
                pygame.draw.rect(sc, (255, 255, 255), r.inflate(8, 8), 3)

    # ---------- Steuerungs-Menue (alle Tasten in eigener Kategorie)
    def keys_tab_rect(self, i):
        return pygame.Rect(W // 2 - 290 + i * 300, 92, 280, 48)

    def keys_toggle_rect(self):
        return pygame.Rect(W // 2 - 220, 612, 440, 46)

    def keys_key(self, k):
        if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_BACKSPACE):
            self.state = "menu"
        elif k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB, pygame.K_a, pygame.K_d):
            self.keys_tab = 1 - self.keys_tab
            self.sfx.play("blip")

    def keys_click(self, pos):
        if self.back_rect().collidepoint(pos):
            self.state = "menu"
            return
        for i in range(2):
            if self.keys_tab_rect(i).collidepoint(pos):
                self.keys_tab = i
                self.sfx.play("blip")
                return
        if self.keys_toggle_rect().collidepoint(pos):
            self.opt["control"] = 1 - self.opt["control"]
            self.touch_reset()
            self.sfx.play("select")
            self.save_data()

    def big_key(self, x, y, label, col):
        sc = self.screen
        w = max(34, self.f_small.size(label)[0] + 18)
        r = pygame.Rect(x, y, w, 30)
        pygame.draw.rect(sc, (14, 18, 44), r)
        pygame.draw.rect(sc, col, r, 2)
        pygame.draw.line(sc, self.dim(col, 0.5), (r.x + 3, r.bottom - 3), (r.right - 4, r.bottom - 3), 2)
        self.text(sc, label, self.f_small, (235, 235, 255), r.center, glow=False)
        return w

    def draw_keys(self):
        sc, t = self.screen, self.t
        self.draw_back_button()
        self.text(sc, "STEUERUNG", self.f_big, (255, 240, 150), (W // 2, 50))
        for i, nm in enumerate(("PC  (Tastatur + Maus)", "HANDY  (Touch)")):
            self.draw_button(self.keys_tab_rect(i), nm, self.keys_tab == i, (110, 230, 255), shift=False)
        self.hud_panel(60, 156, 1160, 440, (110, 120, 255), cut=22, alpha=215)
        if self.keys_tab == 0:
            for c, (title, col, rows) in enumerate(KEYS_PC):
                x = 96 + c * 385
                self.text(sc, title, self.f_mid, col, (x, 188), "midleft", glow=False)
                pygame.draw.line(sc, self.dim(col, 0.6), (x, 208), (x + 340, 208), 2)
                for r_i, (keys, label) in enumerate(rows):
                    y = 226 + r_i * 52
                    kx = x
                    for ki, kname in enumerate(keys):
                        kx += self.big_key(kx, y, kname, col) + 6
                    self.text(sc, label, self.f_small, (215, 220, 255), (x + 195, y + 15), "midleft", glow=False)
            self.text(sc, "Dash macht dich kurz unverwundbar.  Der Schuss legt Drohnen 15 s lahm (alle 10 s).",
                      self.f_small, (170, 175, 230), (W // 2, 545), glow=False)
            self.text(sc, "Menüs: Pfeiltasten + ENTER oder Maus.   ESC = zurück", self.f_tiny, (140, 150, 205),
                      (W // 2, 575), glow=False)
        else:
            cx, cy = 250, 340
            pygame.draw.circle(sc, (110, 130, 255), (cx, cy), 80, 2)
            pygame.draw.circle(sc, (60, 70, 150), (cx, cy), 40, 1)
            kx, ky = cx + int(34 * math.cos(t * 1.6)), cy + int(34 * math.sin(t * 1.6))
            pygame.draw.circle(sc, (150, 170, 255), (kx, ky), 30)
            pygame.draw.circle(sc, (255, 255, 255), (kx, ky), 30, 2)
            self.text(sc, "BEWEGEN", self.f_mid, (150, 170, 255), (cx, cy + 125))
            self.text(sc, "linke Bildschirmhälfte:", self.f_tiny, (170, 175, 230), (cx, cy + 160), glow=False)
            self.text(sc, "Finger halten & ziehen", self.f_tiny, (170, 175, 230), (cx, cy + 180), glow=False)
            items = (("dash", "DASH", "kurz unverwundbar", (90, 255, 255)),
                     ("shot", "SCHUSS", "zielt automatisch auf Drohnen", (255, 120, 230)),
                     ("emp", "EMP", "legt alle Drohnen im Umkreis lahm", (255, 205, 90)),
                     ("trap", "FALLE", "löst bei einer Drohne aus", (255, 170, 70)),
                     ("decoy", "KÖDER", "lockt Drohnen von dir weg", (90, 230, 255)))
            for j, (ic, nm, desc, col) in enumerate(items):
                y = 215 + j * 62
                pygame.draw.circle(sc, (8, 12, 32), (560, y), 27)
                pygame.draw.circle(sc, col, (560, y), 27, 2)
                self.draw_icon(ic, 560, y, col)
                self.text(sc, nm, self.f_small, col, (610, y - 11), "midleft", glow=False)
                self.text(sc, desc, self.f_tiny, (190, 195, 235), (610, y + 11), "midleft", glow=False)
            self.text(sc, "II = Pause     MAP = große Karte", self.f_small, (170, 175, 230), (900, 340), glow=False)
            self.text(sc, "Die Buttons liegen rechts unten,", self.f_tiny, (140, 150, 205), (900, 390), glow=False)
            self.text(sc, "der Joystick links - ganz ohne Tastatur.", self.f_tiny, (140, 150, 205), (900, 410),
                      glow=False)
        r = self.keys_toggle_rect()
        self.draw_button(r, f"Steuerung: {'HANDY' if self.touch_mode() else 'PC'}  (tippen = wechseln)",
                         r.collidepoint(pygame.mouse.get_pos()), (255, 220, 100), shift=False)

    def on_click(self, pos):
        p = self.player
        self.shoot(pos[0] - (p.x - self.camx), pos[1] - (p.y - self.camy))

    def reboot_failed(self, e):
        p = self.player
        self.burst(e.x, e.y, (255, 60, 80), 40, 260, 1.0, 5)
        self.popups.append([e.x, e.y - 30, "REBOOT FAILURE", 1.6, (255, 70, 90)])
        if math.hypot(e.x - p.x, e.y - p.y) < 14 * TS:
            self.shake = max(self.shake, 5)
            self.sfx.play("fail")

    def rebooted(self, e):
        p = self.player
        self.burst(e.x, e.y, (120, 200, 255), 16, 160, 0.5, 3)
        self.popups.append([e.x, e.y - 30, "ONLINE", 1.0, (120, 220, 255)])
        if math.hypot(e.x - p.x, e.y - p.y) < 14 * TS:
            self.sfx.play("reboot")

    def disable_drone(self, e, dur=DISABLE_TIME, quiet=False):
        if e.offline or e.delete_t > 0:
            return False
        e.stun, e.stun_max, e.chasing, e.alert_t, e.boot = dur, dur, False, 0.0, 0.0
        self.burst(e.x, e.y, (120, 200, 255), 18 if quiet else 34, 230, 0.8, 4)
        gain = self.add_score(50)
        self.stats["disabled"] += 1
        if not quiet:
            self.popups.append([e.x, e.y - 22, f"+{gain}", 1.0, (150, 220, 255)])
            self.shake = max(self.shake, 4)
            self.sfx.play("emp")
        return True

    # ---------- Eingabe
    def on_key(self, k, uni=""):
        alt = pygame.key.get_mods() & pygame.KMOD_ALT
        if k == pygame.K_F11 or (alt and k in (pygame.K_RETURN, pygame.K_KP_ENTER)):
            self.toggle_fullscreen()
            self.save_data()
            return False
        if self.console_open:
            self.console_key(k, uni)
            return False
        if self.editing_name:
            self.name_key(k, uni)
            return False
        if k == pygame.K_n:
            self.toggle_mute()
            return False
        st = self.state
        if st in ("play", "pause") and (k in (pygame.K_F1, pygame.K_CARET, pygame.K_BACKQUOTE)
                                        or uni in ("^", "`", "°")):
            self.set_console(True)
            return False
        if st == "menu":
            if k in (pygame.K_UP, pygame.K_w):
                self.msel = (self.msel - 1) % len(MENU_ITEMS)
                self.sfx.play("blip", 0.6)
            elif k == pygame.K_DOWN:
                self.msel = (self.msel + 1) % len(MENU_ITEMS)
                self.sfx.play("blip", 0.6)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.menu_action(self.msel)
            elif k == pygame.K_s:
                self.open_settings("menu")
            elif k == pygame.K_l:
                self.state = "leaderboard"
            elif k == pygame.K_ESCAPE:
                return True
        elif st == "skins":
            self.skins_key(k)
        elif st == "keys":
            self.keys_key(k)
        elif st == "leaderboard":
            if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_l):
                self.state = "menu"
        elif st == "modeselect":
            self.modeselect_key(k)
        elif st == "settings":
            self.settings_key(k)
        elif st == "play":
            if k in (pygame.K_ESCAPE, pygame.K_p):
                self.state = "pause"
            elif k in (pygame.K_TAB, pygame.K_m):
                self.bigmap = not self.bigmap
            elif k in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.player.try_dash(self)
            elif k in (pygame.K_e, pygame.K_f):
                self.on_click(pygame.mouse.get_pos())         # E/F schießen Richtung Maus
            elif k == pygame.K_q:
                self.use_emp()
            elif k == pygame.K_r:
                self.place_trap()
            elif k == pygame.K_c:
                self.place_decoy()
        elif st == "pause":
            if k in (pygame.K_ESCAPE, pygame.K_p):
                self.state = "play"
            elif k == pygame.K_s:
                self.open_settings("pause")
            elif k == pygame.K_q:
                self.end_run()
                self.state = "menu"
        elif st == "levelclear":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.level_no += 1
                self.load_level()
        elif st == "gameover":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE):
                self.state = "menu"
        return False

    # ---------- Partikel
    def burst(self, x, y, color, n, speed, life=0.6, size=4):
        if len(self.particles) > 700:
            return
        for _ in range(n):
            a, s = random.uniform(0, 6.283), random.uniform(0.2, 1.0) * speed
            self.particles.append([x, y, math.cos(a) * s, math.sin(a) * s,
                                   life * random.uniform(0.5, 1.0), life, color, size])

    def update_particles(self, dt):
        damp = 0.04 ** dt
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= damp
            p[3] *= damp
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for q in self.popups:
            q[1] -= 40 * dt
            q[3] -= dt
        self.popups = [q for q in self.popups if q[3] > 0]
        for rg in self.rings:
            rg[3] -= dt
        self.rings = [rg for rg in self.rings if rg[3] > 0]

    # ---------- Update
    def update(self, dt):
        self.t += dt
        self.update_particles(dt)
        self.shake = max(0.0, self.shake - dt * 40)
        self.flash = max(0.0, self.flash - dt)
        self.toast_t = max(0.0, self.toast_t - dt)
        for k in list(self.btn_flash):
            self.btn_flash[k] -= dt
            if self.btn_flash[k] <= 0:
                del self.btn_flash[k]
        if self.state != "play" and (self.touches or self.stick):
            self.touch_reset()
        if self.state == "menu":
            return
        if self.state != "play" or self.console_open:
            return
        lv, p = self.level, self.player
        self.level_time += dt
        self.stats["time"] += dt
        self.banner = max(0.0, self.banner - dt)
        self.combo_t -= dt
        if self.combo_t <= 0:
            self.combo = 0
        self.chain_t -= dt
        if self.chain_t <= 0:
            self.chain = 0
        self.lock_msg_t = max(0.0, self.lock_msg_t - dt)
        self.unlock_t = max(0.0, self.unlock_t - dt)
        self.disp_score += (self.score - self.disp_score) * min(1.0, dt * 8)
        if self.mode == 1:                              # Schild-Modus: Energie lädt sich langsam wieder auf
            p.energy = min(ENERGY_MAX, p.energy + ENERGY_REGEN * dt)
        if p.lives <= 1 and self.diff()["lives"] > 1 and not self.cheat["god"]:
            self.hb_t -= dt                             # Herzschlag-Warnung beim letzten Leben
            if self.hb_t <= 0:
                self.hb_t = 1.1
                self.sfx.play("heartbeat")
        p.update(dt, pygame.key.get_pressed(), lv, self)
        if self.cheat["freeze"]:
            for e in self.enemies:
                e.stun = max(e.stun, 5.0)
        if self.cheat["endless"]:
            self.spawn_t -= dt
            if self.spawn_t <= 0:
                self.spawn_t = 1.2
                self.spawn_drones(1)
        dec = self.decoy if (self.decoy is not None and self.decoy.life > 0) else None
        for e in self.enemies:
            was_stun, was_off, a0 = e.stun > 0, e.offline, e.alert_t
            e.update(dt, lv, p, dec)
            if e.offline and not was_off:
                self.reboot_failed(e)
            elif was_off and not e.offline:
                self.drone_repaired(e)
            elif was_stun and e.stun <= 0 and not e.offline:
                self.rebooted(e)
            if e.alert_t > a0 and math.hypot(e.x - p.x, e.y - p.y) < 9 * TS:
                self.sfx.play("alert", 0.6)
        if self.mode == 1:                              # Schild-Modus: scannen, loeschen, Portal oeffnen
            self.update_scan(dt)
            if not self.portal_open and not self.enemies:
                self.open_portal()
        for b in self.bolts:
            b.update(dt, lv, self)
        self.bolts = [b for b in self.bolts if b.alive]
        if self.decoy is not None:                      # Koeder läuft ab
            self.decoy.life -= dt
            if self.decoy.life <= 0:
                self.burst(self.decoy.x, self.decoy.y, (90, 230, 255), 24, 160, 0.6, 3)
                self.decoy = None
        for tr in self.traps:                           # Fallen: scharf nach 1 s, lösen bei Drohnen aus
            tr.life -= dt
            tr.arm = max(0.0, tr.arm - dt)
            if tr.arm <= 0 and tr.alive:
                for e in self.enemies:
                    if (e.stun <= 0 and not e.offline and e.boot <= 0 and e.delete_t <= 0
                            and math.hypot(e.x - tr.x, e.y - tr.y) < tr.R + e.R):
                        self.trigger_trap(tr)
                        break
        self.traps = [tr for tr in self.traps if tr.alive and tr.life > 0]

        if p.magnet_t > 0:                              # Magnet zieht Kristalle an
            for c in self.crystals:
                if c.alive:
                    mdx, mdy = p.x - c.x, p.y - c.y
                    md = math.hypot(mdx, mdy)
                    if 1 < md < 280:
                        sp = min(md, 420 * dt)
                        c.x += mdx / md * sp
                        c.y += mdy / md * sp
        for it in self.pickups:
            if (it.alive and math.hypot(it.x - p.x, it.y - p.y) < 22
                    and not (it.kind == "heart" and p.lives >= MAX_LIVES)):   # volle Herzen: Item bleibt liegen
                it.alive = False
                self.apply_pickup(it)
        for c in self.crystals:
            if c.alive and math.hypot(c.x - p.x, c.y - p.y) < 22:
                c.alive = False
                self.collected += 1
                self.combo = min(5, self.combo + 1)
                self.combo_t = 2.5
                gain = self.add_score(100 * self.combo)
                self.stats["crystals"] += 1
                self.burst(c.x, c.y, (255, 90, 220), 26, 190, 0.7, 4)
                self.popups.append([c.x, c.y - 10, f"+{gain}", 1.0, (255, 140, 235)])
                self.sfx.play(f"crystal{clamp(self.combo, 1, 5)}")
                if self.mode == 1:
                    p.energy = min(ENERGY_MAX, p.energy + 4)
                if self.mode == 0 and not self.portal_open and self.collected >= self.need:
                    self.open_portal()

        if p.dash_t > 0:
            for e in self.enemies:
                if e.stun > 0 or e.offline or e.delete_t > 0:
                    continue
                if math.hypot(e.x - p.x, e.y - p.y) < e.R + p.R + 14:
                    if self.mode == 1:                  # Schild-Modus: Dash = Schildstoß-Kette, Viren 7 s lahm
                        self.disable_drone(e, 9.0)
                        self.chain = min(6, self.chain + 1)
                        self.chain_t = 2.5
                        p.dash_cd = max(0.0, p.dash_cd - 0.25)      # jeder Stoß verkürzt den Dash-Cooldown
                        p.energy = min(ENERGY_MAX, p.energy + 8)
                        bonus = self.add_score(40 * self.chain)
                        self.popups.append([e.x, e.y - 40, f"STOSS x{self.chain}  +{bonus}", 1.0, (130, 235, 255)])
                        self.ring(e.x, e.y, 1.4 * TS, (110, 230, 255), 0.35)
                        self.shake = max(self.shake, 8)
                        self.sfx.play("bash")
                    elif e.near_t <= 0:                 # Virus-Modus: Knapp-Bonus beim Durchdashen
                        e.near_t = 3.0
                        gain = self.add_score(30)
                        self.popups.append([e.x, e.y - 30, f"KNAPP! +{gain}", 1.0, (255, 220, 120)])
                        self.burst(e.x, e.y, (255, 220, 120), 10, 150, 0.4, 3)
        if p.inv <= 0 and p.dash_t <= 0 and not self.cheat["god"]:
            for e in self.enemies:
                if (e.stun <= 0 and not e.offline and e.boot <= 0 and e.delete_t <= 0
                        and math.hypot(e.x - p.x, e.y - p.y) < e.R + p.R):
                    self.hit_player()
                    break

        while self.score >= self.next_life and not self.cheated:       # Extraleben
            self.next_life += self.diff()["life_every"]
            if p.lives < MAX_LIVES:
                p.lives += 1
                self.popups.append([p.x, p.y - 30, "EXTRALEBEN!", 1.6, (255, 120, 170)])
                self.burst(p.x, p.y, (255, 100, 160), 30, 200, 0.8, 4)
                self.sfx.play("power")
        ex, ey = (lv.exit[0] + 0.5) * TS, (lv.exit[1] + 0.5) * TS
        if self.state == "play" and math.hypot(ex - p.x, ey - p.y) < 20:
            if self.portal_open:
                self.complete_level()
            elif self.lock_msg_t <= 0:                  # Portal ist noch gesperrt
                self.lock_msg_t = 1.6
                hv, nd = self.goal()
                what = "Viren" if self.mode == 1 else "Kristalle"
                self.popups.append([ex, ey - 40, f"PORTAL GESPERRT - noch {nd - hv} {what}", 1.6, (255, 90, 110)])
                self.sfx.play("locked")
                self.shake = max(self.shake, 3)

        tile = (int(p.x // TS), int(p.y // TS))
        if tile != self.last_tile:
            self.last_tile = tile
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    if dx * dx + dy * dy <= 28:
                        x, y = tile[0] + dx, tile[1] + dy
                        if 0 <= x < lv.tw and 0 <= y < lv.th:
                            self.explored.add((x, y))

        # Kamera: immer auf den Spieler zentriert (nur leicht geglättet)
        k = min(1.0, dt * 9)                            # Kamera schaut leicht in Laufrichtung voraus
        self.camx += (p.x + p.vx * 0.12 - W / 2 - self.camx) * k
        self.camy += (p.y + p.vy * 0.12 - H / 2 - self.camy) * k

    # ---------- Zeichnen: Welt
    def draw_stars(self, sc, camx, camy):
        for x, y, d, s, h in self.stars:
            sx, sy = (x - camx * d) % W, (y - camy * d) % H
            b = 0.5 + 0.5 * math.sin(self.t * 1.5 + x)
            sc.fill(hsv(h, 0.4, 0.15 + 0.45 * b * d * 2), (int(sx), int(sy), s, s))

    def draw_world(self, sc, camx, camy):
        lv = self.level
        x0, x1 = max(0, int(camx // TS)), min(lv.tw - 1, int((camx + W) // TS))
        y0, y1 = max(0, int(camy // TS)), min(lv.th - 1, int((camy + H) // TS))
        shift = self.t * 0.02
        for y in range(y0, y1 + 1):
            row = lv.grid[y]
            for x in range(x0, x1 + 1):
                sx, sy = int(x * TS - camx), int(y * TS - camy)
                if row[x] == 0:
                    c1, c2 = lv.floor_cols(x, y)
                    sc.fill(c1, (sx, sy, TS, TS))
                    pygame.draw.rect(sc, c2, (sx + 3, sy + 3, TS - 6, TS - 6), 1)
                    sc.fill(c2, (sx + TS // 2 - 1, sy + TS // 2 - 1, 2, 2))
                    continue
                h = (lv.hue0 + 0.3 * (x / lv.tw + y / lv.th) * 0.5 + shift) % 1.0
                sc.fill((8, 8, 20), (sx, sy, TS, TS))
                pygame.draw.rect(sc, hsv(h, 0.9, 0.28), (sx + 7, sy + 7, TS - 14, TS - 14), 1)
                pv = 0.82 + 0.18 * math.sin(self.t * 2.0 + x * 0.45 + y * 0.3)
                edge, core = hsv(h, 0.85, pv), hsv(h, 0.30, 1.0)
                if not lv.is_wall(x, y - 1):
                    self.edge(sc, edge, core, (sx, sy + 1), (sx + TS, sy + 1))
                if not lv.is_wall(x, y + 1):
                    self.edge(sc, edge, core, (sx, sy + TS - 1), (sx + TS, sy + TS - 1))
                if not lv.is_wall(x - 1, y):
                    self.edge(sc, edge, core, (sx + 1, sy), (sx + 1, sy + TS))
                if not lv.is_wall(x + 1, y):
                    self.edge(sc, edge, core, (sx + TS - 1, sy), (sx + TS - 1, sy + TS))

    @staticmethod
    def edge(sc, edge, core, a, b):
        pygame.draw.line(sc, edge, a, b, 3)
        pygame.draw.line(sc, core, a, b, 1)

    def draw_exit(self, sc, ox, oy):
        lv = self.level
        cx = int((lv.exit[0] + 0.5) * TS - ox)
        cy = int((lv.exit[1] + 0.5) * TS - oy)
        if cx < -90 or cx > W + 90 or cy < -90 or cy > H + 90:
            return
        t = self.t
        if not self.portal_open:                         # gesperrt: rot, Schloss, Fortschrittsring
            col = (255, 70, 90)
            sc.blit(self.glow["exit_r"], (cx - 60, cy - 60), special_flags=pygame.BLEND_RGB_ADD)
            for i in range(3):
                r = 12 + i * 8 + (2 if (int(t * 4) + i) % 2 else 0)
                pygame.draw.circle(sc, self.dim(col, 0.9 - 0.25 * i), (cx, cy), r, 2)
            pygame.draw.rect(sc, col, (cx - 8, cy - 2, 16, 12))
            pygame.draw.arc(sc, col, (cx - 6, cy - 13, 12, 15), 0, math.pi, 2)
            pygame.draw.rect(sc, (20, 0, 8), (cx - 1, cy + 2, 2, 5))
            hv, nd = self.goal()
            frac = clamp(hv / max(1, nd), 0.0, 1.0)
            pygame.draw.arc(sc, (255, 150, 235), (cx - 33, cy - 33, 66, 66), math.pi / 2,
                            math.pi / 2 + 2 * math.pi * frac, 3)
            return
        sc.blit(self.glow["exit_g"], (cx - 60, cy - 60), special_flags=pygame.BLEND_RGB_ADD)
        for i in range(4):
            r = 8 + i * 7 + 2 * math.sin(t * 3 + i)
            pygame.draw.circle(sc, hsv(0.38 + 0.05 * i, 0.8, 1.0), (cx, cy), int(r), 2)
        for i in range(8):
            a = t * 1.8 + i * math.pi / 4
            pygame.draw.line(sc, (180, 255, 220), (cx + math.cos(a) * 12, cy + math.sin(a) * 12),
                             (cx + math.cos(a) * 30, cy + math.sin(a) * 30), 2)
        for i in range(3):
            a = -t * 2.4 + i * 2.094
            pygame.draw.circle(sc, (255, 255, 255), (int(cx + math.cos(a) * 38), int(cy + math.sin(a) * 38)), 3)
        pygame.draw.circle(sc, (255, 255, 255), (cx, cy), 5)

    def draw_crystal(self, sc, c, ox, oy):
        sx = c.x - ox
        sy = c.y - oy + math.sin(self.t * 3 + c.ph) * 3
        if sx < -30 or sx > W + 30 or sy < -30 or sy > H + 30:
            return
        blue = self.mode == 1
        base = (80, 225, 255) if blue else (255, 90, 220)
        hi = (220, 250, 255) if blue else (255, 225, 250)
        sc.blit(self.glow["cry_c" if blue else "cry_p"], (int(sx) - 30, int(sy) - 30),
                special_flags=pygame.BLEND_RGB_ADD)
        r = 11 + 2 * math.sin(self.t * 5 + c.ph)
        top, right, bot, left = (sx, sy - r * 1.25), (sx + r * 0.8, sy), (sx, sy + r * 1.25), (sx - r * 0.8, sy)
        pygame.draw.polygon(sc, base, [top, right, bot, left])
        pygame.draw.polygon(sc, self.dim(base, 0.5), [top, (sx, sy), bot, left])
        pygame.draw.polygon(sc, hi, [top, right, (sx, sy)])
        pygame.draw.polygon(sc, hi, [top, right, bot, left], 2)
        if int(self.t * 3 + c.ph * 5) % 6 == 0:                      # Funkeln
            pygame.draw.line(sc, (255, 255, 255), (sx - 7, sy - 9), (sx + 7, sy - 9), 1)
            pygame.draw.line(sc, (255, 255, 255), (sx, sy - 15), (sx, sy - 3), 1)

    @staticmethod
    def shield_pts(sx, sy, s):
        """Wappenschild: oben breit mit Zacken, unten spitz."""
        return [(sx - 0.95 * s, sy - 0.85 * s), (sx - 0.45 * s, sy - 1.0 * s), (sx, sy - 0.85 * s),
                (sx + 0.45 * s, sy - 1.0 * s), (sx + 0.95 * s, sy - 0.85 * s),
                (sx + 0.95 * s, sy + 0.15 * s), (sx + 0.55 * s, sy + 0.7 * s), (sx, sy + 1.15 * s),
                (sx - 0.55 * s, sy + 0.7 * s), (sx - 0.95 * s, sy + 0.15 * s)]

    def draw_virus(self, sc, sx, sy, R, pal, ext=8, phase=0.0, n=10, style=0):
        """Virus mit Stacheln. pal = (Körper, Stacheln, Rand, Kern).  style: 0 klassisch, 1 Stern, 2 Krake"""
        body, spike, rim, core = pal
        t = self.t
        sx, sy, R = int(sx), int(sy), int(R)
        if style == 1:                                   # STERN: rotierende Zacken + Orbit-Punkte
            for i in range(8):
                a = t * 0.8 + phase + i * math.pi / 4
                ln = R + ext + 6 + 3 * math.sin(t * 5 + i + phase)
                pts = [(sx + math.cos(a - 0.30) * R * 0.75, sy + math.sin(a - 0.30) * R * 0.75),
                       (sx + math.cos(a) * ln, sy + math.sin(a) * ln),
                       (sx + math.cos(a + 0.30) * R * 0.75, sy + math.sin(a + 0.30) * R * 0.75)]
                pygame.draw.polygon(sc, spike, pts)
                pygame.draw.polygon(sc, rim, pts, 1)
            rb = int(R * (0.92 + 0.05 * math.sin(t * 6 + phase)))
            pygame.draw.circle(sc, body, (sx, sy), rb)
            pygame.draw.circle(sc, rim, (sx, sy), rb, 2)
            pygame.draw.circle(sc, core, (sx, sy), max(2, int(R * 0.6)))
            for i in range(3):
                a = -t * 2.2 + phase + i * 2.094
                pygame.draw.circle(sc, rim, (int(sx + math.cos(a) * R * 0.38), int(sy + math.sin(a) * R * 0.38)),
                                   max(1, R // 7))
            return
        if style == 2:                                   # KRAKE: wabbelnde Tentakel + Augen
            for i in range(8):
                a0 = t * 0.4 + phase + i * math.pi / 4
                pts = []
                for k in range(7):
                    rr = R * 0.55 + k * (R * 0.55 + ext) / 6
                    a = a0 + math.sin(t * 4 + i + k * 0.7 + phase) * 0.42 * k / 6
                    pts.append((sx + math.cos(a) * rr, sy + math.sin(a) * rr))
                pygame.draw.lines(sc, spike, False, pts, 3)
                pygame.draw.circle(sc, rim, (int(pts[-1][0]), int(pts[-1][1])), 3)
            rb = int(R * (1 + 0.05 * math.sin(t * 5 + phase)))
            pygame.draw.circle(sc, body, (sx, sy), rb)
            pygame.draw.circle(sc, rim, (sx, sy), rb, 2)
            for ex in (-1, 1):
                ox = sx + ex * R // 3
                pygame.draw.circle(sc, (255, 255, 255), (ox, sy - R // 8), max(2, R // 4))
                pygame.draw.circle(sc, core, (ox + int(2 * math.sin(t * 2)), sy - R // 8), max(1, R // 8))
            return
        for i in range(n):
            a = t * 0.9 + phase + i * 2 * math.pi / n
            ca, sa = math.cos(a), math.sin(a)
            r1 = R + ext + 2 * math.sin(t * 6 + i + phase)
            pygame.draw.line(sc, spike, (sx + ca * R * 0.8, sy + sa * R * 0.8),
                             (sx + ca * r1, sy + sa * r1), 2)
            pygame.draw.circle(sc, spike, (int(sx + ca * r1), int(sy + sa * r1)), 3)
        rb = int(R * (1 + 0.06 * math.sin(t * 7 + phase)))
        pygame.draw.circle(sc, body, (sx, sy), rb)
        pygame.draw.circle(sc, rim, (sx, sy), rb, 2)
        pygame.draw.circle(sc, core, (sx, sy), max(2, int(R * 0.55)))
        pygame.draw.circle(sc, (255, 215, 205), (sx - R // 3, sy - R // 3), max(1, R // 5))

    def draw_shield(self, sc, sx, sy, s, pal, phase=0.0, mark="scan"):
        """Wappenschild. pal = (Füllung, Rand, Innen, Innenrand); mark: Scan-Linie oder Kreuz."""
        fill, rim, inner, inner_rim = pal
        pts = self.shield_pts(sx, sy, s)
        pygame.draw.polygon(sc, fill, pts)
        pygame.draw.polygon(sc, rim, pts, 2)
        ip = self.shield_pts(sx, sy, s * 0.62)
        pygame.draw.polygon(sc, inner, ip)
        pygame.draw.polygon(sc, inner_rim, ip, 1)
        k = s / 13.0
        if mark == "scan":
            sy2 = sy + math.sin(self.t * 3 + phase) * 7 * k           # grüne Scan-Linie
            pygame.draw.line(sc, (90, 255, 150), (sx - 7 * k, sy2), (sx + 7 * k, sy2), 2)
            pygame.draw.circle(sc, (255, 255, 255), (int(sx), int(sy - 1)), 2)
        else:                                                         # Kreuz-Emblem
            pygame.draw.line(sc, (255, 255, 255), (sx - 6 * k, sy), (sx + 6 * k, sy), 3)
            pygame.draw.line(sc, (255, 255, 255), (sx, sy - 7 * k), (sx, sy + 7 * k), 3)

    def draw_enemy(self, sc, e, ox, oy):
        sx, sy = e.x - ox, e.y - oy
        if sx < -40 or sx > W + 40 or sy < -40 or sy > H + 40:
            return
        t = self.t
        virus = self.mode == 1                           # Schild-Modus: die Gegner sind Viren

        def body(fill, rim, inner, s=13):
            if virus:
                c = (int(sx), int(sy))
                pygame.draw.circle(sc, fill, c, int(s))
                pygame.draw.circle(sc, rim, c, int(s), 2)
                if inner is not None:
                    pygame.draw.circle(sc, inner, c, int(s * 0.6))
            else:
                pts = self.shield_pts(sx, sy, s)
                pygame.draw.polygon(sc, fill, pts)
                pygame.draw.polygon(sc, rim, pts, 2)
                if inner is not None:
                    pygame.draw.polygon(sc, inner, self.shield_pts(sx, sy, s * 0.62))

        if e.delete_t > 0:                               # Löschung läuft: Virus wird zerlegt
            frac = clamp(e.delete_t / DELETE_TIME, 0.0, 1.0)
            body((18, 70, 60), (90, 255, 200), (6, 24, 20), 13 * (0.55 + 0.45 * frac))
            for _ in range(3):
                a, ln = random.uniform(0, 6.283), random.uniform(8, 18)
                pygame.draw.line(sc, (90, 255, 200), (sx, sy), (sx + math.cos(a) * ln, sy + math.sin(a) * ln), 1)
            pygame.draw.arc(sc, (90, 255, 200), (int(sx) - 24, int(sy) - 24, 48, 48), math.pi / 2,
                            math.pi / 2 + 2 * math.pi * frac, 3)
            return
        if e.offline:                                    # REBOOT FAILURE: beschädigt, dunkel, raucht
            if virus:
                for i in range(8):                       # abgebrochene Stacheln
                    a = i * math.pi / 4 + 0.3
                    ln = 15 + (i % 3) * 2
                    pygame.draw.line(sc, (60, 66, 84), (sx + math.cos(a) * 9, sy + math.sin(a) * 9),
                                     (sx + math.cos(a) * ln, sy + math.sin(a) * ln), 2)
            body((34, 42, 62), (85, 95, 125), None)
            crack = (8, 10, 18)
            pygame.draw.lines(sc, crack, False, [(sx - 2, sy - 12), (sx + 3, sy - 4), (sx - 3, sy + 2),
                                                 (sx + 2, sy + 11)], 2)
            pygame.draw.line(sc, crack, (sx + 3, sy - 4), (sx + 9, sy - 1), 2)
            rf = clamp(e.off_age / REPAIR_TIME, 0.0, 1.0)      # Reparatur-Fortschritt als Ring
            pygame.draw.arc(sc, (120, 255, 200), (int(sx) - 21, int(sy) - 21, 42, 42), math.pi / 2,
                            math.pi / 2 + 2 * math.pi * rf, 2)
            ph = (t * 0.8 + e.ph) % 1.0                  # aufsteigender Rauch
            pygame.draw.circle(sc, (75, 80, 98), (int(sx + 4 * math.sin(t * 2 + e.ph)), int(sy - 16 - ph * 24)),
                               int(2 + ph * 4), 1)
            return
        if e.stun > 0:                                   # lahmgelegt
            warn = e.stun < 3 and int(t * 8) % 2 == 0    # Neustart-Warnung
            body((255, 170, 40) if warn else (44, 70, 125), (150, 190, 255), (12, 20, 45))
            pygame.draw.line(sc, (150, 190, 255), (sx - 4, sy - 4), (sx + 4, sy + 4), 2)   # X
            pygame.draw.line(sc, (150, 190, 255), (sx + 4, sy - 4), (sx - 4, sy + 4), 2)
            for _ in range(2):                           # Funken
                a, ln = random.uniform(0, 6.283), random.uniform(6, 16)
                pygame.draw.line(sc, (170, 230, 255), (sx, sy),
                                 (sx + math.cos(a) * ln, sy + math.sin(a) * ln), 1)
            frac = clamp(e.stun / e.stun_max, 0.01, 1.0)
            pygame.draw.arc(sc, (120, 200, 255), (int(sx) - 22, int(sy) - 22, 44, 44),
                            math.pi / 2, math.pi / 2 + 2 * math.pi * frac, 2)
            return
        if e.boot > 0 and int(t * 14) % 2 == 0:          # frisch repariert: flackert
            return
        sc.blit(self.glow["dr_h" if e.hunter else ("dr_r" if virus else "dr_b")], (int(sx) - 34, int(sy) - 34),
                special_flags=pygame.BLEND_RGB_ADD)
        chase = e.chasing
        if virus:                                        # online: roter (Jäger: violetter) Virus
            if e.hunter:
                pal = PAL_VIRUS_H_CHASE if chase else PAL_VIRUS_H
            else:
                pal = PAL_VIRUS_E_CHASE if chase else PAL_VIRUS_E
            r = 12 + (1.4 * math.sin(t * 8 + e.ph) if chase else 0.5 * math.sin(t * 3 + e.ph))
            self.draw_virus(sc, sx, sy, r, pal, ext=10 if chase else 6, phase=e.ph)
            if chase:
                pygame.draw.circle(sc, (230, 120, 255) if e.hunter else (255, 90, 100),
                                   (int(sx), int(sy)), int(27 + 4 * math.sin(t * 10)), 1)
        else:                                            # online: blaues (Jäger: violettes) Schild
            if e.hunter:
                pal = PAL_SHIELD_H_CHASE if chase else PAL_SHIELD_H
            else:
                pal = PAL_SHIELD_E_CHASE if chase else PAL_SHIELD_E
            s = 13 + (1.6 * math.sin(t * 8 + e.ph) if chase else 0.6 * math.sin(t * 3 + e.ph))
            self.draw_shield(sc, sx, sy, s, pal, e.ph)
            for i in range(2):
                a = t * 3 + e.ph + i * math.pi
                pygame.draw.circle(sc, pal[3], (int(sx + math.cos(a) * 21), int(sy + math.sin(a) * 21)), 3)
            if chase:
                pygame.draw.circle(sc, (190, 130, 255) if e.hunter else (90, 180, 255),
                                   (int(sx), int(sy)), int(25 + 4 * math.sin(t * 10)), 1)
        if e.alert_t > 0:
            img = self.f_mid.render("!", True, (255, 70, 90))
            sc.blit(img, (int(sx - img.get_width() / 2), int(sy - 48)))

    def draw_trap(self, sc, tr, ox, oy):
        sx, sy = int(tr.x - ox), int(tr.y - oy)
        if sx < -50 or sx > W + 50 or sy < -50 or sy > H + 50:
            return
        if tr.life < 8 and int(self.t * 6) % 2 == 0:
            return
        armed = tr.arm <= 0
        col = (255, 170, 60) if armed else (150, 110, 60)
        if armed:
            sc.blit(self.glow["trap"], (sx - 40, sy - 40), special_flags=pygame.BLEND_RGB_ADD)
        a0 = self.t * 0.6
        pts = [(sx + math.cos(k * 1.0472 + a0) * 15, sy + math.sin(k * 1.0472 + a0) * 15) for k in range(6)]
        pygame.draw.polygon(sc, (30, 18, 6), pts)
        pygame.draw.polygon(sc, col, pts, 2)
        pygame.draw.circle(sc, col, (sx, sy), int(5 + 2 * math.sin(self.t * 6)), 2 if armed else 1)
        if armed:
            for k in range(3):
                a = -a0 * 2 + k * 2.094
                pygame.draw.line(sc, col, (sx + math.cos(a) * 7, sy + math.sin(a) * 7),
                                 (sx + math.cos(a) * 12, sy + math.sin(a) * 12), 2)

    def draw_decoy(self, sc, d, ox, oy):
        sx, sy = int(d.x - ox), int(d.y - oy)
        if sx < -60 or sx > W + 60 or sy < -60 or sy > H + 60:
            return
        col = self.dim((90, 230, 255), 0.6 + 0.4 * random.random())
        sc.blit(self.glow["decoy"], (sx - 46, sy - 46), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.ellipse(sc, col, (sx - 22, sy + 8, 44, 14), 2)
        pygame.draw.ellipse(sc, self.dim(col, 0.5), (sx - 14, sy + 11, 28, 8), 1)
        if self.mode == 1:
            pygame.draw.polygon(sc, col, self.shield_pts(sx, sy - 4, 13), 2)
        else:
            pygame.draw.circle(sc, col, (sx, sy - 4), 12, 2)
            for k in range(8):
                a = self.t + k * math.pi / 4
                pygame.draw.line(sc, col, (sx + math.cos(a) * 13, sy - 4 + math.sin(a) * 13),
                                 (sx + math.cos(a) * 19, sy - 4 + math.sin(a) * 19), 2)
        for k in range(-14, 14, 4):
            pygame.draw.line(sc, self.dim(col, 0.5), (sx - 12, sy + k), (sx + 12, sy + k), 1)
        frac = clamp(d.life / DECOY_TIME, 0.0, 1.0)
        pygame.draw.arc(sc, col, (sx - 26, sy - 30, 52, 52), math.pi / 2, math.pi / 2 + 2 * math.pi * frac, 2)

    def draw_rings(self, sc, ox, oy):
        for x, y, maxr, life, mx, col in self.rings:
            k = 1 - life / mx
            r = int(maxr * (1 - (1 - k) ** 3))
            if r < 3:
                continue
            a = life / mx
            for w, f in ((8, 0.22), (4, 0.55), (1, 1.0)):
                pygame.draw.circle(sc, self.dim(col, f * a), (int(x - ox), int(y - oy)), r, min(w, r))

    def draw_bolt(self, sc, b, ox, oy):
        pts = [(int(x - ox), int(y - oy)) for x, y in b.hist] + [(int(b.x - ox), int(b.y - oy))]
        n = len(pts)
        for i in range(1, n):
            pygame.draw.line(sc, self.dim((70, 190, 255), i / n), pts[i - 1], pts[i], max(1, int(1 + 8 * i / n)))
        bx, by = pts[-1]
        pygame.draw.circle(sc, (70, 190, 255), (bx, by), 9)
        pygame.draw.circle(sc, (230, 255, 255), (bx, by), 4)

    def draw_pickup(self, sc, it, ox, oy):
        sx = it.x - ox
        sy = it.y - oy + math.sin(self.t * 3 + it.ph) * 3
        if sx < -30 or sx > W + 30 or sy < -30 or sy > H + 30:
            return
        col = PICKUP_INFO[it.kind][1]
        r = 16 + 2 * math.sin(self.t * 4 + it.ph)
        pygame.draw.circle(sc, col, (int(sx), int(sy)), int(r), 2)
        a = self.t * 1.5 + it.ph
        for i in range(3):
            ang = a + i * 2.094
            pygame.draw.circle(sc, col, (int(sx + math.cos(ang) * r), int(sy + math.sin(ang) * r)), 3)
        if it.kind == "shield":
            pts = [(sx + math.cos(k * 1.047 + 0.5236) * 9, sy + math.sin(k * 1.047 + 0.5236) * 9)
                   for k in range(6)]
            pygame.draw.polygon(sc, col, pts, 2)
        elif it.kind == "magnet":
            pygame.draw.arc(sc, col, (int(sx) - 7, int(sy) - 6, 14, 14), math.pi, 2 * math.pi, 3)
            pygame.draw.line(sc, col, (sx - 7, sy + 1), (sx - 7, sy - 8), 3)
            pygame.draw.line(sc, col, (sx + 7, sy + 1), (sx + 7, sy - 8), 3)
        elif it.kind == "heart":
            self.draw_heart(sx, sy - 4, 7, True, sc)
        else:
            pts = [(sx + 2, sy - 10), (sx - 6, sy + 2), (sx, sy + 2),
                   (sx - 3, sy + 10), (sx + 6, sy - 3), (sx + 1, sy - 3)]
            pygame.draw.polygon(sc, col, pts)

    def draw_drone_tags(self, ox, oy):
        """Status ueber jeder Drohne: online = SEARCHING, lahm = Fehlerfenster, Loeschung = Loeschfenster."""
        for e in self.enemies:
            sx, sy = int(e.x - ox), int(e.y - oy)
            if sx < -130 or sx > W + 130 or sy < -150 or sy > H + 130:
                continue
            if e.delete_t > 0:
                self.draw_delete_window(e, sx, sy)
            elif e.offline or e.stun > 0:
                self.draw_error_window(e, sx, sy)
            else:
                self.draw_scan_tag(e, sx, sy)
            if self.mode == 1 and e.scan > 0 and e.delete_t <= 0:
                self.draw_scan_bar(e, sx, sy)

    def draw_scan_bar(self, e, sx, sy):
        self.hud_bar(sx - 46, sy + 28, 92, 10, e.scan / SCAN_TIME, (110, 230, 255))
        self.text(self.screen, f"SCAN {e.scan:.1f}/{SCAN_TIME:.0f}s", self.f_key, (200, 245, 255), (sx, sy + 48),
                  glow=False)

    def draw_scan_zones(self, sc, ox, oy):
        """Gestrichelter Scan-Kreis um jeden Virus (Schild-Modus) + Fortschrittsbogen."""
        p, t = self.player, self.t
        R = int(SCAN_RADIUS)
        for e in self.enemies:
            if e.delete_t > 0:
                continue
            sx, sy = int(e.x - ox), int(e.y - oy)
            if sx < -R or sx > W + R or sy < -R or sy > H + R:
                continue
            near = math.hypot(e.x - p.x, e.y - p.y) < SCAN_RADIUS
            col = (110, 230, 255) if near else (55, 110, 150)
            rect = (sx - R, sy - R, 2 * R, 2 * R)
            for i in range(0, 24, 2):
                a0 = i * math.pi / 12 + t * 0.3
                pygame.draw.arc(sc, col, rect, a0, a0 + 0.22, 2)
            if e.scan > 0:
                pygame.draw.arc(sc, (170, 250, 255), (sx - R + 6, sy - R + 6, 2 * R - 12, 2 * R - 12),
                                math.pi / 2, math.pi / 2 + 2 * math.pi * clamp(e.scan / SCAN_TIME, 0.0, 1.0), 4)

    def draw_delete_window(self, e, sx, sy):
        """Terminal-Fenster: LOESCHUNG laeuft (30 s) mit Fortschrittsbalken."""
        sc, t = self.screen, self.t
        col = (90, 255, 200)
        dim = self.dim(col, 0.6)
        frac = 1 - clamp(e.delete_t / DELETE_TIME, 0.0, 1.0)
        age = DELETE_TIME - e.delete_t
        pop = clamp(age / 0.25, 0.0, 1.0)
        ease = 1 - (1 - pop) ** 3
        w, h = 196, 112
        hh, ww = max(20, int(h * ease)), int(w * (0.55 + 0.45 * ease))
        x0 = int(clamp(sx - ww // 2, 4, W - ww - 4))
        y0 = max(4, sy - 28 - hh)
        pygame.draw.line(sc, dim, (int(clamp(sx, x0 + 8, x0 + ww - 8)), y0 + hh), (sx, sy - 26), 1)
        pygame.draw.circle(sc, col, (sx, sy - 26), 2)
        pygame.draw.rect(sc, (0, 0, 0), (x0 + 4, y0 + 4, ww, hh))
        pygame.draw.rect(sc, (0, 20, 14), (x0, y0, ww, hh))
        pygame.draw.rect(sc, self.dim(col, 0.35), (x0 - 3, y0 - 3, ww + 6, hh + 6), 1)
        pygame.draw.rect(sc, col, (x0, y0, ww, hh), 2)
        pygame.draw.rect(sc, col, (x0, y0, ww, 18))
        if pop < 1.0:
            return
        dark = (0, 24, 16)
        self.text(sc, f"VIRUS_{e.uid % 100:02d}.EXE", self.f_tiny, dark, (x0 + 8, y0 + 9), "midleft", glow=False)
        self.text(sc, f"{max(0.0, e.delete_t):.0f}s", self.f_tiny, dark, (x0 + w - 8, y0 + 9), "midright", glow=False)
        self.text(sc, "LÖSCHUNG", self.f_mid, col, (x0 + w // 2, y0 + 40))
        self.text(sc, "VIRUS WIRD ENTFERNT", self.f_tiny, dim, (x0 + w // 2, y0 + 62), glow=False)
        msgs = ("> rm -rf virus.exe", "> shredding sectors", "> purging memory", "> quarantine OK")
        ph = t * 0.6 + e.ph
        msg = msgs[int(ph) % len(msgs)]
        shown = msg[:int((ph % 1.0) * len(msg) * 1.6)] + ("_" if int(t * 4) % 2 == 0 else "")
        self.text(sc, shown, self.f_tiny, self.dim(col, 0.9), (x0 + 10, y0 + 80), "midleft", glow=False)
        bx, by, bw, bh = x0 + 10, y0 + h - 20, w - 20, 14
        pygame.draw.rect(sc, (8, 40, 30), (bx, by, bw, bh))
        pygame.draw.rect(sc, dim, (bx, by, int(bw * frac), bh))
        pygame.draw.rect(sc, col, (bx, by, bw, bh), 1)
        self.text(sc, f"{int(frac * 100)}%", self.f_tiny, (255, 255, 255), (bx + bw // 2, by + bh // 2), glow=False)

    def draw_scan_tag(self, e, sx, sy):
        sc = self.screen
        if self.mode == 1:
            label = "HUNTER VIRUS" if e.hunter else "INFECTING SYSTEM"
            col, bg, off = (255, 90, 110), (26, 4, 8), (120, 30, 45)
        elif e.hunter:
            label, col, bg, off = "HUNTER DRONE", (200, 130, 255), (22, 6, 34), (90, 50, 120)
        else:
            label, col, bg, off = "SEARCHING ANOMALIE", (80, 255, 140), (3, 22, 10), (30, 110, 60)
        if e.boot > 0:
            label, col, bg, off = "NEUSTART ...", (255, 200, 80), (30, 20, 2), (110, 80, 20)
        elif e.lured:
            label, col, bg, off = "KÖDER FOLGEN", (90, 230, 255), (3, 20, 28), (30, 90, 110)
        w = self.f_tiny.size(label)[0] + 18
        x0, y0 = sx - w // 2, sy - 70
        pygame.draw.rect(sc, bg, (x0, y0, w, 20))
        pygame.draw.rect(sc, col, (x0, y0, w, 20), 1)
        blink = int(self.t * 3 + e.ph * 3) % 2 == 0
        pygame.draw.rect(sc, col if blink else off, (x0 + 4, y0 + 7, 5, 6))   # Status-LED
        self.text(sc, label, self.f_tiny, col, (x0 + 13, y0 + 10), "midleft", glow=False)

    def draw_error_window(self, e, sx, sy):
        """Terminal-Fenster: ERROR 404 -> REBOOTING... -> bei Defekt REBOOT FAILURE / DROHNE DAMAGED."""
        sc, t = self.screen, self.t
        virus = self.mode == 1
        offline = e.offline
        reboot = (not offline) and e.stun < 3
        who = "VIRUS" if virus else "DRONE"
        if offline:
            col, title, sub = (255, 60, 90), "REBOOT FAILURE", f"AUTO-REPAIR IN {max(0.0, REPAIR_TIME - e.off_age):.0f}s"
        elif reboot:
            col, title, sub = (255, 175, 45), "REBOOTING...", "RESTART SEQUENCE"
        else:
            col, title, sub = (255, 55, 65), "ERROR 404", f"{who} NOT FOUND"
        if offline and int(t * 7 + e.ph * 5) % 9 == 0:       # flackerndes Fenster
            return
        age = e.off_age if offline else e.stun_max - e.stun   # Sekunden seit dem Treffer
        if age < 0:
            age = 99.0
        pop = clamp(age / 0.25, 0.0, 1.0)                     # Aufpop-Animation
        fresh = (not offline) and age < 0.7                   # Glitch direkt nach dem Treffer
        glitch = random.random() < (0.85 if fresh else (0.22 if offline else 0.05))
        dx = random.choice((-7, -4, 4, 7)) if glitch else 0
        w, h = 196, 124
        ease = 1 - (1 - pop) ** 3
        hh = max(20, int(h * ease))
        ww = int(w * (0.55 + 0.45 * ease))
        x0 = int(clamp(sx - ww // 2 + dx, 4, W - ww - 4))
        y0 = max(4, sy - 28 - hh)
        dim = tuple(int(c * 0.65) for c in col)
        pygame.draw.line(sc, dim, (int(clamp(sx, x0 + 8, x0 + ww - 8)), y0 + hh), (sx, sy - 26), 1)
        pygame.draw.circle(sc, col, (sx, sy - 26), 2)
        pygame.draw.rect(sc, (0, 0, 0), (x0 + 4, y0 + 4, ww, hh))                       # Schatten
        pygame.draw.rect(sc, (22, 0, 8), (x0, y0, ww, hh))
        pygame.draw.rect(sc, tuple(int(c * 0.35) for c in col), (x0 - 3, y0 - 3, ww + 6, hh + 6), 1)
        pygame.draw.rect(sc, col, (x0, y0, ww, hh), 2)
        pygame.draw.rect(sc, col, (x0, y0, ww, 18))                                     # Titelleiste
        if pop < 1.0:
            return
        yy = y0 + 20 + int((t * 35 + e.ph * 50) % (h - 24))                             # Scanline
        pygame.draw.line(sc, (70, 8, 18), (x0 + 2, yy), (x0 + w - 3, yy))
        dark = (20, 0, 6)
        self.text(sc, f"{who}_{e.uid % 100:02d}.SYS", self.f_tiny, dark, (x0 + 8, y0 + 9), "midleft", glow=False)
        if not offline:
            self.text(sc, f"{max(0.0, e.stun):.0f}s", self.f_tiny, dark, (x0 + w - 54, y0 + 9), "midright",
                      glow=False)
        for k in range(3):                                                              # Fensterknöpfe _ [] X
            r = pygame.Rect(x0 + w - 6 - 14 * (3 - k), y0 + 3, 12, 12)
            pygame.draw.rect(sc, dark, r)
            if k == 0:
                pygame.draw.line(sc, col, (r.x + 3, r.bottom - 4), (r.right - 4, r.bottom - 4), 2)
            elif k == 1:
                pygame.draw.rect(sc, col, r.inflate(-6, -6), 1)
            else:
                pygame.draw.line(sc, col, (r.x + 3, r.y + 3), (r.right - 4, r.bottom - 4), 1)
                pygame.draw.line(sc, col, (r.right - 4, r.y + 3), (r.x + 3, r.bottom - 4), 1)
        ix, iy = x0 + 24, y0 + 44                                                       # Warndreieck
        tri = [(ix, iy - 14), (ix + 15, iy + 11), (ix - 15, iy + 11)]
        pygame.draw.polygon(sc, col if int(t * 4 + e.ph) % 2 == 0 else dim, tri)
        self.text(sc, "!", self.f_small, (22, 0, 8), (ix, iy + 2), glow=False)
        cx = x0 + 24 + (w - 24) // 2
        font = self.f_mid if title == "ERROR 404" else self.f_small
        ty = y0 + 40
        if glitch:                                                                      # Farbversatz
            self.text(sc, title, font, (0, 255, 255), (cx + 3, ty), glow=False)
            self.text(sc, title, font, (255, 0, 200), (cx - 3, ty), glow=False)
            for _ in range(2):
                gy = y0 + 20 + random.randrange(h - 32)
                pygame.draw.rect(sc, random.choice(((0, 255, 255), (255, 0, 200))), (x0 + 2, gy, w - 4, 2))
        self.text(sc, title, font, col, (cx, ty))
        self.text(sc, sub, self.f_tiny, dim, (cx, y0 + 64), glow=False)
        # Terminal-Zeile mit Schreibmaschinen-Effekt
        if offline:
            msgs = (f"> HW FAULT 0x{(0xA0 + e.uid * 7) % 256:02X}", "> core: DEAD", "> nanobots: DEPLOYED",
                    f"> repair ETA {max(0.0, REPAIR_TIME - e.off_age):.0f}s")
        elif reboot:
            msgs = ("> boot sector OK", "> loading kernel", "> init motors", "> sync uplink")
        else:
            msgs = ("> ping ... TIMEOUT", "> signal lost 0x404", "> retry link ...", "> NO CARRIER")
        ph = t * 0.6 + e.ph
        msg = msgs[int(ph) % len(msgs)]
        shown = msg[:int((ph % 1.0) * len(msg) * 1.6)]
        cur = "_" if int(t * 4) % 2 == 0 else ""
        img = self.f_tiny.render(shown + cur, True, tuple(int(c * 0.9) for c in col))
        sc.blit(img, (x0 + 10, y0 + 84 - img.get_height() // 2))
        # Fortschrittsbalken
        bx, by, bw, bh = x0 + 10, y0 + h - 20, w - 20, 14
        pygame.draw.rect(sc, (50, 10, 20), (bx, by, bw, bh))
        if offline:                                                                     # Reparatur-Balken
            frac = clamp(e.off_age / REPAIR_TIME, 0.0, 1.0)
            pygame.draw.rect(sc, dim, (bx, by, int(bw * frac), bh))
            label = f"REPARATUR {int(frac * 100)}%"
        else:
            frac = 1 - clamp(e.stun / e.stun_max, 0.0, 1.0)
            pygame.draw.rect(sc, dim, (bx, by, int(bw * frac), bh))
            label = f"{int(frac * 100)}%"
        pygame.draw.rect(sc, col, (bx, by, bw, bh), 1)
        self.text(sc, label, self.f_tiny, (0, 0, 0), (bx + bw // 2 + 1, by + bh // 2 + 1), glow=False)
        self.text(sc, label, self.f_tiny, (255, 255, 255), (bx + bw // 2, by + bh // 2), glow=False)

    def draw_effects(self):
        p, sc = self.player, self.screen
        items = []
        if p.shield:
            items.append((self.pick_name("shield") + " AKTIV", PICKUP_INFO["shield"][1], 1.0))
        if p.magnet_t > 0:
            items.append((f"MAGNET {p.magnet_t:.0f}s", PICKUP_INFO["magnet"][1], p.magnet_t / 10.0))
        if p.oc_t > 0:
            items.append((f"OVERCLOCK {p.oc_t:.0f}s", PICKUP_INFO["overclock"][1], p.oc_t / 10.0))
        for i, (txt, col, f) in enumerate(items):
            y = H - 62 - i * 36
            self.hud_panel(W // 2 - 105, y, 210, 30, col, cut=7, alpha=170)
            self.text(sc, txt, self.f_tiny, col, (W // 2, y + 11), glow=False)
            self.hud_bar(W // 2 - 90, y + 21, 180, 4, f, col)

    def draw_player(self, sc, ox, oy):
        p = self.player
        tcol = (45, 110, 165) if self.mode == 1 else (130, 25, 40)
        for x, y, life in p.trail:
            r = max(1, int(p.R * (life / 0.30) * 0.8))
            pygame.draw.circle(sc, tcol, (int(x - ox), int(y - oy)), r)
        if p.inv > 0 and int(p.inv * 14) % 2 == 0:
            return
        sx, sy = int(p.x - ox), int(p.y - oy)
        dash = p.dash_t > 0
        t = self.t
        extra = 0
        sc.blit(self.glow["pl_c" if self.mode == 1 else "pl_r"], (sx - 46, sy - 46), special_flags=pygame.BLEND_RGB_ADD)
        if self.mode == 1:                               # Schild-Modus: du bist das Schild
            pal = PAL_SHIELD_P_DASH if dash else PAL_SHIELD_P
            self.draw_shield(sc, sx, sy, 15 + (3 if dash else 0) + 0.8 * math.sin(t * 6), pal, mark="cross")
            for i in range(3):
                a = t * 2.2 + i * 2.094
                pygame.draw.circle(sc, pal[3], (int(sx + math.cos(a) * 27), int(sy + math.sin(a) * 27)), 3)
            extra = 6
            frac = clamp(p.energy / ENERGY_MAX, 0.0, 1.0)           # Energie-Ring um das Schild
            ecol = (110, 230, 255) if p.energy >= BLOCK_COST else (255, 150, 100)
            pygame.draw.arc(sc, ecol, (sx - 36, sy - 36, 72, 72), math.pi / 2, math.pi / 2 + 2 * math.pi * frac, 3)
        else:                                            # Virus-Modus: du bist der Virus
            self.draw_virus(sc, sx, sy, p.R, PAL_VIRUS_DASH if dash else PAL_VIRUS_P, ext=12 if dash else 8)
        if p.shield:
            pygame.draw.circle(sc, (90, 220, 255), (sx, sy), p.R + 11 + extra + int(math.sin(self.t * 6)), 2)
            pygame.draw.circle(sc, (50, 130, 170), (sx, sy), p.R + 15 + extra, 1)
        if p.magnet_t > 0:
            pygame.draw.circle(sc, (255, 100, 225), (sx, sy), int(30 + (self.t * 90) % 60), 1)

    def draw_particles(self, sc, ox, oy):
        for x, y, vx, vy, life, mx, col, size in self.particles:
            r = max(1, int(size * life / mx))
            pygame.draw.circle(sc, col, (int(x - ox), int(y - oy)), r)

    def bloom(self, sc):
        small = pygame.transform.smoothscale(sc, (W // 4, H // 4))
        tiny = pygame.transform.smoothscale(small, (W // 16, H // 16))
        b1 = pygame.transform.smoothscale(small, (W, H))
        b2 = pygame.transform.smoothscale(tiny, (W, H))
        b1.fill((150, 150, 150), special_flags=pygame.BLEND_RGB_MULT)
        b2.fill((175, 175, 175), special_flags=pygame.BLEND_RGB_MULT)
        sc.blit(b1, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        sc.blit(b2, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def apply_lights(self, sc, lights):
        self.dark.fill((255, 255, 255) if self.cheat["light"] else AMBIENT)
        for x, y, name in lights:
            spr = self.light[name]
            hw = spr.get_width() // 2
            if -hw < x < W + hw and -hw < y < H + hw:
                self.dark.blit(spr, (int(x - hw), int(y - hw)), special_flags=pygame.BLEND_RGB_ADD)
        sc.blit(self.dark, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    # ---------- Zeichnen: Szenen
    def draw_game(self):
        sc, lv, p = self.scene, self.level, self.player
        sc.fill(BG)
        shk = self.shake if self.opt["shake"] else 0.0
        ox = self.camx + random.uniform(-1, 1) * shk
        oy = self.camy + random.uniform(-1, 1) * shk
        self.draw_stars(sc, ox, oy)
        self.draw_world(sc, ox, oy)
        self.draw_exit(sc, ox, oy)
        if self.mode == 1:
            self.draw_scan_zones(sc, ox, oy)
        for tr in self.traps:
            self.draw_trap(sc, tr, ox, oy)
        for c in self.crystals:
            if c.alive:
                self.draw_crystal(sc, c, ox, oy)
        for it in self.pickups:
            if it.alive:
                self.draw_pickup(sc, it, ox, oy)
        if self.decoy is not None:
            self.draw_decoy(sc, self.decoy, ox, oy)
        for e in self.enemies:
            self.draw_enemy(sc, e, ox, oy)
        for b in self.bolts:
            self.draw_bolt(sc, b, ox, oy)
        self.draw_particles(sc, ox, oy)
        self.draw_player(sc, ox, oy)
        self.draw_rings(sc, ox, oy)
        for x, y, s, life, col in self.popups:
            img = self.f_mid.render(s, True, col)
            sc.blit(img, (int(x - ox - img.get_width() / 2), int(y - oy)))

        pl_light = "player_blue" if self.mode == 1 else "player"
        en_light = "enemy_red" if self.mode == 1 else "enemy"
        lights = [(p.x - ox, p.y - oy, pl_light),
                  ((lv.exit[0] + 0.5) * TS - ox, (lv.exit[1] + 0.5) * TS - oy,
                   "exit" if self.portal_open else "exit_locked")]
        lights += [(c.x - ox, c.y - oy, "crystal") for c in self.crystals if c.alive]
        lights += [(e.x - ox, e.y - oy, "off" if (e.stun > 0 or e.offline) else en_light) for e in self.enemies]
        lights += [(b.x - ox, b.y - oy, "bolt") for b in self.bolts]
        lights += [(it.x - ox, it.y - oy, "pickup") for it in self.pickups if it.alive]
        lights += [(tr.x - ox, tr.y - oy, "trap") for tr in self.traps]
        if self.decoy is not None:
            lights.append((self.decoy.x - ox, self.decoy.y - oy, "decoy"))
        self.apply_lights(sc, lights)
        if self.opt["bloom"]:
            self.bloom(sc)
        self.screen.blit(sc, (0, 0))
        if self.flash > 0:
            self.flash_surf.set_alpha(int(110 * self.flash / 0.3))
            self.screen.blit(self.flash_surf, (0, 0))
        dng = 0.0                                       # Gefahr: roter Rand, wenn ein Jaeger nah ist
        for e in self.enemies:
            if e.chasing and e.stun <= 0 and not e.offline:
                dng = max(dng, 1 - math.hypot(e.x - p.x, e.y - p.y) / (6 * TS))
        if p.lives <= 1 and self.diff()["lives"] > 1 and not self.cheat["god"]:
            dng = max(dng, 0.35 + 0.15 * math.sin(self.t * 5))        # letztes Leben: pulsierender Rand
        if dng > 0:
            self.danger_vig.set_alpha(int(clamp(dng, 0, 1) * (150 + 70 * math.sin(self.t * 9))))
            self.screen.blit(self.danger_vig, (0, 0))
        self.draw_drone_tags(ox, oy)
        self.draw_hud()

    # ---------- HUD-Bausteine
    @staticmethod
    def dim(col, f):
        return tuple(int(c * f) for c in col)

    @staticmethod
    def poly(x, y, w, h, cut):
        """Rechteck mit abgeschraegten Ecken (oben links / unten rechts)."""
        return [(x + cut, y), (x + w, y), (x + w, y + h - cut), (x + w - cut, y + h), (x, y + h), (x, y + cut)]

    def hud_panel(self, x, y, w, h, col, cut=10, alpha=165):
        sc = self.screen
        key = (w, h, cut, alpha)
        bg = self._pc.get(key)
        if bg is None:
            if len(self._pc) > 80:
                self._pc.clear()
            bg = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.polygon(bg, (5, 8, 24, alpha), self.poly(0, 0, w - 1, h - 1, cut))
            for yy in range(3, h - 2, 4):
                pygame.draw.line(bg, (255, 255, 255, 7), (4, yy), (w - 5, yy))
            self._pc[key] = bg
        sc.blit(bg, (x, y))
        pts = self.poly(x, y, w - 1, h - 1, cut)
        pygame.draw.polygon(sc, self.dim(col, 0.28), pts, 3)
        pygame.draw.polygon(sc, self.dim(col, 0.85), pts, 1)
        pygame.draw.line(sc, col, (x + cut, y), (x + cut + 20, y), 3)
        pygame.draw.line(sc, col, (x + w - 1, y + h - 1 - cut - 16), (x + w - 1, y + h - 1 - cut), 3)

    def hud_bar(self, x, y, w, h, frac, col, segs=0):
        sc = self.screen
        frac = clamp(frac, 0.0, 1.0)
        pygame.draw.rect(sc, (12, 16, 38), (x, y, w, h))
        fw = int(w * frac)
        if fw > 0:
            pygame.draw.rect(sc, self.dim(col, 0.6), (x, y, fw, h))
            pygame.draw.rect(sc, col, (x, y, fw, max(1, h // 2)))
            if fw > 3 and h >= 8:
                pygame.draw.rect(sc, (255, 255, 255), (x + fw - 2, y, 2, h))
        if segs > 1:
            for i in range(1, segs):
                xx = x + w * i // segs
                pygame.draw.line(sc, (5, 8, 20), (xx, y), (xx, y + h - 1), 2)
        pygame.draw.rect(sc, self.dim(col, 0.7), (x, y, w, h), 1)

    def keycap(self, cx, cy, label, col):
        w = max(18, self.f_key.size(label)[0] + 10)
        r = pygame.Rect(0, 0, w, 15)
        r.center = (cx, cy)
        pygame.draw.rect(self.screen, (14, 18, 44), r)
        pygame.draw.rect(self.screen, self.dim(col, 0.8), r, 1)
        self.text(self.screen, label, self.f_key, (235, 235, 255), r.center, glow=False)

    def draw_icon(self, kind, cx, cy, col):
        sc = self.screen
        if kind == "shot":
            pygame.draw.circle(sc, col, (cx, cy), 10, 2)
            pygame.draw.line(sc, col, (cx - 17, cy), (cx - 6, cy), 2)
            pygame.draw.line(sc, col, (cx + 6, cy), (cx + 17, cy), 2)
            pygame.draw.line(sc, col, (cx, cy - 17), (cx, cy - 6), 2)
            pygame.draw.line(sc, col, (cx, cy + 6), (cx, cy + 17), 2)
            pygame.draw.circle(sc, col, (cx, cy), 2)
        elif kind == "emp":
            pygame.draw.circle(sc, col, (cx, cy), 17, 1)
            pygame.draw.circle(sc, col, (cx, cy), 12, 1)
            pygame.draw.polygon(sc, col, [(cx + 3, cy - 10), (cx - 5, cy + 1), (cx, cy + 1),
                                          (cx - 3, cy + 10), (cx + 5, cy - 2), (cx + 1, cy - 2)])
        elif kind == "trap":
            pts = [(cx + math.cos(k * 1.0472) * 15, cy + math.sin(k * 1.0472) * 15) for k in range(6)]
            pygame.draw.polygon(sc, col, pts, 2)
            for k in range(3):
                a = k * 2.094 + 0.5
                pygame.draw.line(sc, col, (cx, cy), (cx + math.cos(a) * 9, cy + math.sin(a) * 9), 2)
            pygame.draw.circle(sc, col, (cx, cy), 3)
        elif kind == "decoy":
            pygame.draw.circle(sc, col, (cx, cy - 4), 9, 2)
            pygame.draw.line(sc, col, (cx - 9, cy - 4), (cx - 9, cy + 9), 2)
            pygame.draw.line(sc, col, (cx + 9, cy - 4), (cx + 9, cy + 9), 2)
            pygame.draw.lines(sc, col, False, [(cx - 9, cy + 9), (cx - 4, cy + 5), (cx, cy + 9),
                                               (cx + 4, cy + 5), (cx + 9, cy + 9)], 2)
            pygame.draw.circle(sc, col, (cx - 3, cy - 5), 1)
            pygame.draw.circle(sc, col, (cx + 3, cy - 5), 1)
        else:                                            # dash
            for k in (-7, 3):
                pygame.draw.lines(sc, col, False, [(cx + k - 5, cy - 10), (cx + k + 5, cy), (cx + k - 5, cy + 10)], 3)

    def gadget_slot(self, x, y, sz, icon, col, frac, secs, locked=False, count=None):
        sc = self.screen
        ready = frac <= 0 and not locked
        pts = self.poly(x, y, sz - 1, sz - 1, 9)
        pygame.draw.polygon(sc, (8, 12, 32), pts)
        if ready:
            g = 0.5 + 0.5 * math.sin(self.t * 5)
            pygame.draw.polygon(sc, self.dim(col, 0.18 + 0.14 * g), self.poly(x - 3, y - 3, sz + 5, sz + 5, 11), 3)
        self.draw_icon(icon, x + sz // 2, y + sz // 2, col if ready else self.dim(col, 0.4))
        if frac > 0 and not locked:
            s = pygame.Surface((sz, sz), pygame.SRCALPHA)
            n = max(3, int(36 * frac))
            c = sz / 2.0
            pp = [(c, c)] + [(c + math.cos(-math.pi / 2 + 2 * math.pi * frac * i / n) * sz,
                              c + math.sin(-math.pi / 2 + 2 * math.pi * frac * i / n) * sz) for i in range(n + 1)]
            pygame.draw.polygon(s, (3, 5, 16, 190), pp)
            sc.blit(s, (x, y))
            if secs >= 0.95:
                self.text(sc, f"{secs:.0f}", self.f_mid, (235, 235, 255), (x + sz // 2, y + sz // 2), glow=False)
        pygame.draw.polygon(sc, col if ready else self.dim(col, 0.4), pts, 2)
        if count is not None:
            self.text(sc, str(count), self.f_small, (255, 255, 255) if count else (255, 90, 90),
                      (x + sz - 5, y + 4), "topright", glow=False)

    # ---------- HUD
    def draw_hud(self):
        sc, p, t = self.screen, self.player, self.t
        dd, shield = self.diff(), self.mode == 1
        mcol = MODES[self.mode][1]
        touch = self.touch_mode()
        cx = W // 2
        have, need = self.goal()
        # ---- oben links: Status
        h = 142 + (24 if shield else 0) + (20 if self.cheated else 0)
        self.hud_panel(14, 14, 300, h, mcol)
        x0 = 30
        self.text(sc, f"LEVEL {self.level_no + 1}", self.f_mid, (255, 232, 130), (x0, 24), "topleft", glow=False)
        self.text(sc, f"{MODES[self.mode][0]} | {dd['name']}", self.f_tiny, dd["col"], (300, 36), "midright",
                  glow=False)
        self.text(sc, "PUNKTE", self.f_tiny, (120, 135, 190), (x0, 58), "topleft", glow=False)
        self.text(sc, f"{int(self.disp_score):07d}", self.f_num, (150, 255, 230), (x0, 72), "topleft")
        for i in range(MAX_LIVES):                       # maximal 4 Herzen
            self.draw_heart(x0 + 10 + i * 36, 126, 10, i < p.lives)
        yy = 150
        if shield:
            ok = p.energy >= BLOCK_COST
            self.text(sc, "ENERGIE", self.f_tiny, (120, 200, 255), (x0, yy), "topleft", glow=False)
            self.hud_bar(x0 + 78, yy + 2, 190, 12, p.energy / ENERGY_MAX,
                         (110, 230, 255) if ok else (255, 150, 100), segs=10)
            yy += 24
        if self.cheated:
            self.text(sc, f"ADMIN  {len(self.enemies)} DROHNEN (nicht gewertet)", self.f_tiny, (255, 90, 90),
                      (x0, yy), "topleft", glow=False)
        # ---- oben Mitte: Zeit + Ziel
        self.hud_panel(cx - 100, 12, 200, 40, (140, 150, 255), cut=8)
        self.text(sc, "ZEIT", self.f_tiny, (120, 135, 190), (cx - 86, 32), "midleft", glow=False)
        self.text(sc, f"{self.level_time:6.1f}", self.f_mid, (215, 220, 255), (cx + 90, 32), "midright", glow=False)
        opened = self.portal_open
        gcol = (90, 255, 170) if opened else ((110, 230, 255) if shield else (255, 110, 235))
        pw = 400
        gx = cx - pw // 2
        self.hud_panel(gx, 58, pw, 54, gcol, cut=10)
        dm = (gx + 24, 76)
        pygame.draw.polygon(sc, gcol, [(dm[0], dm[1] - 9), (dm[0] + 6, dm[1]), (dm[0], dm[1] + 9), (dm[0] - 6, dm[1])])
        if opened:
            blink = int(t * 3) % 2 == 0 or self.unlock_t <= 0
            self.text(sc, "PORTAL OFFEN", self.f_small, gcol if blink else self.dim(gcol, 0.5), (gx + 42, 76),
                      "midleft", glow=blink)
            if not shield and self.collected > self.need:
                self.text(sc, f"+{self.collected - self.need} BONUS", self.f_small, (255, 150, 235),
                          (gx + pw - 16, 76), "midright", glow=False)
        elif shield:
            self.text(sc, f"VIREN GELÖSCHT  {have}/{need}", self.f_small, gcol, (gx + 42, 76), "midleft")
            self.text(sc, f"{SCAN_TIME:.0f}s nah bleiben", self.f_tiny, (150, 150, 200), (gx + pw - 16, 76),
                      "midright", glow=False)
        else:
            self.text(sc, f"KRISTALLE  {have}/{need}", self.f_small, gcol, (gx + 42, 76), "midleft")
            self.text(sc, "sammle sie für das Portal", self.f_tiny, (150, 150, 200), (gx + pw - 16, 76),
                      "midright", glow=False)
        self.hud_bar(gx + 16, 92, pw - 32, 12, have / max(1, need), gcol, segs=need if 1 < need <= 40 else 0)
        yy = 120
        if self.combo > 1:
            self.text(sc, f"COMBO x{self.combo}", self.f_small, (255, 220, 90), (cx, yy), "midtop")
            self.hud_bar(cx - 60, yy + 22, 120, 6, self.combo_t / 2.5, (255, 220, 90))
            yy += 38
        if shield and self.chain > 1:
            self.text(sc, f"STOSS-KETTE x{self.chain}", self.f_small, (120, 235, 255), (cx, yy), "midtop")
        # ---- unten links: Gadget-Leiste (PC) oder Touch-Steuerung (Handy)
        if touch:
            self.draw_touch_controls()
        else:
            names = ("SCHUSS", "WELLE" if shield else "EMP", "FALLE", "KÖDER", "STOSS" if shield else "DASH")
            keys = ("LMB", "Q", "R", "C", "SPACE")
            icons = ("shot", "emp", "trap", "decoy", "dash")
            cols = ((255, 120, 230), (110, 230, 255) if shield else (255, 205, 90), (255, 170, 70),
                    (90, 230, 255), (90, 255, 255))
            cds = (p.shoot_cd, p.emp_cd, p.trap_cd, p.decoy_cd, p.dash_cd)
            mx = (SHOT_CD, EMP_CD, TRAP_CD, DECOY_CD, DASH_CD)
            left = TRAP_MAX - len(self.traps)
            self.hud_panel(14, H - 124, 352, 110, (110, 120, 255), cut=10, alpha=170)
            for i in range(5):
                x = 28 + i * 66
                self.text(sc, names[i], self.f_key, self.dim(cols[i], 0.9), (x + 26, H - 108), glow=False)
                self.gadget_slot(x, H - 98, 52, icons[i], cols[i], cds[i] / mx[i], cds[i],
                                 locked=(i == 2 and left <= 0), count=(left if i == 2 else None))
                self.keycap(x + 26, H - 38, keys[i], cols[i])
        self.draw_effects()
        self.draw_compass()
        self.draw_minimap()
        self.draw_crosshair()
        if self.banner > 0:
            a = clamp(self.banner / 0.8, 0, 1)
            self.text(sc, f"LEVEL {self.level_no + 1}", self.f_big,
                      tuple(int(c * a) for c in (255, 240, 150)), (W // 2, H // 2 - 120))
            msg = (f"Lösche {need} Virus{'en' if need != 1 else ''}: bleib {SCAN_TIME:.0f} s in der Nähe, dann startet die Löschung"
                   if shield else f"Sammle {need} Kristalle - dann öffnet sich das Portal")
            self.text(sc, msg, self.f_small, tuple(int(c * a) for c in (200, 200, 255)), (W // 2, H // 2 - 80),
                      glow=False)
        if self.unlock_t > 0:
            a = clamp(self.unlock_t / 0.8, 0, 1)
            self.text(sc, "PORTAL OFFEN", self.f_big, tuple(int(c * a) for c in (90, 255, 170)),
                      (W // 2, H // 2 - 150))
            self.text(sc, "Finde den Ausgang!", self.f_small, tuple(int(c * a) for c in (200, 255, 230)),
                      (W // 2, H // 2 - 108), glow=False)

    def draw_touch_controls(self):
        sc, p = self.screen, self.player
        if self.stick:
            ox, oy, kx, ky = self.stick[1], self.stick[2], self.stick[3], self.stick[4]
            a = 1.0
        else:
            ox = kx = 150
            oy = ky = H - 150
            a = 0.45
        pygame.draw.circle(sc, self.dim((110, 130, 255), 0.55 * a), (int(ox), int(oy)), 80, 2)
        pygame.draw.circle(sc, self.dim((110, 130, 255), 0.30 * a), (int(ox), int(oy)), 40, 1)
        kd = math.hypot(kx - ox, ky - oy)
        if kd > 80:
            kx, ky = ox + (kx - ox) / kd * 80, oy + (ky - oy) / kd * 80
        pygame.draw.circle(sc, self.dim((150, 170, 255), 0.40 * a), (int(kx), int(ky)), 34)
        pygame.draw.circle(sc, self.dim((200, 215, 255), a), (int(kx), int(ky)), 34, 2)
        if not self.stick:
            self.text(sc, "BEWEGEN", self.f_tiny, (150, 160, 230), (150, H - 70), glow=False)
        cds = {"dash": (p.dash_cd, DASH_CD), "shoot": (p.shoot_cd, SHOT_CD), "emp": (p.emp_cd, EMP_CD),
               "trap": (p.trap_cd, TRAP_CD), "decoy": (p.decoy_cd, DECOY_CD)}
        icons = {"dash": "dash", "shoot": "shot", "emp": "emp", "trap": "trap", "decoy": "decoy"}
        for name, cx, cy, r, label, col in TOUCH_BTNS:
            cd, mx = cds.get(name, (0.0, 1.0))
            locked = name == "trap" and len(self.traps) >= TRAP_MAX
            ready = cd <= 0 and not locked
            flash = self.btn_flash.get(name, 0) > 0
            pygame.draw.circle(sc, self.dim(col, 0.45) if flash else (8, 12, 32), (cx, cy), r)
            if ready:
                g = 0.5 + 0.5 * math.sin(self.t * 5)
                pygame.draw.circle(sc, self.dim(col, 0.2 + 0.15 * g), (cx, cy), r + 5, 3)
            if name in icons:
                self.draw_icon(icons[name], cx, cy - 6, col if ready else self.dim(col, 0.4))
                self.text(sc, label, self.f_key, col if ready else self.dim(col, 0.5), (cx, cy + r - 16),
                          glow=False)
            else:
                self.text(sc, label, self.f_small, col, (cx, cy), glow=False)
            if cd > 0 and name in cds:
                s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
                frac = clamp(cd / mx, 0.0, 1.0)
                n = max(3, int(36 * frac))
                pp = [(r, r)] + [(r + math.cos(-math.pi / 2 + 2 * math.pi * frac * i / n) * r,
                                  r + math.sin(-math.pi / 2 + 2 * math.pi * frac * i / n) * r) for i in range(n + 1)]
                pygame.draw.polygon(s, (3, 5, 16, 185), pp)
                sc.blit(s, (cx - r, cy - r))
                if cd >= 0.95:
                    self.text(sc, f"{cd:.0f}", self.f_mid, (235, 235, 255), (cx, cy), glow=False)
            pygame.draw.circle(sc, col if ready else self.dim(col, 0.4), (cx, cy), r, 2)
            if name == "trap":
                n_left = TRAP_MAX - len(self.traps)
                self.text(sc, str(n_left), self.f_small, (255, 255, 255) if n_left else (255, 90, 90),
                          (cx + r - 8, cy - r + 8), glow=False)

    def draw_compass(self):
        if not self.portal_open or self.bigmap:
            return
        lv, sc = self.level, self.screen
        exs = (lv.exit[0] + 0.5) * TS - self.camx
        eys = (lv.exit[1] + 0.5) * TS - self.camy
        if 40 < exs < W - 40 and 40 < eys < H - 40:
            return
        dx, dy = exs - W / 2, eys - H / 2
        k = min((W / 2 - 90) / abs(dx) if dx else 1e9, (H / 2 - 90) / abs(dy) if dy else 1e9)
        ax, ay = W / 2 + dx * k, H / 2 + dy * k
        ang = math.atan2(dy, dx)
        pulse = 1.0 + 0.12 * math.sin(self.t * 6)
        col = (90, 255, 170)
        tip = (ax + math.cos(ang) * 22 * pulse, ay + math.sin(ang) * 22 * pulse)
        l1 = (ax + math.cos(ang + 2.5) * 16, ay + math.sin(ang + 2.5) * 16)
        r1 = (ax + math.cos(ang - 2.5) * 16, ay + math.sin(ang - 2.5) * 16)
        pygame.draw.polygon(sc, self.dim(col, 0.35), [tip, l1, r1])
        pygame.draw.polygon(sc, col, [tip, l1, r1], 2)
        dist = int(math.hypot(dx, dy) / TS)
        self.text(sc, f"PORTAL {dist}", self.f_tiny, col, (ax - math.cos(ang) * 36, ay - math.sin(ang) * 36),
                  glow=False)

    def draw_drone_counter(self, x, y, w):
        sc = self.screen
        on = st = off = dl = 0
        nxt = None
        for e in self.enemies:
            if e.delete_t > 0:
                dl += 1
            elif e.offline:
                off += 1
                rem = REPAIR_TIME - e.off_age
                nxt = rem if nxt is None else min(nxt, rem)
            elif e.stun > 0:
                st += 1
            else:
                on += 1
        ec = self.ecol()
        rows = [("ONLINE", on, ec), ("LAHM", st, (120, 200, 255)), ("DEFEKT", off, (255, 170, 60))]
        if self.mode == 1:
            rows.append(("LÖSCHUNG", dl, (90, 255, 200)))
        h = 30 + 20 * len(rows) + (20 if nxt is not None else 0)
        self.hud_panel(x, y, w, h, ec, cut=8, alpha=170)
        self.text(sc, "VIREN" if self.mode == 1 else "DROHNEN", self.f_tiny, ec, (x + 12, y + 14), "midleft",
                  glow=False)
        for i, (lab, n, col) in enumerate(rows):
            yy = y + 38 + i * 20
            pygame.draw.rect(sc, col, (x + 12, yy - 5, 9, 9))
            self.text(sc, lab, self.f_tiny, (190, 195, 235), (x + 28, yy), "midleft", glow=False)
            self.text(sc, str(n), self.f_small, col, (x + w - 12, yy), "midright", glow=False)
        if nxt is not None:
            self.text(sc, f"REPARATUR IN {max(0.0, nxt):.0f}s", self.f_tiny, (255, 190, 90),
                      (x + 12, y + h - 14), "midleft", glow=False)

    def draw_heart(self, x, y, s, full, sc=None):
        sc = self.screen if sc is None else sc
        col = (255, 60, 120) if full else (90, 30, 55)
        w = 0 if full else 2
        pygame.draw.circle(sc, col, (int(x - s * 0.5), int(y)), int(s * 0.55), w)
        pygame.draw.circle(sc, col, (int(x + s * 0.5), int(y)), int(s * 0.55), w)
        pygame.draw.polygon(sc, col, [(x - s * 1.02, y + s * 0.25),
                                      (x + s * 1.02, y + s * 0.25), (x, y + s * 1.4)], w)

    def draw_hud(self):
        sc, p, lv = self.screen, self.player, self.level
        self.text(sc, f"LEVEL {self.level_no + 1}", self.f_mid, (255, 230, 120), (24, 18), "topleft")
        self.text(sc, f"PUNKTE {self.score:06d}", self.f_small, (150, 255, 230), (24, 52), "topleft")
        for i in range(MAX_LIVES):                       # maximal 4 Herzen
            self.draw_heart(36 + i * 40, 98, 11, i < p.lives)
        dd = self.diff()
        self.text(sc, f"{MODES[self.mode][0]}-MODUS  -  {dd['name']}", self.f_small, dd["col"],
                  (24, 126), "topleft", glow=False)
        yy = 150
        if self.mode == 1 and self.level_no >= 1:
            self.text(sc, f"NEUER VIRUS IN {max(0.0, self.spread_t):.0f}s", self.f_small, (255, 110, 120),
                      (24, yy), "topleft", glow=False)
            yy += 24
        if self.cheated:
            self.text(sc, f"ADMIN  DROHNEN {len(self.enemies)}  (nicht gewertet)", self.f_small,
                      (255, 90, 90), (24, yy), "topleft", glow=False)
        # Zeit + Kristalle
        self.text(sc, f"ZEIT {self.level_time:6.1f}", self.f_small, (200, 200, 255), (W // 2, 16), "midtop")
        pts = [(W // 2 - 62, 52), (W // 2 - 54, 44), (W // 2 - 46, 52), (W // 2 - 54, 60)]
        pygame.draw.polygon(sc, (255, 90, 220), pts)
        self.text(sc, f"{self.collected}/{len(self.crystals)}", self.f_small,
                  (255, 150, 235), (W // 2 - 36, 52), "midleft")
        if self.combo > 1:
            self.text(sc, f"COMBO x{self.combo}", self.f_small, (255, 220, 90),
                      (W // 2, 74), "midtop")
        # Dash- und Schuss-Anzeige
        bars = (("DASH", clamp(1 - p.dash_cd / DASH_CD, 0, 1), (90, 255, 255)),
                ("SCHUSS", clamp(1 - p.shoot_cd / SHOT_CD, 0, 1), (255, 120, 230)))
        for i, (label, frac, col) in enumerate(bars):
            y = H - 42 - i * 30
            self.text(sc, label, self.f_small, col, (24, y - 4), "topleft", glow=False)
            pygame.draw.rect(sc, (30, 40, 60), (110, y, 150, 12))
            pygame.draw.rect(sc, col if frac >= 1 else tuple(int(c * 0.55) for c in col),
                             (110, y, int(150 * frac), 12))
            pygame.draw.rect(sc, col, (110, y, 150, 12), 1)
            if label == "SCHUSS" and p.shoot_cd > 0:
                self.text(sc, f"{p.shoot_cd:.0f}s", self.f_small, col, (272, y - 4), "topleft", glow=False)
        self.draw_minimap()
        self.draw_effects()
        self.draw_crosshair()
        if self.banner > 0:
            a = clamp(self.banner / 0.8, 0, 1)
            self.text(sc, f"LEVEL {self.level_no + 1}", self.f_big,
                      tuple(int(c * a) for c in (255, 240, 150)), (W // 2, H // 2 - 120))

    def draw_crosshair(self):
        if self.state != "play" or self.touch_mode():
            return
        sc, p, t = self.screen, self.player, self.t
        mx, my = pygame.mouse.get_pos()
        ready = p.shoot_cd <= 0
        col = (120, 255, 255) if ready else (110, 110, 140)
        if ready:                                        # Zielhilfe
            psx, psy = p.x - self.camx, p.y - self.camy
            d = math.hypot(mx - psx, my - psy)
            if d > 30:
                ux, uy = (mx - psx) / d, (my - psy) / d
                for k in range(1, int(min(d, 300) // 24) + 1):
                    pygame.draw.circle(sc, (70, 170, 210), (int(psx + ux * 24 * k), int(psy + uy * 24 * k)), 2)
        r = 15 + (2 if ready else 0)
        for k in range(4):                               # rotierende Klammern
            a = t * (2.0 if ready else 0.5) + k * math.pi / 2
            pygame.draw.arc(sc, col, (mx - r, my - r, 2 * r, 2 * r), a, a + 0.9, 2)
        pygame.draw.line(sc, col, (mx - 23, my), (mx - 10, my), 1)
        pygame.draw.line(sc, col, (mx + 10, my), (mx + 23, my), 1)
        pygame.draw.line(sc, col, (mx, my - 23), (mx, my - 10), 1)
        pygame.draw.line(sc, col, (mx, my + 10), (mx, my + 23), 1)
        pygame.draw.circle(sc, col, (mx, my), 2)
        if not ready:
            frac = 1 - clamp(p.shoot_cd / SHOT_CD, 0.0, 1.0)
            pygame.draw.arc(sc, (255, 120, 230), (mx - 27, my - 27, 54, 54), math.pi / 2,
                            math.pi / 2 + 2 * math.pi * frac, 2)

    def draw_minimap(self):
        if self.bigmap:
            self.draw_bigmap()
            return
        sc, lv, p = self.screen, self.level, self.player
        s = max(2, min(5, 260 // lv.tw, 200 // lv.th))
        pw, ph = lv.tw * s + 16, lv.th * s + 32
        px, py = W - pw - 14, 14
        self.hud_panel(px, py, pw, ph, (110, 120, 255), cut=10, alpha=190)
        self.text(sc, "RADAR", self.f_tiny, (140, 150, 255), (px + 12, py + 12), "midleft", glow=False)
        self.text(sc, "%d/%d" % self.goal(), self.f_tiny,
                  (90, 255, 170) if self.portal_open else (255, 150, 235), (px + pw - 12, py + 12), "midright",
                  glow=False)
        mx0, my0 = px + 8, py + 24
        sc.set_clip((mx0, my0, lv.tw * s, lv.th * s))
        for (x, y) in self.explored:
            col = (70, 80, 190) if lv.grid[y][x] else (22, 28, 60)
            sc.fill(col, (mx0 + x * s, my0 + y * s, s, s))
        if lv.exit in self.explored:
            ex, ey = lv.exit
            pygame.draw.circle(sc, (60, 255, 150) if self.portal_open else (255, 80, 100),
                               (mx0 + ex * s + s // 2, my0 + ey * s + s // 2), s + 1)
        pxm, pym = int(mx0 + p.x / TS * s), int(my0 + p.y / TS * s)
        pygame.draw.circle(sc, (255, 220, 100), (pxm, pym), int(s * 2 + (self.t * 12) % (s * 5)), 1)
        pygame.draw.circle(sc, (255, 220, 100), (pxm, pym), s)
        for e in self.enemies:                           # Radar: Drohnen in Reichweite
            if math.hypot(e.x - p.x, e.y - p.y) < 10 * TS:
                col = (255, 170, 60) if e.offline else ((120, 130, 160) if e.stun > 0 else self.ecol())
                pygame.draw.circle(sc, col, (int(mx0 + e.x / TS * s), int(my0 + e.y / TS * s)), max(2, s - 1))
        sc.set_clip(None)
        w2 = max(pw, 176)
        self.draw_drone_counter(W - w2 - 14, py + ph + 8, w2)

    # ---------- Große Karte
    def draw_bigmap(self):
        sc, lv, p = self.screen, self.level, self.player
        s = max(2, min((W - 120) // lv.tw, (H - 160) // lv.th))
        pw, ph = lv.tw * s, lv.th * s
        px, py = (W - pw) // 2, (H - ph) // 2 + 20
        self.hud_panel(px - 14, py - 14, pw + 28, ph + 28, (110, 120, 255), cut=14, alpha=225)
        for (x, y) in self.explored:
            col = (70, 80, 190) if lv.grid[y][x] else (30, 38, 85)
            sc.fill(col, (px + x * s, py + y * s, s, s))
        ex, ey = lv.exit
        if lv.exit in self.explored:
            pygame.draw.circle(sc, (60, 255, 150) if self.portal_open else (255, 80, 100),
                               (px + ex * s + s // 2, py + ey * s + s // 2), s + 2)
        for e in self.enemies:
            if self.cheat["light"] or math.hypot(e.x - p.x, e.y - p.y) < 12 * TS:
                col = (255, 170, 60) if e.offline else ((120, 130, 160) if e.stun > 0 else self.ecol())
                pygame.draw.circle(sc, col, (int(px + e.x / TS * s), int(py + e.y / TS * s)), max(2, s // 2))
        for tr in self.traps:
            pygame.draw.circle(sc, (255, 170, 60), (int(px + tr.x / TS * s), int(py + tr.y / TS * s)), max(2, s // 2), 1)
        if int(self.t * 3) % 2 == 0:
            pygame.draw.circle(sc, (255, 220, 100), (int(px + p.x / TS * s), int(py + p.y / TS * s)),
                               max(3, s // 2 + 1))
        state = "PORTAL OFFEN" if self.portal_open else (("Viren gelöscht %d/%d" if self.mode == 1 else "Kristalle %d/%d") % self.goal())
        self.text(sc, f"KARTE  -  {state}  -  TAB / M schließen", self.f_small, (170, 170, 230),
                  (W // 2, py - 22), "midbottom")

    # ---------- Admin-Konsole
    def set_console(self, on):
        self.console_open = on
        self.con_buf = ""
        if on:
            pygame.key.set_repeat(350, 35)
        else:
            pygame.key.set_repeat()

    def log(self, s, col=(200, 200, 255)):
        self.con_lines.append((s, col))
        del self.con_lines[:-17]

    def _flag(self, key, args, label):
        a = args[0].lower() if args else ""
        if a in ("on", "an", "ein", "1"):
            v = True
        elif a in ("off", "aus", "0"):
            v = False
        else:
            v = not self.cheat[key]
        self.cheat[key] = v
        self.log(f"{label}: {'AN' if v else 'AUS'}", (120, 255, 200) if v else (255, 170, 120))
        return v

    @staticmethod
    def _num(args, default, lo, hi):
        try:
            return clamp(float(args[0].replace(",", ".")), lo, hi)
        except Exception:
            return default

    def spawn_drones(self, n):
        lv, p = self.level, self.player
        n = min(n, max(0, MAX_DRONES - len(self.enemies)))
        ptx, pty = p.x / TS, p.y / TS
        far = [c for c in lv.cells if math.hypot(c[0] + 0.5 - ptx, c[1] + 0.5 - pty) >= 7] or lv.cells
        for _ in range(n):
            c = random.choice(far)
            self.enemies.append(self.make_drone(c))
            self.burst((c[0] + 0.5) * TS, (c[1] + 0.5) * TS, (255, 80, 80), 10, 120, 0.5, 3)
        return n

    def unstick(self):
        p, lv = self.player, self.level
        tx, ty = int(p.x // TS), int(p.y // TS)
        if lv.is_wall(tx, ty):
            tx, ty = min(lv.cells, key=lambda c: math.hypot((c[0] + 0.5) * TS - p.x,
                                                            (c[1] + 0.5) * TS - p.y))
        p.x, p.y = (tx + 0.5) * TS, (ty + 0.5) * TS
        p.vx = p.vy = 0.0

    def run_command(self, line):
        parts = line.lstrip("/").split()
        if not parts:
            return
        name = CMD_ALIAS.get(parts[0].lower(), parts[0].lower())
        args = parts[1:]
        self.log("> " + line, (150, 255, 230))
        p, lv = self.player, self.level
        warn = (255, 170, 120)
        if name not in CMD_NAMES:
            self.log("Unbekannter Befehl. 'hilfe' zeigt alle Befehle.", warn)
            return
        if name not in CMD_SAFE:
            self.cheated = True
        if name == "hilfe":
            for l in HELP_LINES:
                self.log(l, (170, 170, 230))
        elif name == "god":
            self._flag("god", args, "Unsterblich")
        elif name == "spawn":
            k = self.spawn_drones(int(self._num(args, 1, 1, 50)))
            self.log(f"{k} Drohne(n) gespawnt - gesamt {len(self.enemies)} (max {MAX_DRONES})")
        elif name == "endlos":
            if self._flag("endless", args, "Endlos-Spawn"):
                self.spawn_t = 0.0
        elif name == "disable":
            t = self._num(args, DISABLE_TIME, 1, 3600)
            for e in self.enemies:
                e.stun, e.stun_max, e.chasing, e.alert_t = t, t, False, 0.0
                self.burst(e.x, e.y, (120, 200, 255), 12, 180, 0.6, 4)
            self.log(f"{len(self.enemies)} Drohnen für {t:.0f} s lahmgelegt")
        elif name == "enable":
            for e in self.enemies:
                e.stun, e.offline, e.off_age, e.boot = 0.0, False, 0.0, 0.0
            self.log(f"{len(self.enemies)} Drohnen geweckt")
        elif name == "kill":
            n = len(self.enemies)
            self.enemies.clear()
            self.log(f"{n} Drohnen gelöscht")
        elif name == "freeze":
            self._flag("freeze", args, "Drohnen dauerhaft lahm")
        elif name == "leben":
            p.lives = int(self._num(args, MAX_LIVES, 1, MAX_LIVES))
            self.log(f"Leben: {p.lives}")
        elif name == "schild":
            p.shield = True
            self.log("Schild aktiv")
        elif name == "magnet":
            p.magnet_t = self._num(args, 60, 1, 3600)
            self.log(f"Magnet {p.magnet_t:.0f} s")
        elif name == "oc":
            p.oc_t = self._num(args, 60, 1, 3600)
            p.dash_cd = p.shoot_cd = 0.0
            self.log(f"Overclock {p.oc_t:.0f} s")
        elif name == "alle":
            p.shield, p.magnet_t, p.oc_t = True, 120.0, 120.0
            p.dash_cd = p.shoot_cd = p.emp_cd = p.trap_cd = p.decoy_cd = 0.0
            p.energy = ENERGY_MAX
            self.log("Schild + Magnet + Overclock (120 s)")
        elif name == "speed":
            self.cheat["speed"] = self._num(args, 1.0, 0.2, 6.0)
            self.log(f"Spielertempo x{self.cheat['speed']:.1f}")
        elif name == "nocd":
            self._flag("nocd", args, "KEIN Cooldown (Dash + Schuss)")
        elif name == "noshot":
            self._flag("noshot", args, "Kein Schuss-Cooldown")
        elif name == "nodash":
            self._flag("nodash", args, "Kein Dash-Cooldown")
        elif name == "noclip":
            if not self._flag("noclip", args, "Noclip"):
                self.unstick()
        elif name == "licht":
            self._flag("light", args, "Vollhelligkeit")
        elif name == "reveal":
            self.explored = {(x, y) for x in range(lv.tw) for y in range(lv.th)}
            self.log("Karte aufgedeckt (TAB = große Karte)")
        elif name == "kristalle":
            n = 0
            for c in self.crystals:
                if c.alive:
                    c.alive = False
                    n += 1
            self.collected += n
            self.score += 100 * n
            self.log(f"{n} Kristalle eingesammelt")
        elif name == "punkte":
            self.score += int(self._num(args, 1000, -10 ** 9, 10 ** 9))
            self.log(f"Punkte: {self.score}")
        elif name == "tp":
            tile = None
            if not args or args[0].lower() in ("exit", "portal"):
                tile = lv.exit
            elif args[0].lower() == "start":
                tile = lv.start
            else:
                try:
                    tile = (int(args[0]), int(args[1]))
                except Exception:
                    tile = None
            if tile is None or lv.is_wall(*tile):
                self.log("tp exit | start | <x> <y>   (Kachel-Koordinaten, keine Wand)", warn)
            else:
                p.x, p.y = (tile[0] + 0.5) * TS, (tile[1] + 0.5) * TS
                p.vx = p.vy = 0.0
                self.camx, self.camy = p.x - W / 2, p.y - H / 2
                self.log(f"Teleportiert nach {tile[0]}, {tile[1]}")
        elif name == "portal":
            if not self.portal_open:
                self.open_portal()
            self.log("Portal geöffnet")
        elif name == "skip":
            self.set_console(False)
            self.complete_level()
        elif name == "level":
            n = int(self._num(args, self.level_no + 2, 1, 999))
            self.level_no, self.lives = n - 1, p.lives
            self.set_console(False)
            self.load_level()
        elif name == "zeit":
            self.cheat["timescale"] = self._num(args, 1.0, 0.1, 1.5)
            self.log(f"Zeit x{self.cheat['timescale']:.1f}")
        elif name == "status":
            on = [k for k in ("god", "endless", "freeze", "nocd", "noshot", "nodash", "noclip", "light")
                  if self.cheat[k]]
            self.log("Aktiv: " + (", ".join(on) or "nichts") +
                     f" | Tempo x{self.cheat['speed']:.1f} | Zeit x{self.cheat['timescale']:.1f}")
            self.log(f"Drohnen: {len(self.enemies)}  Leben: {p.lives}  Level: {self.level_no + 1}"
                     f"  Karte: {lv.cols}x{lv.rows} Zellen")
        elif name == "reset":
            self.reset_cheats()
            self.log("Alle Cheats ausgeschaltet (Lauf bleibt als Admin-Lauf markiert)")
        elif name == "clear":
            self.con_lines.clear()
        elif name == "exit":
            self.set_console(False)

    def console_key(self, k, uni):
        if k in (pygame.K_ESCAPE, pygame.K_F1):
            self.set_console(False)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            line = self.con_buf.strip()
            self.con_buf = ""
            if line:
                self.hist.append(line)
                self.hist_i = len(self.hist)
                self.run_command(line)
        elif k == pygame.K_BACKSPACE:
            self.con_buf = self.con_buf[:-1]
        elif k == pygame.K_UP and self.hist:
            self.hist_i = max(0, self.hist_i - 1)
            self.con_buf = self.hist[self.hist_i]
        elif k == pygame.K_DOWN and self.hist:
            self.hist_i = min(len(self.hist), self.hist_i + 1)
            self.con_buf = self.hist[self.hist_i] if self.hist_i < len(self.hist) else ""
        elif k == pygame.K_TAB:
            pre = self.con_buf.strip().lower()
            m = sorted(c for c in CMD_NAMES + list(CMD_ALIAS) if c.startswith(pre)) if pre else []
            if len(m) == 1:
                self.con_buf = m[0] + " "
            elif m:
                self.log("  ".join(m), (170, 170, 230))
        elif uni and uni.isprintable() and len(self.con_buf) < 60:
            if uni in ("^", "`", "°") and not self.con_buf:
                self.set_console(False)
            else:
                self.con_buf += uni

    def draw_console(self):
        sc = self.screen
        h = 17 * 22 + 64
        s = pygame.Surface((W, h), pygame.SRCALPHA)
        s.fill((0, 6, 14, 228))
        sc.blit(s, (0, 0))
        pygame.draw.line(sc, (0, 255, 200), (0, h), (W, h), 2)
        self.text(sc, "ADMIN-KONSOLE   (ESC / F1 schließen)", self.f_small, (0, 255, 200),
                  (W - 16, 6), "topright", glow=False)
        y = 8
        for txt, col in self.con_lines:
            self.text(sc, txt, self.f_small, col, (16, y), "topleft", glow=False)
            y += 22
        cur = "_" if int(self.t * 2) % 2 == 0 else " "
        self.text(sc, "> " + self.con_buf + cur, self.f_mid, (255, 255, 255), (16, h - 40),
                  "topleft", glow=False)

    # ---------- Einstellungen / Bestenliste
    # ---------- Spielmodus-Auswahl
    def start_rect(self):
        return pygame.Rect(W // 2 - 140, 614, 280, 52)

    def diff_rect(self, i):
        return pygame.Rect(W // 2 - 340 if i == 0 else W // 2 + 270, 536, 70, 50)

    @staticmethod
    def mode_card(i):
        return pygame.Rect(145 + i * 520, 120, 470, 400)

    def modeselect_key(self, k):
        o = self.opt
        if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.state = "menu"
            return
        if k in (pygame.K_LEFT, pygame.K_a):
            o["mode"] = 0
        elif k in (pygame.K_RIGHT, pygame.K_d):
            o["mode"] = 1
        elif k in (pygame.K_UP, pygame.K_w):
            o["difficulty"] = (o["difficulty"] - 1) % len(DIFFICULTIES)
        elif k in (pygame.K_DOWN, pygame.K_s):
            o["difficulty"] = (o["difficulty"] + 1) % len(DIFFICULTIES)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.save_data()
            self.start_game()
            return
        else:
            return
        self.sfx.play("blip")
        self.save_data()

    def modeselect_click(self, pos):
        for i in range(len(MODES)):
            if self.mode_card(i).collidepoint(pos):
                if self.opt["mode"] == i:                 # zweiter Klick auf dieselbe Karte startet
                    self.save_data()
                    self.start_game()
                else:
                    self.opt["mode"] = i
                    self.sfx.play("blip")
                    self.save_data()
                return

    def draw_modeselect(self):
        sc, t, o = self.screen, self.t, self.opt
        d = self.diff()
        self.draw_back_button()
        self.text(sc, "SPIELMODUS WÄHLEN", self.f_big, (255, 240, 150), (W // 2, 62))
        descr = (
            ("Du bist der VIRUS.", "Drohnen sind Schilde und jagen dich.", f"Sammle {CRYSTAL_GOAL} Kristalle fürs Portal.",
             "Knapp vorbeidashen = Bonus.", "Nutze EMP, Fallen und Köder."),
            ("Du bist das SCHILD.", "Pro Level 1 Virus mehr.", f"Bleib {SCAN_TIME:.0f} s bei einem Virus:",
             f"dann läuft seine Löschung ({DELETE_TIME:.0f} s).", "Alle gelöscht = Portal öffnet."),
        )
        for i, (mname, mcol) in enumerate(MODES):
            r = self.mode_card(i)
            sel = o["mode"] == i
            self.hud_panel(r.x, r.y, r.w, r.h, mcol if sel else self.dim(mcol, 0.4), cut=22,
                           alpha=238 if sel else 185)
            if sel:
                g = 4 + int(2 * math.sin(t * 5))
                pygame.draw.polygon(sc, self.dim(mcol, 0.5), self.poly(r.x - g, r.y - g, r.w + 2 * g, r.h + 2 * g, 24), 1)
            cx = r.centerx
            self.text(sc, f"{mname}-MODUS", self.f_big, mcol if sel else self.dim(mcol, 0.6),
                      (cx, r.y + 45), glow=sel)
            py = r.y + 135
            wob = 8 * math.sin(t * 3)
            if i == 0:                                    # Virus flieht vor dem Schild
                self.draw_virus(sc, cx - 80 + wob, py, 26, self.skin_pal(), ext=16, style=o["skin_style"])
                self.draw_shield(sc, cx + 90 - wob, py, 21, PAL_SHIELD_E_CHASE, 0.0)
            else:                                         # Schild wird von Virus gejagt
                self.draw_shield(sc, cx - 80 + wob, py, 29, PAL_SHIELD_P, mark="cross")
                self.draw_virus(sc, cx + 90 - wob, py, 15, PAL_VIRUS_E_CHASE, ext=10)
            for k, line in enumerate(descr[i]):
                self.text(sc, line, self.f_small, mcol if k == 0 else (200, 200, 255),
                          (cx, r.y + 215 + k * 30), glow=False)
            self.text(sc, "<  GEWÄHLT  >" if sel else "wählen", self.f_small,
                      (255, 240, 130) if sel else (130, 130, 175), (cx, r.bottom - 28), glow=False)
        self.text(sc, f"SCHWIERIGKEIT   <  {d['name']}  >", self.f_mid, d["col"], (W // 2, 560))
        self.text(sc, d["info"], self.f_small, (190, 190, 235), (W // 2, 596), glow=False)
        for i in range(2):
            r = self.diff_rect(i)
            self.hud_panel(r.x, r.y, r.w, r.h, d["col"], cut=8, alpha=190)
            dd_ = -1 if i == 0 else 1
            cxx, cyy = r.center
            pygame.draw.polygon(sc, (255, 255, 255), [(cxx + dd_ * 9, cyy - 11), (cxx + dd_ * 9, cyy + 11), (cxx - dd_ * 9, cyy)])
        sr = self.start_rect()
        self.draw_button(sr, "START", sr.collidepoint(pygame.mouse.get_pos()) or int(t * 2) % 2 == 0,
                         (90, 255, 170), shift=False)
        self.text(sc, "LINKS/RECHTS Modus   HOCH/RUNTER Schwierigkeit   ENTER Start   ESC zurück",
                  self.f_tiny, (170, 170, 230), (W // 2, 700), glow=False)

    def open_settings(self, frm):
        self.settings_from, self.sel, self.state = frm, 0, "settings"

    def close_settings(self):
        self.editing_name = False
        self.save_data()
        self.state = self.settings_from

    def name_key(self, k, uni):
        o = self.opt
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
            self.editing_name = False
            o["name"] = o["name"].strip() or "SPIELER"
            self.save_data()
        elif k == pygame.K_BACKSPACE:
            o["name"] = o["name"][:-1]
        elif uni and uni.isprintable() and len(o["name"]) < 12:
            o["name"] += uni

    def change_setting(self, key, d):
        o = self.opt
        if key in ("volume", "music"):
            self.set_volume(key, o[key] + 10 * d)
            return
        if key == "mute":
            self.toggle_mute()
            return
        if key == "mapsize":
            o["mapsize"] = (o["mapsize"] + d) % len(MAP_SIZES)
        elif key == "difficulty":
            o["difficulty"] = (o["difficulty"] + d) % len(DIFFICULTIES)
        elif key == "control":
            o["control"] = 1 - o["control"]
            self.touch_reset()
        elif key in ("bloom", "scanlines", "shake"):
            o[key] = not o[key]
        elif key == "fullscreen":
            self.toggle_fullscreen()
        self.sfx.play("blip")
        self.save_data()

    def settings_rows(self):
        top = H // 2 - 340
        return [pygame.Rect(W // 2 - 360, top + 84 + i * 38, 720, 34) for i in range(len(SETTING_KEYS))]

    def settings_click(self, pos):
        for i, r in enumerate(self.settings_rows()):
            if not r.collidepoint(pos):
                continue
            self.sel = i
            key = SETTING_KEYS[i]
            if key in ("volume", "music"):
                bx = r.right - 14 - 260 - 70
                if bx - 8 <= pos[0] <= bx + 268:
                    self.set_volume(key, int(round(clamp((pos[0] - bx) / 260.0, 0.0, 1.0) * 10)) * 10)
                    return
            if key == "name":
                self.editing_name = True
                try:
                    pygame.key.start_text_input()
                except Exception:
                    pass
            elif key == "back":
                self.close_settings()
            else:
                self.change_setting(key, 1)
            return

    def draw_pause(self):
        sc = self.screen
        self.panel(560, 440, (110, 110, 255))
        self.text(sc, "PAUSE", self.f_big, (150, 200, 255), (W // 2, H // 2 - 165))
        mp = pygame.mouse.get_pos()
        for i, (lab, col) in enumerate((("WEITER", (90, 255, 170)), ("EINSTELLUNGEN", (110, 230, 255)),
                                        ("HAUPTMENÜ", (255, 120, 140)))):
            r = self.pause_btn(i)
            self.draw_button(r, lab, r.collidepoint(mp), col, shift=False)
        have, need = self.goal()
        self.text(sc, f"{MODES[self.mode][0]}-MODUS  -  {self.diff()['name']}", self.f_small, self.diff()["col"],
                  (W // 2, H // 2 + 112), glow=False)
        self.text(sc, ("Viren gelöscht " if self.mode == 1 else "Kristalle ") + f"{have}/{need}",
                  self.f_small, (200, 200, 255), (W // 2, H // 2 + 142), glow=False)
        self.text(sc, "P / ESC weiter   S Einstellungen   Q Hauptmenü   N Ton   F1 Konsole", self.f_tiny,
                  (150, 155, 210), (W // 2, H // 2 + 178), glow=False)

    def settings_key(self, k):
        n = len(SETTING_KEYS)
        if k == pygame.K_ESCAPE:
            self.close_settings()
            return
        if k == pygame.K_UP:
            self.sel = (self.sel - 1) % n
        elif k == pygame.K_DOWN:
            self.sel = (self.sel + 1) % n
        key = SETTING_KEYS[self.sel]
        if k == pygame.K_LEFT and key not in ("name", "back"):
            self.change_setting(key, -1)
        elif k == pygame.K_RIGHT and key not in ("name", "back"):
            self.change_setting(key, 1)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if key == "name":
                self.editing_name = True
            elif key == "back":
                self.close_settings()
            else:
                self.change_setting(key, 1)

    def draw_settings(self):
        sc, o = self.screen, self.opt
        self.panel(800, 680, (110, 130, 255))
        top = H // 2 - 340
        self.text(sc, "EINSTELLUNGEN", self.f_big, (150, 200, 255), (W // 2, top + 42))
        onoff = lambda v: "AN" if v else "AUS"
        dd = self.diff()
        vals = {"name": o["name"] + ("_" if self.editing_name and int(self.t * 3) % 2 == 0 else ""),
                "control": "HANDY (Touch)" if o["control"] == 1 else "PC (Tastatur+Maus)",
                "mapsize": MAP_SIZES[o["mapsize"]][0], "difficulty": dd["name"],
                "bloom": onoff(o["bloom"]), "scanlines": onoff(o["scanlines"]),
                "shake": onoff(o["shake"]), "fullscreen": onoff(self.fullscreen),
                "mute": "STUMM" if o["mute"] else "Ton an", "back": ""}
        for i, (key, r) in enumerate(zip(SETTING_KEYS, self.settings_rows())):
            sel = i == self.sel
            if sel:
                pygame.draw.rect(sc, (18, 24, 66), r)
                pygame.draw.rect(sc, (110, 130, 255), r, 1)
                pygame.draw.rect(sc, (255, 240, 130), (r.x, r.y, 4, r.h))
            col = (255, 240, 130) if sel else (190, 190, 235)
            self.text(sc, SETTING_LABELS[key], self.f_mid, col, (r.x + 16, r.centery), "midleft", glow=sel)
            if key in ("volume", "music"):
                v = o[key]
                bw = 260
                bx = r.right - 14 - bw - 70
                self.hud_bar(bx, r.centery - 7, bw, 14, v / 100.0,
                             (110, 230, 255) if key == "volume" else (255, 120, 230), segs=10)
                self.text(sc, f"{v} %", self.f_mid, col if not o["mute"] else (120, 120, 150),
                          (r.right - 14, r.centery), "midright", glow=False)
                continue
            v = vals[key]
            vcol = dd["col"] if key == "difficulty" else ((255, 90, 100) if (key == "mute" and o["mute"]) else col)
            if key == "name":
                v = v if not sel or self.editing_name else v + "   [ENTER]"
            elif sel and key != "back":
                v = f"<  {v}  >"
            if v:
                self.text(sc, v, self.f_mid, vcol, (r.right - 14, r.centery), "midright", glow=sel)
        self.text(sc, f"{dd['name']}: {dd['info']}", self.f_small, dd["col"], (W // 2, top + 556), glow=False)
        self.text(sc, "Pfeile oder Maus/Touch: wählen / ändern     ENTER: Name bearbeiten     N: Ton     ESC: zurück",
                  self.f_tiny, (170, 170, 230), (W // 2, top + 600), glow=False)
        self.text(sc, "Kartengröße & Schwierigkeit gelten ab dem nächsten Level.  Steuerung: PC oder HANDY",
                  self.f_tiny, (170, 170, 230), (W // 2, top + 624), glow=False)

    def draw_leaderboard(self):
        sc, cx = self.screen, W // 2
        self.panel(1000, 560, (255, 220, 100))
        top = H // 2 - 280
        self.text(sc, "BESTENLISTE", self.f_big, (255, 220, 100), (cx, top + 45))
        hc = (150, 255, 230)
        for label, x, anc in (("#", -470, "midleft"), ("NAME", -420, "midleft"),
                              ("PUNKTE", -110, "midright"), ("LV", -90, "midleft"),
                              ("MODUS", -40, "midleft"), ("KARTE", 60, "midleft"),
                              ("STUFE", 150, "midleft"), ("DATUM", 470, "midright")):
            self.text(sc, label, self.f_small, hc, (cx + x, top + 100), anc, glow=False)
        pygame.draw.line(sc, (110, 110, 255), (cx - 470, top + 116), (cx + 470, top + 116), 1)
        if not self.board:
            self.text(sc, "Noch keine Einträge - spiel eine Runde!", self.f_mid, (190, 190, 235),
                      (cx, top + 260), glow=False)
        for i, e in enumerate(self.board[:10]):
            y = top + 140 + i * 36
            col = (255, 240, 130) if i == 0 else (210, 210, 245)
            if self.last_rank == i + 1:
                col = (120, 255, 200)
            self.text(sc, str(i + 1), self.f_small, col, (cx - 470, y), "midleft", glow=False)
            self.text(sc, str(e.get("name", "?"))[:12], self.f_small, col, (cx - 420, y), "midleft", glow=False)
            self.text(sc, f"{e['score']:,}".replace(",", "."), self.f_small, col, (cx - 110, y), "midright", glow=False)
            self.text(sc, str(e.get("level", "?")), self.f_small, col, (cx - 90, y), "midleft", glow=False)
            self.text(sc, str(e.get("mode", "VIRUS")), self.f_small, col, (cx - 40, y), "midleft", glow=False)
            self.text(sc, str(e.get("map", "?")), self.f_small, col, (cx + 60, y), "midleft", glow=False)
            self.text(sc, str(e.get("diff", "?")), self.f_small, col, (cx + 150, y), "midleft", glow=False)
            self.text(sc, str(e.get("date", "")), self.f_small, col, (cx + 470, y), "midright", glow=False)
        self.text(sc, "ESC / ENTER zurück   -   lokale Liste, Admin-Läufe zählen nicht",
                  self.f_small, (170, 170, 230), (cx, top + 530), glow=False)

    def panel(self, w, h, border):
        self.hud_panel(W // 2 - w // 2, H // 2 - h // 2, w, h, border, cut=18, alpha=228)

    def build_menu_art(self):
        """Einmalig vorgerendert: Himmel, Sonne mit Streifen, Skyline."""
        hz = 430
        sky = pygame.Surface((W, hz))
        for y in range(hz):
            k = y / float(hz)
            pygame.draw.line(sky, (int(6 + 80 * k ** 2.2), int(2 + 10 * k), int(28 + 96 * k ** 1.6)), (0, y), (W, y))
        R = 150
        sun = pygame.Surface((2 * R, 2 * R), pygame.SRCALPHA)
        for y in range(2 * R):
            k = y / (2.0 * R)
            if k > 0.52 and (y % 14) < 2 + 9 * (k - 0.5) * 2:
                continue
            half = math.sqrt(max(0.0, R * R - (y - R) ** 2))
            pygame.draw.line(sun, (255, int(235 - 195 * k), int(100 + 60 * k), 255), (R - half, y), (R + half, y))
        rnd = random.Random(7)
        blocks, x = [], -10
        while x < W:
            bw, bh = rnd.randint(34, 90), rnd.randint(40, 190)
            wins = [(rnd.randint(6, bw - 10), rnd.randint(10, bh - 8), rnd.random() * 6.28)
                    for _ in range(max(2, bw * bh // 900))]
            blocks.append((x, bw, bh, wins, rnd.random()))
            x += bw + rnd.randint(-4, 12)
        self.menu_art = (sky, sun, blocks)
        self.sun_glow = self.make_light(260, (110, 30, 100))

    def draw_menu_bg(self):
        sc, t = self.scene, self.t
        sky, sun, blocks = self.menu_art
        hz = 430
        sc.blit(sky, (0, 0))
        self.draw_stars(sc, t * 6, 0)
        sx, sy = 930, 285 + int(math.sin(t * 0.8) * 6)
        sc.blit(self.sun_glow, (sx - 260, sy - 260), special_flags=pygame.BLEND_RGB_ADD)
        sc.blit(sun, (sx - 150, sy - 150))
        for bx, bw, bh, wins, hue in blocks:                      # Skyline aus Neon-Tuermen
            top = hz - bh
            sc.fill((8, 5, 24), (bx, top, bw, bh))
            pygame.draw.line(sc, hsv(0.5 + hue * 0.4, 0.8, 0.8), (bx, top), (bx + bw, top), 2)
            pygame.draw.line(sc, hsv(0.5 + hue * 0.4, 0.8, 0.35), (bx, top), (bx, hz), 1)
            for wx, wy, ph in wins:
                if math.sin(t * 1.3 + ph) > -0.35:
                    sc.fill(hsv(0.12 + hue * 0.1, 0.5, 0.75), (bx + wx, top + wy, 3, 4))
        sc.fill((7, 3, 24), (0, hz, W, H - hz))
        for i in range(-14, 15):                                  # Perspektiv-Gitter
            pygame.draw.line(sc, hsv(0.83 - abs(i) * 0.004, 0.9, 0.5), (W // 2 + i * 14, hz), (W // 2 + i * 190, H), 1)
        for k in range(12):
            z = (k + (t * 0.45) % 1.0) / 12.0
            y = int(hz + (H - hz) * z ** 2.0)
            pygame.draw.line(sc, hsv(0.5 + z * 0.35, 0.85, 0.25 + 0.75 * z), (0, y), (W, y), 1 + int(z * 2))
        pygame.draw.line(sc, (255, 80, 200), (0, hz), (W, hz), 3)
        if self.opt["bloom"]:
            self.bloom(sc)
        self.screen.blit(sc, (0, 0))
        self.draw_embers()

    def draw_embers(self):
        sc = self.screen
        for x, y, sp, r, ph in self.embers:
            yy = (y - self.t * sp * 3) % H
            xx = x + math.sin(self.t * 0.7 + ph * 6) * 14
            a = max(0.0, 0.35 + 0.5 * math.sin(self.t * 2 + ph * 9))
            pygame.draw.circle(sc, hsv(0.55 + ph * 0.25 + self.t * 0.02, 0.6, 0.30 + 0.70 * a),
                               (int(xx), int(yy)), int(r))

    def draw_menu(self):
        self.draw_menu_bg()
        sc, t = self.screen, self.t
        # ---- Titel: Farbverlauf, Wellenbewegung, Farbversatz und gelegentliche Glitches
        title = "NEON MAZE"
        widths = [self.f_title.size(ch)[0] for ch in title]
        x = 60
        for i, (ch, w) in enumerate(zip(title, widths)):
            y = 52 + math.sin(t * 2 + i * 0.6) * 7
            jit = random.choice((-9, 9)) if random.random() < 0.012 else 0
            col = hsv(round((t * 0.12 + i * 0.045) * 48) / 48.0, 0.8, 1.0)
            if ch != " ":
                self.text(sc, ch, self.f_title, (0, 255, 255), (x - 4 + jit, y), "topleft", glow=False)
                self.text(sc, ch, self.f_title, (255, 0, 200), (x + 4 + jit, y), "topleft", glow=False)
                self.text(sc, ch, self.f_title, col, (x + jit, y), "topleft")
            x += w
        pygame.draw.line(sc, hsv(t * 0.12, 0.7, 1.0), (66, 196), (66 + 380, 196), 3)
        self.text(sc, "P  R  O", self.f_mid, (255, 255, 255), (66, 228), "midleft")
        self.text(sc, "SAMMELN  -  LAHMLEGEN  -  ENTKOMMEN", self.f_tiny, (150, 160, 230), (230, 228), "midleft",
                  glow=False)
        # ---- Buttons
        subs = (f"{MODES[self.opt['mode']][0]} | {self.diff()['name']}", SKIN_COLORS[self.opt["skin_color"]][0],
                "HANDY" if self.touch_mode() else "PC", "Ton, Grafik, Handy", f"{len(self.board)} Einträge", "")
        cols = ((90, 255, 170), (255, 120, 230), (255, 205, 90), (110, 230, 255), (255, 220, 100), (255, 100, 120))
        for i, (lab, act) in enumerate(MENU_ITEMS):
            self.draw_button(self.menu_btn(i), lab, self.msel == i, cols[i], subs[i])
        # ---- Maskottchen: dein Skin, umkreist von Schild-Drohnen
        mx, my = 930, 285 + math.sin(t * 1.4) * 10
        self.draw_virus(sc, mx, my, 54, self.skin_pal(), ext=22, style=self.opt["skin_style"])
        for k in range(3):
            a = t * 0.9 + k * 2.094
            ex, ey = mx + math.cos(a) * 190, my + math.sin(a) * 70 + 10
            self.draw_shield(sc, ex, ey, 17 + 4 * math.sin(a), PAL_SHIELD_E_CHASE if k % 2 else PAL_SHIELD_H, k)
        self.text(sc, "DEIN VIRUS", self.f_tiny, (170, 175, 230), (mx, my + 118), glow=False)
        # ---- Rekord + Tipp
        self.hud_panel(W - 330, H - 92, 300, 60, (255, 220, 100), cut=12, alpha=200)
        self.text(sc, "REKORD", self.f_tiny, (255, 220, 100), (W - 314, H - 78), "topleft", glow=False)
        self.text(sc, f"{self.best:06d}", self.f_mid, (255, 235, 150), (W - 46, H - 52), "midright")
        tips = ("Q: EMP-Puls legt alle Drohnen im Umkreis lahm",
                "R: Falle legen - sie löst aus, sobald eine Drohne drüberläuft",
                "C: Köder-Hologramm lockt Drohnen von dir weg",
                f"Sammle {CRYSTAL_GOAL} Kristalle, dann öffnet sich das Portal",
                "Schild-Modus: bleib 8 s bei einem Virus, dann wird er gelöscht",
                "Defekte Drohnen reparieren sich nach 60 s selbst")
        self.text(sc, "TIPP: " + tips[int(t / 4) % len(tips)], self.f_small, (150, 160, 225), (90, H - 36),
                  "midleft", glow=False)

    def draw(self):
        pygame.mouse.set_visible(self.state != "play" or self.console_open)
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "leaderboard":
            self.draw_menu()
            self.draw_leaderboard()
        elif self.state == "modeselect":
            self.draw_menu_bg()
            self.draw_modeselect()
        elif self.state == "skins":
            self.draw_menu_bg()
            self.draw_skins()
        elif self.state == "keys":
            self.draw_menu_bg()
            self.draw_keys()
        elif self.state == "settings" and self.settings_from == "menu":
            self.draw_menu()
            self.draw_settings()
        else:
            self.draw_game()
            st = self.state
            if st == "settings":
                self.draw_settings()
            elif st == "pause":
                self.draw_pause()
            elif st == "levelclear":
                s = self.summary
                self.panel(620, 400, (60, 255, 170))
                cy = H // 2 - 150
                self.text(self.screen, "LEVEL GESCHAFFT!", self.f_big, (90, 255, 170), (W // 2, cy + 10))
                rows = [(f"Zeit              {s['time']:.1f} s", (200, 200, 255)),
                        (f"Kristalle         {s['col']} / {s['total']}", (255, 150, 235)),
                        (f"Zeitbonus         +{s['tb']}", (255, 230, 120)),
                        (f"Kristallbonus     +{s['cb']}", (255, 230, 120)),
                        (f"PUNKTE            {self.score}", (120, 255, 230))]
                for i, (txt, col) in enumerate(rows):
                    self.text(self.screen, txt, self.f_mid, col, (W // 2, cy + 100 + i * 40), glow=False)
                if int(self.t * 2) % 2 == 0:
                    self.text(self.screen, "ENTER - nächstes Level", self.f_small, (255, 255, 255),
                              (W // 2, cy + 335))
            elif st == "gameover":
                cy, sc2 = H // 2, self.screen
                self.panel(620, 400, (255, 60, 90))
                self.text(sc2, "GAME OVER", self.f_big, (255, 70, 100), (W // 2, cy - 150))
                self.text(sc2, f"Punkte  {self.score}   (Level {self.level_no + 1})", self.f_mid,
                          (255, 230, 120), (W // 2, cy - 80))
                self.text(sc2, f"Rekord  {self.best}", self.f_mid, (150, 255, 230), (W // 2, cy - 38))
                secs = int(self.stats["time"])
                self.text(sc2, f"Drohnen lahmgelegt {self.stats['disabled']}    Kristalle {self.stats['crystals']}",
                          self.f_small, (200, 200, 255), (W // 2, cy + 10), glow=False)
                self.text(sc2, f"Spielzeit {secs // 60}:{secs % 60:02d}    {MODES[self.mode][0]} / {self.diff()['name']}",
                          self.f_small, self.diff()["col"], (W // 2, cy + 38), glow=False)
                note = ("ADMIN-LAUF - nicht in der Bestenliste" if self.cheated else
                        (f"Bestenliste: Platz {self.last_rank}" if self.last_rank else ""))
                if note:
                    self.text(sc2, note, self.f_small, (255, 220, 100), (W // 2, cy + 82))
                if int(self.t * 2) % 2 == 0:
                    self.text(sc2, "ENTER - Hauptmenü", self.f_small, (255, 255, 255), (W // 2, cy + 140))
        self.screen.blit(self.vignette, (0, 0))
        if self.opt["scanlines"]:
            self.screen.blit(self.scanlines, (0, 0))
        if self.toast_t > 0:
            a = clamp(self.toast_t / 0.4, 0.0, 1.0)
            self.text(self.screen, self.toast_s, self.f_mid, tuple(int(c * a) for c in (255, 240, 150)),
                      (W // 2, H - 150))
        if self.console_open:
            self.draw_console()

    # ---------- Hauptschleife
    def run(self):
        FD, FU, FM = (getattr(pygame, n, -1) for n in ("FINGERDOWN", "FINGERUP", "FINGERMOTION"))
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.music_scene(dt)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.end_run()
                    pygame.quit()
                    return
                if e.type == pygame.KEYDOWN and self.on_key(e.key, e.unicode):
                    self.end_run()
                    pygame.quit()
                    return
                if e.type == FD:
                    self.finger_seen = True
                    self.pointer_down(("f", e.finger_id), (e.x * W, e.y * H))
                elif e.type == FM:
                    self.pointer_move(("f", e.finger_id), (e.x * W, e.y * H))
                elif e.type == FU:
                    self.pointer_up(("f", e.finger_id))
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    if getattr(e, "touch", False) and self.finger_seen:
                        continue                          # vom Touch erzeugte Maus-Events ignorieren
                    if e.button == 1:
                        self.pointer_down(("m", 1), e.pos)
                    elif e.button == 3:
                        self.right_click(e.pos)
                elif e.type == pygame.MOUSEBUTTONUP:
                    if not (getattr(e, "touch", False) and self.finger_seen) and e.button == 1:
                        self.pointer_up(("m", 1))
                elif e.type == pygame.MOUSEMOTION:
                    if not (getattr(e, "touch", False) and self.finger_seen):
                        self.pointer_move(("m", 1), e.pos)
                        self.hover(e.pos)
            if self.quit_req:
                self.end_run()
                pygame.quit()
                return
            if self.state == "play" and not self.console_open:
                dt *= self.cheat["timescale"]
            steps = int(dt / 0.05) + 1
            for _ in range(steps):
                self.update(dt / steps)
            self.draw()
            pygame.display.flip()

if __name__ == "__main__":
    try:
        Game().run()
    except Exception:
        import traceback
        err = traceback.format_exc()
        print("\n===== FEHLER =====")
        print(err)
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "neon_maze_fehler.log"), "w", encoding="utf-8") as f:
                f.write(f"Python {sys.version}\npygame {getattr(pygame, 'version', None) and pygame.version.ver}\n\n{err}")
        except Exception:
            pass
        pause()