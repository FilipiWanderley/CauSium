from __future__ import annotations

from unittest.mock import patch, MagicMock


def test_redis_pool_with_rediss_url_removes_ssl_from_kwargs():
    """Test that Redis pool creation with rediss:// URL removes ssl from connection_kwargs.

    Regression test for: AbstractConnection.__init__() got an unexpected keyword argument 'ssl'
    redis-py 8.x adds ssl=True to connection_kwargs automatically for rediss:// URLs,
    but Connection.__init__ doesn't accept ssl parameter.
    """
    from app.core.redis import get_redis_pool

    # Reset global state
    import app.core.redis as redis_module
    redis_module._redis_pool = None
    redis_module._redis_pool_loop_id = None

    mock_settings = MagicMock()
    mock_settings.redis_url_effective = "rediss://user:pass@causium-redis.redis.cache.windows.net:6380/0"
    mock_settings.redis_ssl_verify = True
    mock_settings.redis_ssl_ca_file = ""
    mock_settings.redis_ssl_min_version = "TLSv1.2"

    with patch("app.core.redis.get_settings", return_value=mock_settings):
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_pool = MagicMock()
            mock_pool.connection_pool = MagicMock()
            mock_pool.connection_pool.connection_kwargs = {
                "encoding": "utf-8",
                "decode_responses": True,
                "ssl": True,  # redis-py 8.x adds this automatically
                "host": "localhost",
                "port": 6380,
                "db": 0,
            }
            mock_from_url.return_value = mock_pool

            _ = get_redis_pool()

            # Verify from_url was called
            mock_from_url.assert_called_once()

            # Verify ssl was removed from connection_kwargs
            assert "ssl" not in mock_pool.connection_pool.connection_kwargs, (
                "ssl should be removed from connection_kwargs to avoid TypeError"
            )


def test_redis_pool_with_http_url_no_ssl_removed():
    """Test that Redis pool creation with redis:// URL (no SSL) works without removing ssl."""
    from app.core.redis import get_redis_pool

    # Reset global state
    import app.core.redis as redis_module
    redis_module._redis_pool = None
    redis_module._redis_pool_loop_id = None

    mock_settings = MagicMock()
    mock_settings.redis_url_effective = "redis://localhost:6379/0"
    mock_settings.redis_ssl_verify = True
    mock_settings.redis_ssl_ca_file = ""
    mock_settings.redis_ssl_min_version = "TLSv1.2"

    with patch("app.core.redis.get_settings", return_value=mock_settings):
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_pool = MagicMock()
            mock_pool.connection_pool = MagicMock()
            mock_pool.connection_pool.connection_kwargs = {
                "encoding": "utf-8",
                "decode_responses": True,
                "host": "localhost",
                "port": 6379,
                "db": 0,
            }
            mock_from_url.return_value = mock_pool

            _ = get_redis_pool()

            # Verify from_url was called
            mock_from_url.assert_called_once()

            # Verify ssl was NOT added (it shouldn't be in kwargs for redis://)
            assert "ssl" not in mock_pool.connection_pool.connection_kwargs, (
                "ssl should not be in connection_kwargs for redis:// URLs"
            )


def test_redis_pool_disabled_when_no_url():
    """Test that Redis pool returns DisabledRedis when REDIS_URL is empty."""
    from app.core.redis import get_redis_pool, DisabledRedis

    # Reset global state
    import app.core.redis as redis_module
    redis_module._redis_pool = None
    redis_module._redis_pool_loop_id = None

    mock_settings = MagicMock()
    mock_settings.redis_url_effective = ""

    with patch("app.core.redis.get_settings", return_value=mock_settings):
        pool = get_redis_pool()

        # Verify DisabledRedis is returned
        assert isinstance(pool, DisabledRedis), "Should return DisabledRedis when no URL"
