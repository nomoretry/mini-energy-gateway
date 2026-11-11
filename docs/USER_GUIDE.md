# Mini Energy Gateway – User Guide

This guide explains how to install, run and check the gateway, how the code is organised, and how we work on it together.

## 1. What it does

The gateway reads two measurements from a solar inverter over Modbus TCP every 5 seconds and offers them in two ways:

| Output | How to get the data |
|---|---|
| REST API | Ask for the latest values: `GET http://localhost:8000/api/measurements` |
| MQTT | Receive a message every 5 s on the topic `solar/inverter01/readings` |

Both outputs deliver the same JSON:

```json
{
  "device_id": "inverter01",
  "timestamp": "2026-11-03T10:15:00Z",
  "dc_voltage_v": 612.4,
  "ac_power_w": 4870.0,
  "status": "ok"
}
```

| `status` | Meaning |
|---|---|
| `ok` | The last Modbus read succeeded. |
| `error` | The last read failed; the values are the last good ones. |
| `stale` | No successful read for three poll intervals (15 s). |

Before the first successful read the REST API answers with HTTP 503.

## 2. What you need

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11 or newer | `python --version`. Developed and tested on Python 3.12; the code uses no 3.12-only features, but it has not been run on 3.11 yet. |
| Git | any recent | `git --version` |
| Mosquitto | 2.x | MQTT broker, <https://mosquitto.org/download/>. On Windows the installer registers it as a service that listens on port 1883. |

No inverter hardware is needed: the repository contains a simulator.

## 3. Install

```bash
git clone https://gitlab.lrz.de/00000000014C491E/mini-energy-gateway.git
cd mini-energy-gateway
python -m venv .venv
```

Activate the virtual environment (repeat this in every new terminal):

| System | Command |
|---|---|
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows cmd | `.venv\Scripts\activate.bat` |
| Linux / macOS | `source .venv/bin/activate` |

Then install the libraries:

```bash
pip install -r requirements.txt
```

## 4. Run

Open three terminals in the project folder and activate the virtual environment in each.

**Terminal 1 – inverter simulator**

```bash
python simulator/inverter_sim.py
```

Expected output: `Inverter simulator listening on 127.0.0.1:5020 (unit id 1)`

**Terminal 2 – gateway**

```bash
python -m gateway
```

Expected output: `Modbus read ok: {...}`, `MQTT connected to 127.0.0.1:1883` and `Uvicorn running on http://127.0.0.1:8000`

**Terminal 3 – watch the MQTT messages**

```bash
mosquitto_sub -h localhost -t "solar/#" -v
```

If the command is not found on Windows, call it with its full path, for example `"C:\Program Files\mosquitto\mosquitto_sub.exe"`.

Expected output: `solar/inverter01/status online`, then one `solar/inverter01/readings {...}` line every 5 seconds.

Stop each program with `Ctrl+C`.

## 5. Check that it works

| Check | How | Expected result |
|---|---|---|
| REST API (Task 4) | Open <http://localhost:8000/api/measurements> | JSON with `"status": "ok"`; values change on reload |
| API documentation | Open <http://localhost:8000/docs> | Swagger UI with the endpoint |
| MQTT (Task 5) | Terminal 3 | A new message every 5 s |
| Modbus (Task 3) | Compare REST values with the gateway log | Same values |
| Fault handling | Stop the simulator (`Ctrl+C` in terminal 1) | `status` becomes `error`, after 15 s `stale` |
| Recovery | Start the simulator again | `status` returns to `ok` within one poll interval |
| Unit tests | `pytest` | `13 passed` |

## 6. Configuration

All settings are environment variables; without them the defaults below are used.

| Variable | Default | Meaning |
|---|---|---|
| `MODBUS_HOST` | `127.0.0.1` | Address of the inverter or simulator |
| `MODBUS_PORT` | `5020` | Modbus TCP port |
| `MODBUS_UNIT_ID` | `1` | Modbus unit ID |
| `POLL_INTERVAL_S` | `5` | How often the inverter is read |
| `MQTT_HOST` / `MQTT_PORT` | `127.0.0.1` / `1883` | MQTT broker |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | not set | Broker login, if required |
| `PUBLISH_INTERVAL_S` | `5` | How often a message is published |
| `HTTP_HOST` / `HTTP_PORT` | `127.0.0.1` / `8000` | Address of the REST API |
| `GATEWAY_DEVICE_ID` | `inverter01` | Used in the payload and the MQTT topic |

Example for Windows PowerShell, then start the gateway in the same terminal:

