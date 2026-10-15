"""Word-anchored cue library. A project's cues.py (from templates/cues.example.py) only DECLARES cards, zooms and
graphics by the spoken word that carries them; this library resolves times and collisions.

    from cues_lib import Cues
    C = Cues(edit_dir)
    C.cards(title_src=95.4, chapters=[(1, "The roadmap", "What ships next", 95.4), ...], title={...}, end={...})
    C.add(dict(type="stage", layout="bullets", t0=C.at(120.1, "three") - 0.2, t1=..., title=..., items=[...]))
    C.write()

Guarantees enforced in write():
  - every anchor resolves (all misses listed, then exit); cold-open duplicates use after=
  - ZONES: stage | col | panel | label | highlight | full. At most one item per zone at a time. A newcomer either
    takes over (the current one has had >= 1.5s: it ends just before) or is queued (starts when the current one
    ends, if it still gets >= 1.5s); otherwise it is reported as a CONFLICT. A stage blocks label + highlight.
  - mode rules: col only during screen share, panel only on camera (talk), stage over either card
  - no empty cards: a card with no static text enters with its first spoken line, never before
  - nothing runs across an inserted chapter card; zooms render only when verified (zoom_check.py)
"""
import json, re, sys
from pathlib import Path

TITLE_D, CH_D, END_D, COVER = 2.4, 1.6, 5.0, 0.34
MIN_ON = 1.5
KEY_DEFAULT = {"10x", "percent", "goal"}
STATIC_KEYS = ("title", "text", "value", "kicker")
CHILD_KEYS = ("rows", "items", "steps", "lines", "dots", "players")


def norm(s): return re.sub(r"[^a-z0-9%]", "", s.lower())


def zone(g):
    if g["type"] == "stage": return "stage"
    if g["type"] == "lane": return "label"
    if g["type"] == "rowhi": return "highlight"
    return g.get("pos", "col")


