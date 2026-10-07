"""Template cache eviction behavior and boundary cases."""

from flaxon.jinax.cache import CachedTemplate, TemplateCache


def test_bounded_cache_evicts_oldest_entry(monkeypatch):
    clock = iter([100, 101, 102])
    monkeypatch.setattr("flaxon.jinax.cache.time.time", lambda: next(clock))
    cache = TemplateCache(max_size=2)
    cache.set("a", "A")
    cache.set("b", "B")
    cache.set("c", "C")
    assert cache.size == 2
    assert cache.get("a") is None and cache.get("b") == "B" and cache.get("c") == "C"


def test_clear_resets_values_and_hit_rate():
    cache = TemplateCache()
    cache.set("a", "A")
    assert cache.get("a") == "A"
    assert cache.get("missing") is None
    assert cache.hit_rate == 0.5
    cache.clear()
    assert cache.size == 0 and cache.hit_rate == 0


def test_cached_template_expiration_uses_creation_time(monkeypatch):
    monkeypatch.setattr("flaxon.jinax.cache.time.time", lambda: 100)
    template = CachedTemplate("html", "key", ttl=2)
    assert not template.is_expired()
    monkeypatch.setattr("flaxon.jinax.cache.time.time", lambda: 103)
    assert template.is_expired()
