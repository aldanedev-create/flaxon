"""GuardianFlow: a small Flaxon event-intelligence demo.

Run from the repository root with:
    flaxon run examples.guardianflow.app:app --reload --port 8014
"""

from pathlib import Path

from flaxon import Flaxon
from flaxon.jinax import Jinax

from .modules import intelligence_module, notifications_module, ring_module, vision_module
from .ring import RingSimulator
from .routes import pages
from .state import GuardianState

ROOT = Path(__file__).parent
app = Flaxon("guardianflow", debug=True)
app.use_templates(Jinax(ROOT / "templates", auto_reload=True, strict_undefined=True))
app.mount_static("/static", str(ROOT / "static"))

state = GuardianState(str(ROOT / "rules"))
simulator = RingSimulator()
app.container.register_instance("guardian_state", state)
app.container.register_instance("state", state)
app.container.register_instance("ring_simulator", simulator)
state.manager = app.websocket_manager

for module in (pages, ring_module, vision_module, intelligence_module, notifications_module):
    app.mount_module(module)
