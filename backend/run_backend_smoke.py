import json
import os
import subprocess
import time
import urllib.request
import urllib.error

BACKEND_CMD = [
    "python",
    "-m",
    "uvicorn",
    "main:app",
    "--port",
    "9101",
    "--host",
    "127.0.0.1"
]
LOG_PATH = "backend_smoke_runtime.log"
HEALTH_URL = "http://127.0.0.1:9101/health"

ENDPOINTS = [
    {"name": "health", "method": "GET", "url": "http://127.0.0.1:9101/health"},
    {"name": "test", "method": "GET", "url": "http://127.0.0.1:9101/api/test"},
    {"name": "data-sources", "method": "GET", "url": "http://127.0.0.1:9101/api/public/data-sources"},
    {"name": "forecast-trend", "method": "GET", "url": "http://127.0.0.1:9101/api/public/forecast-trend?lat=-37.7&lon=176.2"},
    {"name": "history", "method": "GET", "url": "http://127.0.0.1:9101/api/public/history?lat=-43.5&lon=172.6&days=30"},
    {"name": "drought-risk", "method": "GET", "url": "http://127.0.0.1:9101/api/public/drought-risk?lat=-43.5&lon=172.6&region=Canterbury"},
    {"name": "news-headlines", "method": "GET", "url": "http://127.0.0.1:9101/api/public/news-headlines"},
    {"name": "council-alerts", "method": "GET", "url": "http://127.0.0.1:9101/api/public/council-alerts"},
    {"name": "weather-narrative", "method": "GET", "url": "http://127.0.0.1:9101/api/public/weather-narrative"},
    {"name": "triggers-evaluate", "method": "POST", "url": "http://127.0.0.1:9101/api/triggers/evaluate", "body": json.dumps({"user_id": 1, "weather_data": {"temperature": 20, "rainfall": 5, "humidity": 55, "wind_speed": 8}})},
    {"name": "hilltop-sites", "method": "GET", "url": "http://127.0.0.1:9101/api/public/hilltop/sites"},
    {"name": "hilltop-measurements", "method": "GET", "url": "http://127.0.0.1:9101/api/public/hilltop/measurements?site=Stony%20at%20Mangatete%20Bridge"},
    {"name": "hilltop-data", "method": "GET", "url": "http://127.0.0.1:9101/api/public/hilltop/data?site=Stony%20at%20Mangatete%20Bridge&measurement=Flow&days=1"},
]


def wait_for_health(url: str, timeout: int = 90) -> None:
    """Poll the health endpoint until it responds or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"Backend did not become healthy within {timeout} seconds")


def fetch(url: str, method: str = "GET", data: str | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, method=method.upper())
    if data is not None:
        encoded = data.encode("utf-8")
        req.data = encoded
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
        return resp.status, body


def main() -> None:
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)

    log_file = open(LOG_PATH, "w", encoding="utf-8")
    proc = subprocess.Popen(
        BACKEND_CMD,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    results: list[dict[str, str | int]] = []
    try:
        wait_for_health(HEALTH_URL)
        for endpoint in ENDPOINTS:
            name = endpoint["name"]
            method = endpoint["method"]
            url = endpoint["url"]
            body = endpoint.get("body")

            entry: dict[str, str | int] = {"endpoint": name, "url": url}
            try:
                status_code, response_body = fetch(url, method, body)
                entry["status"] = "OK"
                entry["code"] = status_code
                entry["sample"] = response_body[:400]
            except urllib.error.HTTPError as http_err:
                entry["status"] = "HTTPError"
                entry["code"] = http_err.code
                entry["sample"] = http_err.read().decode("utf-8", errors="ignore")[:200]
            except Exception as exc:  # pylint: disable=broad-except
                entry["status"] = "FAIL"
                entry["sample"] = str(exc)
            results.append(entry)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        log_file.close()

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
