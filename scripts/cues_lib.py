"""Word-anchored cue library. A project's cues.py (copied from templates/cues.example.py) only DECLARES
chapters, zooms and graphics by the spoken word that carries them; this library does the rest.

    from cues_lib import Cues
    C = Cues(edit_dir)
    C.cards(title_src=200.52, chapters=[(1, "The roadmap", "What Growth is working on", 200.52), ...])
    C.zoom("roadmap", C.pre(218.9, "One") - 0.2, C.pre(384.0, "cases.", "end") + 0.4, z=1.5, fx=0.3, fy=0.5)
    C.add(dict(type="list", pos="card", t0=C.at(512.9, "don't") - 0.3, ...))
    C.write()

Rules it enforces: every anchor resolves (all misses reported at once, then exit); a cold open that reuses
source audio is disambiguated with after=; nothing runs across an inserted card; one thing per slot.
"""
import json, re, sys
from pathlib import Path

TITLE_D, CH_D, END_D, COVER = 2.4, 1.6, 5.0, 0.34
KEY_DEFAULT = {"5", "10x", "95", "percent", "goal", "phase"}


def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())


class Cues:
    def __init__(self, edit_dir):
        self.ED = Path(edit_dir)
        self.P = json.loads((self.ED / "project.json").read_text())
        tl = json.loads((self.ED / "timeline.json").read_text())
        self.segs, self.words, self.pre_total = tl["segs"], tl["words"], tl["total"]
        self.gaps, self.G, self.Z, self.misses = [], [], [], []
        self.fixes, self.keys, self.short = {}, set(KEY_DEFAULT), {}

    # ---------------- anchors
    def pre(self, src, word, which="start", after=-1.0):
        """Pre-card output time of `word` spoken nearest source second `src` (and after pre-card time `after`)."""
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
        """Title card before `title_src`, a chapter card before each chapter's first word, end card at the end."""
        self.title_text = title or {}
        self.end_text = end or {}
        self.gaps = [dict(at=self.seg_start(title_src), dur=TITLE_D, kind="title")]
        self.gaps += [dict(at=self.seg_start(s), dur=CH_D, kind="chapter", n=n, title=t, kicker=k) for n, t, k, s in chapters]
        self.gaps.append(dict(at=self.pre_total, dur=END_D, kind="end"))
        self.gaps.sort(key=lambda g: (g["at"], g["kind"] != "title"))
        acc, self.final_gaps = 0, []
        for g in self.gaps:
            self.final_gaps.append(dict(g, start=round(g["at"] + acc, 3))); acc += g["dur"]
        self.total = round(self.pre_total + acc, 3)

    def zoom(self, name, t0, t1, z, fx, fy):
        """Pre-card times (use C.pre). fx, fy = the point on the screen card (0-1) that stays put while zooming."""
        self.Z.append(dict(name=name, t0=round(t0, 3), t1=round(t1, 3), z=z, fx=fx, fy=fy))

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
            bub.append(dict(t0=round(self.F(g[0]["start"]) - 0.12, 3), t1=round(self.F(g[-1]["end"]) + 1.4, 3),
                            text=para or text, who=g[0]["spk"], kind="q" if "?" in text else "react"))
        for x, y in zip(bub, bub[1:]): x["t1"] = min(x["t1"], y["t0"] - 0.05)
        return caps, bub, long

    # ---------------- write
    def write(self):
        if self.misses:
            sys.exit("MISS (fix the src time or word, see frames.py words): " + "; ".join(self.misses))
        caps, bub, long = self._captions()
        fg = self.final_gaps

        def clamp(t0, t1):
            for g in fg:
                if t0 < g["start"] < t1: return round(g["start"] + 0.2, 3)
            return t1
        for g in self.G: g["t1"] = clamp(g.get("t0", g.get("t")), g["t1"])
        for c in caps: c["t1"] = clamp(c["t0"], c["t1"])
        for b in bub: b["t1"] = clamp(b["t0"], b["t1"])
        slot = lambda g: "lane" if g["type"] == "lane" else ("row" if g["type"] == "rowhi" else g.get("pos", "card"))
        Gs = sorted(self.G, key=lambda g: g["t0"])
        for i, a in enumerate(Gs):
            nxt = [b["t0"] for b in Gs[i + 1:] if slot(b) == slot(a) and b["t0"] < a["t1"]]
            nxt += [b["t0"] for b in bub if slot(a) == "col" and a["t0"] < b["t0"] < a["t1"]]
            if nxt: a["t1"] = round(min(nxt) - 0.05, 3)
        bad = [g for g in self.G if g["t1"] <= g["t0"]]
        if bad: sys.exit(f"graphics with no time on screen (t1<=t0): {[(g['type'], g['t0']) for g in bad]}")
        chapters = [dict(n=g["n"], title=g["title"], kicker=g["kicker"], start=g["start"], dur=g["dur"]) for g in fg if g["kind"] == "chapter"]
        endg = next(g for g in fg if g["kind"] == "end"); titleg = next(g for g in fg if g["kind"] == "title")
        chips = [dict(n=c["n"], title=c["title"], t0=round(c["start"] + c["dur"], 3),
                      t1=round(chapters[k + 1]["start"] if k + 1 < len(chapters) else endg["start"], 3)) for k, c in enumerate(chapters)]
        modes = []
        for s in self.segs:
            t0 = round(self.F(s["out_start"]), 3); t1 = round(t0 + s["dur"], 3)
            if modes and modes[-1]["mode"] == s["mode"] and abs(modes[-1]["t1"] - t0) < 0.01: modes[-1]["t1"] = t1
            else: modes.append(dict(mode=s["mode"], t0=t0, t1=t1))
        names = {k: v for k, v in self.P["names"].items()}
        D = dict(total=self.total, title=dict(start=titleg["start"], dur=titleg["dur"], **self.title_text),
                 end=dict(start=endg["start"], dur=endg["dur"], **self.end_text), chapters=chapters, chips=chips,
                 captions=caps, bubbles=bub, graphics=self.G, modes=modes, nch=len(chapters), names=names,
                 brand=self.P["brand"], layout=self.P["layout"])
        mg = self.ED / "mg"; mg.mkdir(exist_ok=True)
        (mg / "data.js").write_text("window.DATA = " + json.dumps(D) + ";\n")
        html = mg / "index.html"
        if html.exists():   # the renderer reads the STATIC root data-duration; a JS-set value is ignored
            html.write_text(re.sub(r'(id="root"[^>]*?data-duration=")[\d.]+(")', rf"\g<1>{self.total}\g<2>", html.read_text()))
        (self.ED / "motion_plan.json").write_text(json.dumps(dict(gaps=fg, zooms=self.Z, total=self.total, pre_total=self.pre_total), indent=1))
        print(f"total {self.total:.2f}s ({self.total / 60:.1f} min)  captions {len(caps)}  bubbles {len(bub)}  graphics {len(self.G)}  zooms {len(self.Z)}")
        if long: print("PARAPHRASE these bubble lines (add to C.short):", *long, sep="\n  ")
