from __future__ import annotations

from ..models import GuardianEvent, VisionFact


class Detector:
    def detect(self, event: GuardianEvent) -> VisionFact:
        mapping = {
            "person_detected": ("person", "detected"),
            "person_left": ("person", "left"),
            "package_detected": ("package", "detected"),
            "package_removed": ("package", "removed"),
            "vehicle_detected": ("vehicle", "detected"),
            "motion_detected": ("motion", "detected"),
        }
        object_type, state = mapping.get(event.type, ("motion", "detected"))
        return VisionFact(object_type, event.confidence, event.camera_id, state)
