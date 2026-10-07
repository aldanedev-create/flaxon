"""Trusted host validation behavior and boundary cases."""

import pytest

from flaxon.middleware.trusted_hosts import TrustedHostsMiddleware


@pytest.mark.parametrize("host", ["example.com", "EXAMPLE.COM", "example.com:8000"])
def test_authorized_hosts_and_ports_are_accepted(host):
    assert TrustedHostsMiddleware(None, ["example.com"])._is_allowed(host)


@pytest.mark.parametrize(
    "host",
    [
        "evil.com",
        "example.com.evil",
        "evil@example.com",
        "example.com/path",
        "example.com?x=1",
        "example.com#fragment",
        "[",
        "example.com:invalid",
        "example.com:99999",
        " example.com",
    ],
)
def test_malformed_or_untrusted_authorities_are_rejected(host):
    assert not TrustedHostsMiddleware(None, ["example.com"])._is_allowed(host)


def test_ipv6_host_and_port_are_supported():
    assert TrustedHostsMiddleware(None, ["::1"])._is_allowed("[::1]:8000")
