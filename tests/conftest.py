import socket
import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Public-core tests must be offline")
    monkeypatch.setattr(socket, "create_connection", blocked)
