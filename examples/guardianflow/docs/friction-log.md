# Friction log

## Module namespace

The prompt's illustrative `flaxon/modules` path would shadow Flaxon's installed framework package when the example is run from the repository. GuardianFlow-specific modules therefore live under `examples/guardianflow/modules` and import the real `flaxon.modules.FlaxonModule` API. This keeps the example runnable and demonstrates the framework's actual module system.
