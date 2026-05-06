"""
TLS context factory for datastore connections (SP-A07).

All three datastores — PostgreSQL (asyncpg), Redis (redis.asyncio), and
ClickHouse (clickhouse-connect) — accept an ssl.SSLContext at connection
time, which lets us enforce a minimum TLS protocol version and pin a custom
CA certificate from a single, auditable location.

Supported minimum TLS versions: TLSv1.2, TLSv1.3 (production default: TLSv1.3)

Design notes
------------
* asyncpg (PostgreSQL):
    Accepts ssl.SSLContext via connect_args={"ssl": ctx} in SQLAlchemy
    create_async_engine(). The minimum_version attribute is honoured by
    OpenSSL before the TLS handshake.

* redis.asyncio:
    In this project version, prefer TLS kwargs in from_url() (ssl_cert_reqs,
    ssl_check_hostname, ssl_ca_certs, ssl_min_version) with rediss:// URLs.

* clickhouse-connect (ClickHouse):
    clickhouse-connect < 0.8 does not accept an SSLContext directly; it
    builds one internally from the ca_cert path. Client-side minimum TLS
    version is therefore influenced by the underlying OpenSSL defaults and
    the ClickHouse *server* configuration (config.xml disableProtocols).
    This module enforces TLS 1.3 for asyncpg and redis where direct context
    injection is supported. For ClickHouse, set
        <disableProtocols>sslv2,sslv3,tlsv1,tlsv1_1,tlsv1_2</disableProtocols>
    in ClickHouse's server config and ensure CLICKHOUSE_VERIFY=true in
    production so the client always validates the server certificate.
"""
from __future__ import annotations

import ssl
from pathlib import Path

_VERSION_MAP: dict[str, ssl.TLSVersion] = {
    "TLSv1.2": ssl.TLSVersion.TLSv1_2,
    "TLSv1.3": ssl.TLSVersion.TLSv1_3,
}


def build_ssl_context(
    *,
    verify: bool = True,
    ca_file: str | None = None,
    min_version: str = "TLSv1.3",
) -> ssl.SSLContext:
    """
    Build a client-side SSLContext for outbound datastore connections.

    Args:
        verify:       Verify the server's certificate chain and hostname.
                      Set ``False`` only for self-signed certs in local dev.
        ca_file:      Path to a PEM-encoded CA certificate bundle. Omit to
                      use the system / OS trust store.
        min_version:  Minimum TLS protocol version. Allowed: ``'TLSv1.2'``,
                      ``'TLSv1.3'``. Production must be ``'TLSv1.3'``.

    Returns:
        A configured ``ssl.SSLContext`` ready to be passed to asyncpg,
        redis.asyncio, or an httpx transport.

    Raises:
        ValueError:       If ``min_version`` is not a recognised value.
        FileNotFoundError: If ``ca_file`` is given but the path does not exist.
    """
    if min_version not in _VERSION_MAP:
        raise ValueError(
            f"Unsupported TLS version '{min_version}'. "
            f"Allowed: {sorted(_VERSION_MAP)}"
        )

    if ca_file and not Path(ca_file).is_file():
        raise FileNotFoundError(f"CA certificate file not found: '{ca_file}'")

    ctx = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=ca_file or None,
    )
    ctx.minimum_version = _VERSION_MAP[min_version]

    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    return ctx


def maybe_ssl_context(
    *,
    enabled: bool,
    verify: bool = True,
    ca_file: str | None = None,
    min_version: str = "TLSv1.3",
) -> ssl.SSLContext | None:
    """
    Return a built ``SSLContext`` when ``enabled`` is ``True``, else ``None``.

    Convenience wrapper so call-sites remain explicit::

        ctx = maybe_ssl_context(
            enabled=settings.db_ssl_enabled,
            verify=settings.db_ssl_verify,
            ca_file=settings.db_ssl_ca_file or None,
            min_version=settings.db_ssl_min_version,
        )
    """
    if not enabled:
        return None
    return build_ssl_context(verify=verify, ca_file=ca_file or None, min_version=min_version)
