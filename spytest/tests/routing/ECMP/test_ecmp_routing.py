"""Compatibility shim for legacy ECMP routing test discovery."""

from __future__ import annotations

from spytest.tests.routing.ecmp.test_ecmp_routing_suite import (
    TestEcmpRoutingSuite as _Suite,
)


class TestEcmpRouting(_Suite):
    """Backward compatible alias keeping historical module path alive."""

    pass
