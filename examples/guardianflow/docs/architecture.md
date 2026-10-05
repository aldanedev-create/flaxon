# GuardianFlow architecture

```text
Ring-shaped event -> RingClient -> VisionPipeline -> Correlator -> YAML policy -> Alert -> WebSocket -> Jinjax
```

The simulator and webhook boundary produce normalized `GuardianEvent` values. The detector turns each event into a `VisionFact`; it does not decide whether a delivery happened. `Correlator` keeps a small in-memory event graph and applies ordered policy sequences. Explanations are generated only after a structured decision exists.

`FlaxonModule` instances make the boundaries visible in `app.py`: pages, Ring ingestion, vision facts, intelligence APIs, and notifications can be mounted independently.
