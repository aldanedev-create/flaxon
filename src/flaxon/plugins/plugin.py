from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class Plugin(ABC):
    """Plugin implementation for the plugins subsystem."""

    __test__ = False
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    requires: ClassVar[list[str]] = []
    provides: ClassVar[list[str]] = []

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
        """Configure the supplied application or resource."""
        return

    def on_load(self) -> None:
        """Run the optional plugin load hook."""
        return

    def on_unload(self) -> None:
        """Run the optional plugin unload hook."""
        return

    def on_startup(self) -> None:
        """Run the optional plugin startup hook."""
        return

    def on_shutdown(self) -> None:
        """Run the optional plugin shutdown hook."""
        return

    def get_metadata(self) -> dict[str, Any]:
        """Return the configured metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "requires": self.requires,
            "provides": self.provides,
        }


class SimplePlugin(Plugin):
    """Simple plugin implementation for the plugins subsystem."""

    def __init__(  # noqa: PLR0917 - preserve existing positional API
        self,
        name: str,
        setup_func: Any,
        version: str = "0.1.0",
        description: str = "",
        author: str = "",
        requires: list[str] | None = None,
        provides: list[str] | None = None,
    ) -> None:
        self.name = name
        self._setup_func = setup_func
        self.version = version
        self.description = description
        self.author = author
        self.requires = requires or []
        self.provides = provides or []

    def setup(self, app: Any) -> None:
        """Configure the supplied application or resource."""
        self._setup_func(app)
