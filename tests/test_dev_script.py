import os
import socket
import subprocess
import sys


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_dev_script_can_exit_after_workbench_is_ready(tmp_path):
    api_port = free_port()
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": sys.executable,
            "PAPER_LAB_DATA_DIR": str(tmp_path / "data"),
            "API_PORT": str(api_port),
            "DEV_READY_TIMEOUT": "30",
            "DEV_EXIT_AFTER_READY": "true",
            "PAPER_LAB_SCHEDULER_ENABLED": "false",
        }
    )
    for key in [
        "DATABASE_PATH",
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
        "VECTOR_DB_BACKEND",
        "API_BASE_URL",
    ]:
        env.pop(key, None)

    result = subprocess.run(
        ["bash", "scripts/dev.sh"],
        text=True,
        capture_output=True,
        timeout=35,
        env=env,
        check=True,
    )

    assert f"FastAPI:  http://127.0.0.1:{api_port}" in result.stdout
    assert f"工作台:    http://127.0.0.1:{api_port}/ui/" in result.stdout
    assert f"API_BASE_URL=http://127.0.0.1:{api_port}/api/v1" in result.stdout
    assert "DEV_EXIT_AFTER_READY=true" in result.stdout
