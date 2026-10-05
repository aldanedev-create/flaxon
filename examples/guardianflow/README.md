# GuardianFlow

GuardianFlow is a compact Flaxon hackathon demo that transforms camera events into activity stories. It is intentionally small: the judge can press three buttons and see delivery confirmation, package-removal review, and after-hours activity.

## Run it

From the repository root:

```powershell
python -m pip install pyyaml
python -m flaxon run examples.guardianflow.app:app --reload --port 8014
```

Open `http://127.0.0.1:8014/`. No Ring hardware, AWS account, or credentials are required for demo mode.

## Demo flow

1. Press **Simulate delivery**: person detected, package detected, person leaves, delivery confirmed.
2. Press **Simulate removal**: the existing delivery context plus person and package removal produces a review alert.
3. Press **Simulate after-hours**: a person event at 23:15 produces a warning.

The dashboard uses Jinjax templates and a Flaxon WebSocket for live event notifications. `RingClient` is the integration boundary and normalizes Ring-shaped payloads; `RingSimulator` is clearly separate and is what makes the demo deterministic.

## Flaxon modules

The example mounts `guardian-pages`, `guardian-ring`, `guardian-vision`, `guardian-intelligence`, and `guardian-notifications` with `app.mount_module()`. Each module declares its state dependency with `requires()`, so this is a real reusable Flaxon composition rather than a collection of unrelated folders.

The app uses in-memory state for a fast demo. Replace `GuardianState` with a repository-backed implementation when persistence is needed. The policy engine remains independent from the UI and reads the YAML files in `rules/`.