```powershell
$env:MODBUS_PORT = "502"
python -m gateway
```

Example for Linux / macOS:

```bash
MODBUS_PORT=502 python -m gateway
```

## 7. Using ModRSsim2 or diagslave instead of our simulator

These simulators start with all registers at 0 and do not change them on their own, so you have to write test values first.

**diagslave** (command line, <https://www.modbusdriver.com/diagslave.html>):

```bash
# Terminal 1: start diagslave as Modbus TCP server on port 502
diagslave -m tcp

# Terminal 2: write test values (DC voltage 612.5 V, AC power 4870 W)
python simulator/set_registers.py 612.5 4870

# Terminal 2: start the gateway against port 502
#   Windows PowerShell:  $env:MODBUS_PORT = "502"; python -m gateway
#   Linux / macOS:       MODBUS_PORT=502 python -m gateway
```

<http://localhost:8000/api/measurements> must then show `"dc_voltage_v": 612.5` and `"ac_power_w": 4870.0`. Run `set_registers.py` again with other numbers and the output follows within 5 seconds.

Tested on 11 November 2026 with diagslave 3.5 on Windows: REST and MQTT returned exactly the written values, and changed values appeared after the next poll.

**ModRSsim2** (Windows GUI): choose *Modbus TCP/IP*, then either run `set_registers.py` as above or type the values by hand. Not tested yet.

Notes for both tools:

- The values live in **holding registers**.
- Mind the address offset: the exercise gives zero-based addresses. `0x0010` is address 16, shown as **40017** in ModRSsim2; `0x0020` is address 32, shown as **40033**.
- The gateway expects a 32-bit float in two registers, high word first. If you store a 16-bit integer instead, change the entry in `gateway/hal/register_map.py`, for example:

```python
Register(name="dc_voltage_v", address=0x0010, unit="V", data_type="uint16", scale=0.1, decimals=1)
```

## 8. How the code is organised

The code follows the layered architecture described in `Mini_Energy_Gateway_Requirements_Architecture.docx`.

| Layer | File | Responsibility |
|---|---|---|
| 4 – Application | `gateway/api/rest.py` | REST endpoint (Task 4) |
| 4 – Application | `gateway/mqtt/publisher.py` | MQTT publisher (Task 5) |
| 3 – Service | `gateway/services/poller.py` | Reads the inverter every 5 s |
| 3 – Service | `gateway/services/store.py` | Holds the latest measurement for REST and MQTT |
| 2 – HAL | `gateway/hal/modbus_reader.py` | Modbus TCP client (Task 3) |
| 2 – HAL | `gateway/hal/register_map.py` | Register addresses, data types, decoding |
| – | `gateway/config.py`, `gateway/models.py` | Settings and the `Measurement` data model |
| – | `gateway/main.py` | Creates the components and connects them |

Data flow: `Poller` → `ModbusReader.read()` → `MeasurementStore.update()`. The REST API and the MQTT publisher only call `MeasurementStore.get_latest()`; they never talk to Modbus.

To add a measurement, add one `Register(...)` line to `REGISTER_MAP`. It then appears in the REST response and the MQTT payload without further changes.

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| REST returns 503 | The inverter has not been read yet | Start the simulator; check `MODBUS_HOST` / `MODBUS_PORT` |
| `status` is `stale` | The simulator stopped or is unreachable | Restart the simulator |
| No MQTT messages | Mosquitto is not running | Windows: start the *Mosquitto Broker* service; Linux: `sudo systemctl start mosquitto` |
| `Address already in use` | Port 8000 or 5020 is taken | Stop the other program or change `HTTP_PORT` / `--port` |
| `ModuleNotFoundError` | Virtual environment not active | Activate it and run `pip install -r requirements.txt` |
| Simulator fails on import | pymodbus older than 3.16 | `pip install -U -r requirements.txt` |
| `git` reports `SEC_E_UNTRUSTED_ROOT` for gitlab.lrz.de | Windows lacks the root certificate | Run `git config --global http.sslBackend openssl` |

## 10. Working together

`main` always holds a working version. Changes go through a feature branch and a merge request.

```bash
git switch main
git pull
git switch -c feature/<short-name>
```

Edit, then check and commit:

```bash
pytest
git add .
git commit -m "Describe what changed and why"
git push -u origin feature/<short-name>
```

Then open a **merge request** on GitLab, ask a teammate to review it, and merge it into `main` after approval.

Rules that keep conflicts rare:

- Pull before you start new work.
- Keep commits small and branches short-lived.
- Say in the team chat which file you are working on.

Open points are tracked as issues on GitLab.
