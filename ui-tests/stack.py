"""Start the UI test application against an isolated PostgreSQL Testcontainer."""

import os
import signal
import socket
import subprocess
import tempfile
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from testcontainers.community.postgres import PostgresContainer


BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "petify-frontend"
JAR = BACKEND / "target" / "petify-0.0.1-SNAPSHOT.jar"


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _frontend_port():
    for port in (5173, 5176):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("UI tests need port 5173 or 5176 free for the frontend")


def _stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def _wait_for(url, process, log, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except (HTTPError, URLError, TimeoutError):
            pass
        time.sleep(0.5)
    log.flush()
    log.seek(0)
    tail = log.read()[-4000:]
    raise RuntimeError("Service did not become ready at %s. Recent output:\n%s" % (url, tail))


@contextmanager
def managed_ui_stack():
    if not (FRONTEND / "package.json").exists():
        raise RuntimeError("Expected the frontend checkout at %s" % FRONTEND)
    if not (FRONTEND / "node_modules" / ".bin" / "vite").exists():
        raise RuntimeError("Install frontend dependencies with npm ci in %s" % FRONTEND)

    build = subprocess.run(
        [str(BACKEND / "mvnw"), "-q", "-DskipTests", "package"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )
    if build.returncode:
        raise RuntimeError("Backend build failed:\n%s" % (build.stdout + build.stderr)[-4000:])

    with ExitStack() as cleanup:
        postgres = cleanup.enter_context(PostgresContainer(
            "postgres:15-alpine", username="petify_ui", password="petify_ui", dbname="petify_ui"
        ))
        api_port = _free_port()
        frontend_port = _frontend_port()
        api_url = "http://localhost:%s" % api_port
        base_url = "http://localhost:%s" % frontend_port

        runtime_dir = cleanup.enter_context(tempfile.TemporaryDirectory(prefix="petify-ui-"))
        backend_log = cleanup.enter_context(open(Path(runtime_dir) / "backend.log", "w+"))
        backend = subprocess.Popen(
            [
                "java", "-jar", str(JAR),
                "--spring.profiles.active=ui-test",
                "--spring.datasource.url=jdbc:postgresql://%s:%s/%s" % (
                    postgres.get_container_host_ip(), postgres.get_exposed_port(5432), postgres.dbname
                ),
                "--spring.datasource.username=%s" % postgres.username,
                "--spring.datasource.password=%s" % postgres.password,
                "--server.port=%s" % api_port,
                "--spring.jpa.show-sql=false",
                "--logging.level.org.flywaydb=INFO",
                "--logging.level.org.springframework.jdbc=INFO",
                "--logging.level.com.zaxxer.hikari=INFO",
            ],
            cwd=runtime_dir,
            stdout=backend_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        cleanup.callback(_stop, backend)
        _wait_for(api_url + "/actuator/health", backend, backend_log, timeout=90)

        frontend_log = cleanup.enter_context(open(Path(runtime_dir) / "frontend.log", "w+"))
        frontend_env = os.environ.copy()
        frontend_env["VITE_API_BASE_URL"] = ""
        frontend_env["PETIFY_UI_PROXY_TARGET"] = api_url
        frontend = subprocess.Popen(
            [
                str(FRONTEND / "node_modules" / ".bin" / "vite"),
                "--config", str(BACKEND / "ui-tests" / "vite.config.mjs"),
                "--host", "localhost", "--port", str(frontend_port), "--strictPort",
            ],
            cwd=FRONTEND,
            env=frontend_env,
            stdout=frontend_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        cleanup.callback(_stop, frontend)
        _wait_for(base_url + "/", frontend, frontend_log, timeout=30)

        yield base_url, api_url
