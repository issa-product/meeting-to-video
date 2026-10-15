"""cues.py for ONE project (copy to <edit_dir>/cues.py and rewrite for your video).
Worked example (fictional): "Pebble", a notes app. Alex (PM) presents a deck + the app on a screen share, Sam
asks questions, then they chat on camera. Every time is a SOURCE second + the word that carries the beat
(`frames.py words <transcript> <from> <to>`). Screen kinds come from inventory.json: text screens become stage
scenes, visual screens stay in full with side cards. Run: python cues.py (after timeline.py); fix anything it
prints under MISS / CONFLICT / PROBLEMS, then run layout_audit.py.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/meeting-to-video/scripts"))
from cues_lib import Cues

C = Cues(Path(__file__).parent)
at, pre = C.at, C.pre

# ---- captions: mishearing fixes (glossary from intake) and words to highlight
C.fixes = {"pebble": "Pebble", "sink": "sync"}
C.keys |= {"offline", "sync", "spaces", "beta"}
# ---- the other person's lines during the share become bubbles; paraphrase long ones (keyed by how they start)
C.short = {"So I guess my question": "What ships first, and why?"}

# ---- cards
C.cards(title_src=95.40, chapters=[
    (1, "The roadmap", "What Pebble ships next", 95.40),
    (2, "What comes first", "Impact x urgency", 260.10),
    (3, "Offline mode", "Notes that never get lost", 352.80),
], title=dict(kicker="Product walkthrough", big="What's next<br/>for Pebble", sub="Alex Rivera, with Sam"),
   end=dict(kicker="That's the tour", big="Questions?", cta="Ping Alex on Slack", sub="Pebble product team"))

# ---- cold open (camera): a stage headline over the speaker card, landing on the words
C.add(dict(type="stage", layout="headline", t0=at(41.10, "Nobody") - 0.2, t1=at(47.90, "promise.", "end") + 0.6,
           lines=[dict(t=at(42.30, "hour"), text="An hour of roadmap?"),
                  dict(t=at(46.20, "short"), text="Here's the short version.", style="sub")]))

# ---- inventory #2 is a TEXT slide ("Q3 priorities", 3 bullets) -> a stage scene replaces it
C.add(dict(type="stage", layout="bullets", t0=at(98.10, "three") - 0.2, t1=at(131.40, "spaces", "end") + 0.4,
           title="Three things this quarter",
           items=[dict(t=at(101.80, "offline"), icon="zap", text="Offline mode"),
                  dict(t=at(115.30, "search"), icon="sparkles", text="Faster search"),
                  dict(t=at(131.40, "spaces"), icon="users", text="Team spaces")]))

# ---- inventory #3 is VISUAL (the app itself): shown in full; a column card + a label chip (corner is calm)
C.add(dict(type="list", pos="col", t0=at(140.20, "here's") - 0.2, t1=at(171.00, "sync", "end") + 0.5, title="Offline mode",
           rows=[dict(t=at(150.70, "airplane"), icon="zap", text="Write on a plane"),
                 dict(t=at(171.00, "sync"), icon="swap", text="Syncs when you're back")]))
C.add(dict(type="lane", t0=at(140.20, "here's"), t1=at(171.00, "sync", "end") + 0.5, icon="play", text="Live in the beta app"))

# ---- inventory #5 is a TEXT slide (a 2x2) -> stage matrix, then the line worth keeping as a stage quote
C.add(dict(type="stage", layout="matrix", t0=at(262.40, "If") - 0.2, t1=at(318.50, "everything") - 0.25, title="Impact x urgency",
           dots=[dict(label="Offline mode", t=at(270.30, "offline"), x=0.80, y=0.20),
                 dict(label="Team spaces", t=at(289.70, "spaces"), x=0.40, y=0.32)]))
C.add(dict(type="stage", layout="quote", t0=at(318.50, "everything") - 0.2, t1=at(322.90, "high.", "end") + 0.8,
           t=at(318.50, "everything"), text="If everything's high, nothing's high.", who="Alex"))

# ---- a number said out loud -> stage stat (never a burst over a busy slide)
C.add(dict(type="stage", layout="stat", t0=at(361.20, "40%") - 0.2, t1=at(366.80, "offline.", "end") + 0.8,
           t=at(361.20, "40%"), value="40%", label="of notes are written on the go"))

# ---- camera stretch: something in the panel the whole time
C.add(dict(type="track", pos="panel", t0=at(377.40, "beta") - 0.2, t1=at(401.00, "everyone.", "end") + 0.8, title="Road to launch",
           steps=[dict(t=at(377.40, "beta"), text="Beta in May"), dict(t=at(389.20, "feedback"), text="Two weeks of feedback"),
                  dict(t=at(401.00, "everyone."), text="Everyone in June")]))

# ---- zooms are off by default. If one helps (a small UI detail on a VISUAL screen):
# C.zoom("toggle", pre(150.0, "toggle") - 0.2, pre(156.0, "here.", "end") + 0.4, z=1.4, fx=0.7, fy=0.3)  # then zoom_check.py, verified=True

C.write()
