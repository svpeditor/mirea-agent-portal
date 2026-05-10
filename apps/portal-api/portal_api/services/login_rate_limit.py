"""Rate limit для /api/auth/login через Redis sliding window.

Защита от brute-force подбора паролей. Считаем неудачные попытки логина
по паре (ip, email_lower). 5 попыток за 15 минут — на 6-й 429 Too Many
Requests с Retry-After-секундами в заголовке.

Хранилище: ZSET в Redis, score = timestamp.unix. Очистка через
ZREMRANGEBYSCORE на каждый вход. TTL ключа = window_seconds.

Fail-open: если Redis недоступен — пропускаем (логируем). Падение
Redis не должно полностью блокировать логин в системе.
"""
# ruff: noqa: RUF002
from __future__ import annotations

import contextlib
import logging
import time
from dataclasses import dataclass

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

LIMIT_DEFAULT = 5
WINDOW_SECONDS_DEFAULT = 15 * 60


@dataclass(frozen=True)
class LoginRateLimit:
    redis_url: str
    limit: int = LIMIT_DEFAULT
    window_seconds: int = WINDOW_SECONDS_DEFAULT

    def _key(self, ip: str, email: str) -> str:
        return f"login_rl:{ip}:{email.lower()}"

    async def check(self, ip: str, email: str) -> tuple[bool, int]:
        """Вернуть (allowed, retry_after_seconds).

        retry_after — сколько секунд до следующего разрешённого запроса.
        Для allowed=True значение всегда 0. Fail-open при ошибке Redis.
        """
        if not ip or not email:
            return True, 0
        client = AsyncRedis.from_url(self.redis_url)
        key = self._key(ip, email)
        now = time.time()
        cutoff = now - self.window_seconds
        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            pipe.zrange(key, 0, 0, withscores=True)
            _, count, oldest = await pipe.execute()
            count = int(count or 0)
            if count >= self.limit:
                if oldest:
                    oldest_ts = float(oldest[0][1])
                    retry_after = max(1, int(oldest_ts + self.window_seconds - now))
                else:
                    retry_after = self.window_seconds
                return False, retry_after
            return True, 0
        except (RedisError, OSError) as exc:
            logger.warning("login_rate_limit.check redis error (fail-open): %s", exc)
            return True, 0
        finally:
            with contextlib.suppress(RedisError, OSError):
                await client.aclose()

    async def record_failure(self, ip: str, email: str) -> None:
        """Инкрементировать счётчик после неудачи. Сбрасывается через
        window_seconds. Молча игнорирует ошибки Redis."""
        if not ip or not email:
            return
        client = AsyncRedis.from_url(self.redis_url)
        key = self._key(ip, email)
        now = time.time()
        try:
            pipe = client.pipeline()
            member = f"{now}:{time.monotonic_ns()}"
            pipe.zadd(key, {member: now})
            pipe.expire(key, self.window_seconds)
            await pipe.execute()
        except (RedisError, OSError) as exc:
            logger.warning("login_rate_limit.record_failure redis error: %s", exc)
        finally:
            with contextlib.suppress(RedisError, OSError):
                await client.aclose()

    async def reset(self, ip: str, email: str) -> None:
        """Очистить счётчик после успешного логина."""
        if not ip or not email:
            return
        client = AsyncRedis.from_url(self.redis_url)
        key = self._key(ip, email)
        try:
            await client.delete(key)
        except (RedisError, OSError) as exc:
            logger.warning("login_rate_limit.reset redis error: %s", exc)
        finally:
            with contextlib.suppress(RedisError, OSError):
                await client.aclose()
