import dataclasses
import functools
import logging
import pathlib
import typing

import diskcache
import platformdirs

logger = logging.getLogger(__name__)


class Cache(typing.Protocol):
    def get(self, k: str) -> typing.Any | None: ...

    def set(self, k: str, v: typing.Any, ttl: int | None) -> None: ...


class NullCache:
    def get(self, k: str) -> typing.Any | None:
        return None

    def set(self, k: str, v: typing.Any, ttl: int | None) -> None:
        pass


@dataclasses.dataclass(frozen=True)
class DiskcacheCache:
    project_slug: str
    size_limit_mb: int = 100

    @functools.cached_property
    def _cache(self) -> diskcache.Cache:
        cache_dir = (
            pathlib.Path(platformdirs.user_cache_dir("circle-cli")) / self.project_slug
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Diskcache using directory %s", cache_dir)
        size_limit = self.size_limit_mb * 1024 * 1024
        return diskcache.Cache(
            cache_dir,
            size_limit=size_limit,
            eviction_policy="least-recently-used",
        )

    def get(self, k: str) -> typing.Any | None:
        try:
            result = self._cache[k]
            logger.info("Cache hit: %s", k)
            return result
        except KeyError:
            logger.info("Cache miss: %s", k)
            return None

    def set(self, k: str, v: typing.Any, ttl: int | None) -> None:
        if ttl == 0:
            return
        self._cache.set(k, v, expire=ttl)

    def size(self) -> int:
        """Return cache size in bytes."""
        return self._cache.volume()

    def prune(self) -> None:
        """Remove expired items."""
        self._cache.expire()

    def clear(self) -> None:
        """Clear all items."""
        self._cache.clear()
