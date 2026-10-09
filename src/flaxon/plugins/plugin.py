from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Plugin(ABC):
    __test__ = False
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    requires: list[str] = []
    provides: list[str] = []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Every subclass gets its OWN list, copied from whatever it declared
        # (or inherited). Without this, "requires"/"provides" default to the
        # exact same [] object shared across every Plugin subclass, so one
        # plugin appending to its own list silently pollutes every other one.
        cls.requires = list(cls.__dict__.get("requires", cls.requires))
        cls.provides = list(cls.__dict__.get("provides", cls.provides))

    @abstractmethod
    def setup(self, app: Any) -> None:
        pass

    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "requires": self.requires,
            "provides": self.provides,
        }


class SimplePlugin(Plugin):
    def __init__(
        self,
        name: str,
        setup_func: Any,
        version: str = "0.1.0",
        description: str = "",
        author: str = "",
        requires: list[str] = None,
        provides: list[str] = None,
    ) -> None:
        self.name = name
        self._setup_func = setup_func
        self.version = version
        self.description = description
        self.author = author
        self.requires = requires or []
        self.provides = provides or []

    def setup(self, app: Any) -> None:
        self._setup_func(app)
