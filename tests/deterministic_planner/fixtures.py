from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable

from mathhead.capability_registry import (
    capability_route_result_bytes,
    make_capability_availability,
    make_capability_route_request,
    route_capabilities,
)
from mathhead.deterministic_planner import (
    RESOURCE_DIMENSIONS,
    make_planning_policy,
    make_planning_request,
)
from tests.capability_registry.fixtures import RouteFixture, plugin_bytes, sha


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def self_hash(value: dict[str, object], field: str) -> None:
    value[field] = None
    value[field] = hashlib.sha256(canonical(value)).hexdigest()


class PlannerFixture:
    def __init__(self) -> None:
        self.route_fixture = RouteFixture()
        availability = make_capability_availability(platform="linux", python_version="3.12")
        request = make_capability_route_request(
            **self.route_fixture.request_fields,
            availability=availability,
        )
        result = route_capabilities(request, (), self.route_fixture.artifacts)
        if result.status != "unsupported" or result.fragment is None:
            raise AssertionError(result)
        self.fragment = result.fragment
        self.descriptor = plugin_bytes(self.fragment)
        self.artifacts = self.route_fixture.artifacts

    def descriptors(
        self,
        count: int = 1,
        *,
        mutation: Callable[[dict[str, Any]], None] | None = None,
    ) -> tuple[bytes, ...]:
        if count == 1 and mutation is None:
            return (self.descriptor,)
        return tuple(
            plugin_bytes(
                self.fragment,
                suffix=f"planner_{index}",
                base_cost=5 + index,
                priority=100 - index,
                mutation=mutation,
            )
            for index in range(count)
        )

    def route_request(
        self,
        descriptors: tuple[bytes, ...],
        *,
        request_changes: dict[str, object] | None = None,
        availability_changes: dict[str, object] | None = None,
    ) -> bytes:
        fields = copy.deepcopy(self.route_fixture.request_fields)
        if request_changes:
            fields.update(request_changes)
        availability_fields: dict[str, object] = {
            "platform": "linux",
            "python_version": "3.12",
            "available_descriptor_sha256s": tuple(sorted({sha(item) for item in descriptors})),
        }
        if availability_changes:
            availability_fields.update(availability_changes)
        availability = make_capability_availability(**availability_fields)
        return make_capability_route_request(**fields, availability=availability)

    def planning_inputs(
        self,
        descriptors: tuple[bytes, ...] | None = None,
        *,
        request_changes: dict[str, object] | None = None,
        availability_changes: dict[str, object] | None = None,
        limits: dict[str, int] | None = None,
        maximum_strategies: int = 100_000,
        policy_mode: str = "registry_order",
    ) -> tuple[bytes, bytes, tuple[bytes, ...], tuple[bytes, ...]]:
        selected = (self.descriptor,) if descriptors is None else descriptors
        route_request = self.route_request(
            selected,
            request_changes=request_changes,
            availability_changes=availability_changes,
        )
        route = route_capabilities(route_request, selected, self.artifacts)
        route_bytes = capability_route_result_bytes(route)
        resources = (
            {name: 1_000_000_000_000 for name in RESOURCE_DIMENSIONS}
            if limits is None
            else limits
        )
        policy = make_planning_policy(
            mode=policy_mode,
            maximum_strategies=maximum_strategies,
        )
        request = make_planning_request(
            route_request=route_request,
            route_result=route_bytes,
            resource_limits=resources,
            policy=policy,
        )
        return request, route_bytes, selected, self.artifacts
