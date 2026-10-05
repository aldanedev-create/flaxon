from .detector import Detector


class VisionPipeline:
    def __init__(self, detector: Detector | None = None) -> None:
        self.detector = detector or Detector()

    def process(self, event):
        return self.detector.detect(event)