class Cues:
    def __init__(self, edit_dir):
        self.ED = Path(edit_dir)
        self.P = json.loads((self.ED / "project.json").read_text())
        tl = json.loads((self.ED / "timeline.json").read_text())
        self.segs, self.words, self.pre_total = tl["segs"], tl["words"], tl["total"]
        self.gaps, self.G, self.Z, self.misses, self.problems = [], [], [], [], []
        self.fixes, self.keys, self.short = {}, set(KEY_DEFAULT), {}

    # ---------------- anchors
    def pre(self, src, word, which="start", after=-1.0):
        c = [w for w in self.words if norm(w["text"]) == norm(word) and abs(w["src"] - src) < 2.5 and w["start"] > after]
        if not c:
            self.misses.append(f"{word!r}@{src}"); return 0.0
        return min(c, key=lambda w: abs(w["src"] - src))[which]

    def F(self, t):
        return t + sum(g["dur"] for g in self.gaps if g["at"] <= t + 1e-6 and g["kind"] != "end") + (END_D if t >= self.pre_total else 0)

    def at(self, src, word, which="start", after=-1.0):
        return round(self.F(self.pre(src, word, which, after)), 3)

    def seg_start(self, src):
        return next(s["out_start"] for s in self.segs if s["src_start"] - 0.3 <= src < s["src_end"])

    def mode_at(self, t_pre):
        for s in self.segs:
            if s["out_start"] <= t_pre < s["out_start"] + s["dur"]: return s["mode"]
        return self.segs[-1]["mode"]

    # ---------------- structure
    def cards(self, title_src, chapters, title=None, end=None):
        self.title_text, self.end_text = title or {}, end or {}
        self.gaps = [dict(at=self.seg_start(title_src), dur=TITLE_D, kind="title")]
        self.gaps += [dict(at=self.seg_start(s), dur=CH_D, kind="chapter", n=n, title=t, kicker=k) for n, t, k, s in chapters]
        self.gaps.append(dict(at=self.pre_total, dur=END_D, kind="end"))
        self.gaps.sort(key=lambda g: (g["at"], g["kind"] != "title"))
        acc, self.final_gaps = 0, []
        for g in self.gaps:
            self.final_gaps.append(dict(g, start=round(g["at"] + acc, 3))); acc += g["dur"]
        self.total = round(self.pre_total + acc, 3)

    def zoom(self, name, t0, t1, z, fx, fy, verified=False):
        """Pre-card times (C.pre). Zooms are OFF by default in taste; a zoom renders only after zoom_check.py passes
        and you set verified=True."""
        self.Z.append(dict(name=name, t0=round(t0, 3), t1=round(t1, 3), z=z, fx=fx, fy=fy, verified=verified))

    def add(self, g): self.G.append(g); return g

    # ---------------- captions + bubbles
    def _captions(self):
        bubble_spk = set(self.P.get("bubble_speakers", []))
        cap, side = [], []
        for w in self.words:
            t = w["text"].replace("[laughs]", "").strip()
            if not t or t == "..." or norm(t) in ("um", "uh"): continue
            t = self.fixes.get(t, t)
            md = self.mode_at(w["start"])
            (side if (w["spk"] in bubble_spk and md == "share") else cap).append(dict(w, text=t, mode=md))
        chunks, cur = [], []
        for w in cap:
            if cur:
                gap = w["start"] - cur[-1]["end"]; chars = sum(len(x["text"]) + 1 for x in cur)
                if (gap > 0.45 or chars + len(w["text"]) > 34 or re.search(r"[.?!]$", cur[-1]["text"])
                        or (re.search(r"[,;:]$", cur[-1]["text"]) and len(cur) >= 3) or w["spk"] != cur[-1]["spk"]
                        or w["mode"] != cur[-1]["mode"] or (w["seg"] != cur[-1]["seg"] and gap > 0.2)):
                    chunks.append(cur); cur = []
            cur.append(w)
        if cur: chunks.append(cur)
        caps = []
        for k, c in enumerate(chunks):
            en = c[-1]["end"] + 0.4
            if k + 1 < len(chunks): en = min(en, chunks[k + 1][0]["start"])
            caps.append(dict(t0=round(self.F(c[0]["start"]), 3), t1=round(self.F(en), 3), mode=c[0]["mode"], who=c[0]["spk"],
                             w=[dict(x=x["text"], t=round(self.F(x["start"]), 3), k=norm(x["text"]) in self.keys) for x in c]))
        groups, cur = [], []
        for w in side:
            if cur and w["start"] - cur[-1]["end"] > 1.2: groups.append(cur); cur = []
            cur.append(w)
        if cur: groups.append(cur)
        bub, long = [], []
        for g in groups:
            text = " ".join(x["text"] for x in g)
            if len(re.sub(r"[^a-z]", "", text.lower())) < 8: continue
            para = next((v for k, v in self.short.items() if text.startswith(k)), None)
            if para is None and len(text) > 70: long.append(text[:60])
            bub.append(dict(type="bubble", pos="col", t0=round(self.F(g[0]["start"]) - 0.12, 3), t1=round(self.F(g[-1]["end"]) + 1.4, 3),
                            text=para or text, who=g[0]["spk"], kind="q" if "?" in text else "react"))
        return caps, bub, long

    # ---------------- resolution
    @staticmethod
    def _children_t(g):
        ts = [c["t"] for k in CHILD_KEYS for c in g.get(k, []) if isinstance(c, dict) and "t" in c]
        ts += [g[k]["t"] for k in ("a", "b", "old", "new") if isinstance(g.get(k), dict) and "t" in g[k]]
        if "t" in g: ts.append(g["t"])
        return ts

    def _no_empty(self, g):
        """A card whose only text arrives with spoken words enters with its first line (never an empty box)."""
        static = any(g.get(k) for k in STATIC_KEYS) and not (g["type"] == "stage" and g.get("layout") in ("headline", "stat"))
        ts = self._children_t(g)
        if not static and ts:
            g["t0"] = round(max(g["t0"], min(ts) - 0.25), 3)

    def _zones(self, items):
        by = {}
        for g in items: by.setdefault(zone(g), []).append(g)
        for zn, lst in by.items():
            lst.sort(key=lambda g: g["t0"])
            cur = None
            for g in lst:
                if cur is None or g["t0"] >= cur["t1"]: cur = g; continue
                if g["t0"] - cur["t0"] >= MIN_ON:          # handoff: the current item has had its time
                    cur["t1"] = round(g["t0"] - 0.05, 3); cur = g
                elif g["t1"] - (cur["t1"] + 0.05) >= MIN_ON:  # queue the newcomer
                    g["t0"] = round(cur["t1"] + 0.05, 3); cur = g
                else:
                    g["_drop"] = True
                    self.problems.append(f"CONFLICT in zone '{zn}': {g['type']} at {g['t0']:.1f}s can't fit after "
                                         f"{cur['type']} ({cur['t0']:.1f}-{cur['t1']:.1f}s). Move or shorten one of them.")
        stages = [(g["t0"], g["t1"]) for g in by.get("stage", [])]
        for g in by.get("label", []) + by.get("highlight", []):   # the stage covers the screen: no labels/highlights on top
            for a, b in stages:
                if g["t0"] < b and g["t1"] > a:
                    if g["t0"] < a and a - g["t0"] >= 1.0: g["t1"] = round(a - 0.05, 3)
                    elif g["t1"] > b and g["t1"] - b >= 1.0: g["t0"] = round(b + 0.05, 3)
                    else: g["_drop"] = True; self.problems.append(f"dropped {g['type']} at {g['t0']:.1f}s: covered by a stage scene")
        return [g for g in items if not g.get("_drop")]

    def _modes_ok(self, g):
        md = self.mode_out(g["t0"] + 0.3)
        if zone(g) == "col" and md != "share": self.problems.append(f"{g['type']} at {g['t0']:.1f}s is in the column but the screen isn't shared then (use pos='panel')")
        if zone(g) == "panel" and md != "talk": self.problems.append(f"{g['type']} at {g['t0']:.1f}s is in the panel but it's screen-share mode (use pos='col' or a stage)")

    def mode_out(self, t):
        for m in self.modes:
            if m["t0"] - 0.01 <= t < m["t1"]: return m["mode"]
        return self.modes[-1]["mode"] if self.modes else "share"

    # ---------------- write
    def write(self):
        if self.misses: sys.exit("MISS (fix the src time or word, see frames.py words): " + "; ".join(self.misses))
        caps, bub, long = self._captions(); fg = self.final_gaps
        self.modes = []
        for s in self.segs:
            t0 = round(self.F(s["out_start"]), 3); t1 = round(t0 + s["dur"], 3)
            if self.modes and self.modes[-1]["mode"] == s["mode"] and abs(self.modes[-1]["t1"] - t0) < 0.01: self.modes[-1]["t1"] = t1
            else: self.modes.append(dict(mode=s["mode"], t0=t0, t1=t1))

        def clamp(t0, t1):
            for g in fg:
                if t0 < g["start"] < t1: return round(g["start"] + 0.2, 3)
            return t1
        for g in self.G: self._no_empty(g); g["t1"] = clamp(g["t0"], g["t1"])
        for c in caps: c["t1"] = clamp(c["t0"], c["t1"])
        for b in bub: b["t1"] = clamp(b["t0"], b["t1"])
        items = self._zones(self.G + bub)
        for g in items: self._modes_ok(g)
        short = [g for g in items if g["t1"] - g["t0"] < 1.0]
        for g in short: self.problems.append(f"{g['type']} at {g['t0']:.1f}s is on screen < 1s after resolution")
        graphics = [g for g in items if g["type"] != "bubble"]; bubbles = [g for g in items if g["type"] == "bubble"]
        chapters = [dict(n=g["n"], title=g["title"], kicker=g["kicker"], start=g["start"], dur=g["dur"]) for g in fg if g["kind"] == "chapter"]
        endg = next(g for g in fg if g["kind"] == "end"); titleg = next(g for g in fg if g["kind"] == "title")
        chips = [dict(n=c["n"], title=c["title"], t0=round(c["start"] + c["dur"], 3),
                      t1=round(chapters[k + 1]["start"] if k + 1 < len(chapters) else endg["start"], 3)) for k, c in enumerate(chapters)]
        D = dict(total=self.total, title=dict(start=titleg["start"], dur=titleg["dur"], **self.title_text),
                 end=dict(start=endg["start"], dur=endg["dur"], **self.end_text), chapters=chapters, chips=chips,
                 captions=caps, bubbles=bubbles, graphics=graphics, modes=self.modes, nch=len(chapters), names=self.P["names"],
                 brand=self.P["brand"], layout=self.P["layout"])
        mg = self.ED / "mg"; mg.mkdir(exist_ok=True)
        (mg / "data.js").write_text("window.DATA = " + json.dumps(D) + ";\n")
        html = mg / "index.html"
        if html.exists():   # the renderer reads the STATIC root data-duration; a JS-set value is ignored
            html.write_text(re.sub(r'(id="root"[^>]*?data-duration=")[\d.]+(")', rf"\g<1>{self.total}\g<2>", html.read_text()))
        (self.ED / "motion_plan.json").write_text(json.dumps(dict(gaps=fg, zooms=self.Z, total=self.total, pre_total=self.pre_total), indent=1))
        print(f"total {self.total:.2f}s ({self.total / 60:.1f} min)  captions {len(caps)}  bubbles {len(bubbles)}  graphics {len(graphics)}  zooms {len(self.Z)}")
        unv = [z["name"] for z in self.Z if not z.get("verified")]
        if unv: print("UNVERIFIED zooms (not rendered until zoom_check.py passes and you set verified=True):", ", ".join(unv))
        if long: print("PARAPHRASE these bubble lines (add to C.short):", *long, sep="\n  ")
        if self.problems: print("PROBLEMS (fix in cues.py, then re-run):", *self.problems, sep="\n  ")
