"""Keep the component fixture suite's ordinary socket connections offline."""

import socket

import pytest


@pytest.fixture(autouse=True)
def no_network_connection(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Component fixture tests use local data and stdio.")
    monkeypatch.setattr(socket, "create_connection", blocked)
