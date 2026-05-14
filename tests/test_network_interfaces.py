import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main


class DummyResult:
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


@pytest.fixture(autouse=True)
def patch_system_commands(monkeypatch):
    monkeypatch.setattr(main, "run_cmd", lambda cmd: DummyResult(returncode=0, stdout=""))
    monkeypatch.setattr(main, "get_system_interfaces", lambda: ["eth0", "eth1"])
    yield


def test_validate_interface_config_for_dhcp():
    interface = {
        "name": "eth0",
        "type": "wan",
        "bootproto": "dhcp"
    }

    result = main.validate_interface_config(interface)

    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_interface_config_for_static():
    interface = {
        "name": "eth1",
        "type": "lan",
        "bootproto": "static",
        "ipaddr": "192.168.1.100",
        "prefix": "24",
        "gateway": "192.168.1.1",
        "dns1": "8.8.8.8",
        "dns2": "8.8.4.4"
    }

    result = main.validate_interface_config(interface)

    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_interface_config_invalid():
    interface = {
        "name": "",
        "type": "invalid",
        "bootproto": "static",
        "ipaddr": "300.300.300.300",
        "prefix": "40",
        "gateway": "bad.gateway",
        "dns1": "notip",
        "dns2": "12345"
    }

    result = main.validate_interface_config(interface)

    assert result["valid"] is False
    assert "Interface name is required" in result["errors"]
    assert "Interface type must be 'wan' or 'lan'" in result["errors"]
    assert "Invalid IP address" in result["errors"]
    assert "Invalid prefix (must be 0-32)" in result["errors"]
    assert "Invalid gateway IP address" in result["errors"]
    assert "Invalid primary DNS" in result["errors"]
    assert "Invalid secondary DNS" in result["errors"]


def test_read_write_interfaces_config(tmp_path):
    main.INTERFACES_CONFIG_FILE = str(tmp_path / "interfaces.json")
    config = {"interfaces": []}

    assert main.write_interfaces_config(config) is True
    read_config = main.read_interfaces_config()

    assert read_config == config
    assert Path(main.INTERFACES_CONFIG_FILE).exists()


def test_interface_api_flow(tmp_path, monkeypatch):
    main.INTERFACES_CONFIG_FILE = str(tmp_path / "interfaces.json")
    main.NOIP_CONFIG_FILE = str(tmp_path / "noip.json")

    client = TestClient(main.app)

    response = client.post(
        "/login",
        data={"username": main.ADMIN_USER, "password": main.ADMIN_PASS},
        follow_redirects=False,
    )
    assert response.status_code == 303

    response = client.get("/network-interfaces/api/list")
    assert response.status_code == 200
    payload = response.json()
    assert payload["interfaces"] == []
    assert payload["available_interfaces"] == ["eth0", "eth1"]

    response = client.post(
        "/network-interfaces/api/add",
        data={
            "name": "eth0",
            "interface_type": "wan",
            "bootproto": "dhcp"
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    response = client.get("/network-interfaces/api/list")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["interfaces"]) == 1
    assert payload["interfaces"][0]["name"] == "eth0"

    interface_id = payload["interfaces"][0]["id"]

    response = client.post(f"/network-interfaces/api/delete/{interface_id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

    response = client.get("/network-interfaces/api/list")
    assert response.status_code == 200
    assert response.json()["interfaces"] == []

    monkeypatch.setattr(main, "apply_interface_config", lambda interface: {"success": True, "message": "ok"})
    response = client.post("/network-interfaces/api/apply")
    assert response.status_code == 200
    assert response.json()["success"] is True
