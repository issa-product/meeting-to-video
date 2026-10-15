"""cues.py for ONE project (copy to <edit_dir>/cues.py and rewrite for your video).
Worked example (fictional): "Pebble", a notes app. Alex (PM) walks Sam through the roadmap on a screen share,
then they chat on camera. Every time is a SOURCE second + the word that carries the beat; get them from
`frames.py words <transcript> <from> <to>`. Graphics land ON the word.
Run: python cues.py   (after timeline.py). Re-run any time you change something; then re-render the overlay.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/meeting-to-video/scripts"))
from cues_lib import Cues

C = Cues(Path(__file__).parent)
at, pre = C.at, C.pre

# ---- caption fixes (transcription mishearings, glossary from intake) and words to highlight
C.fixes = {"pebble": "Pebble", "sink": "sync"}
C.keys |= {"offline", "sync", "spaces", "beta", "impact", "urgency"}
# ---- the side speaker's lines during the screen share become bubbles; paraphrase long ones (keyed by how they start)
C.short = {"So I guess my question": "What ships first, and why?",
           "Wait, does that mean": "So offline edits never get lost?"}

# ---- cards: title before chapter 1's first kept word, a card per chapter, end card
C.cards(title_src=95.40, chapters=[
    (1, "The roadmap", "What Pebble ships next", 95.40),
    (2, "What comes first", "Impact x urgency", 260.10),
    (3, "Offline mode", "Notes that never get lost", 352.80),
], title=dict(kicker="Product walkthrough", big="What's next<br/>for Pebble", sub="Alex Rivera, with Sam"),
   end=dict(kicker="That's the tour", big="Questions?", cta="Ping Alex on Slack", sub="Pebble product team"))

# ---- zoom on the screen card while the roadmap is read out (pre-card times; fx, fy = the point that stays put)
C.zoom("roadmap", pre(101.20, "first") - 0.2, pre(205.70, "quarter.", "end") + 0.4, z=1.5, fx=0.30, fy=0.48)

# ---- cold open (camera): the presenter's self-aware line, as kinetic text that lands word by word
C.add(dict(type="kinetic", pos="panel", t0=at(41.10, "Nobody") - 0.1, t1=at(47.90, "promise.", "end") + 0.8, lines=[
    dict(t=at(42.30, "hour"), text="An hour of roadmap?", style="big", strike_t=at(46.20, "short") - 0.3),
    dict(t=at(46.20, "short"), text="The short version", style="pill", icon="scissors")]))

# ---- roadmap: a card per project in the column + a highlight on its row (row y measured with the zoom in)
C.add(dict(type="proj", pos="col", t0=at(101.80, "offline") - 0.2, t1=at(131.40, "spaces") - 0.45, icon="zap",
           title="Offline mode", rows=[dict(t=at(101.80, "offline"), text="Write without a connection"),
                                       dict(t=at(108.60, "sync"), text="Syncs when you're back")]))
C.add(dict(type="rowhi", t0=at(101.80, "offline") - 0.2, t1=at(131.40, "spaces") - 0.45, ys=[372.0], h=46))

# ---- a question from Sam during the share: shows as a bubble automatically (bubble_speakers in project.json)

# ---- priority: a 2x2 that fills as each item is placed, then the line worth quoting
C.add(dict(type="matrix", pos="card", t0=at(262.40, "If") - 0.2, t1=at(318.50, "everything") - 0.25, title="Impact x urgency",
           dots=[dict(label="Offline mode", t=at(270.30, "offline"), x=0.82, y=0.18, tone="pop"),
                 dict(label="Team spaces", t=at(289.70, "spaces"), x=0.40, y=0.30, tone="acc")], hot_t=at(305.10, "impact")))
C.add(dict(type="quote", pos="card", t0=at(318.50, "everything") - 0.2, t1=at(322.90, "high.", "end") + 0.7,
           t=at(318.50, "everything"), text="If everything's high, nothing's high.", who="Alex"))

# ---- a number said out loud gets a burst; a decision gets a stamp
C.add(dict(type="burst", t0=at(361.20, "40%") - 0.1, t1=at(361.20, "40%", "end") + 1.4, t=at(361.20, "40%"), text="40%"))
C.add(dict(type="stamp", t0=at(377.40, "beta") - 0.12, t1=at(377.40, "beta", "end") + 1.5, t=at(377.40, "beta"), text="Beta in May", tone="primary"))

C.write()
