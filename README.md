# Mini Energy Gateway

Lab exercise for *Software Engineering for Electrical Engineers – Module C: Software Architectures*.

A software gateway for a solar inverter: it reads measurements over **Modbus TCP** and exposes them via a **REST API** and **MQTT**.

```
Inverter / simulator --Modbus TCP--> Gateway --HTTP GET /api/measurements--> clients
                                        └------MQTT solar/inverter01/readings--> Mosquitto --> subscribers
```

**New here?** Read the [Handover](docs/HANDOVER.md) for the current status and open decisions, then the [User Guide](docs/USER_GUIDE.md) for installation, running, checks, troubleshooting and our Git workflow.

## Tasks

| Task | Where |
|---|---|
| 1 – Requirements | `docs/Mini_Energy_Gateway_Requirements_Architecture.docx` |
| 2 – Architecture | same document, diagram source in `docs/architecture.drawio` |
| 3 – Read Modbus (pymodbus): DC voltage `0x0010`, AC power `0x0020` | `gateway/hal/` |
| 4 – REST API (FastAPI): `GET /api/measurements` | `gateway/api/rest.py` |
| 5 – MQTT publish (paho-mqtt): `solar/inverter01/readings` every 5 s | `gateway/mqtt/publisher.py` |

## Project structure

The code follows the layered architecture from the design document.

```
gateway/
  api/rest.py            Layer 4 – REST API (Task 4)
  mqtt/publisher.py      Layer 4 – MQTT publisher (Task 5)
  services/poller.py     Layer 3 – reads the inverter every 5 s
  services/store.py      Layer 3 – latest measurement, shared by REST and MQTT
  hal/modbus_reader.py   Layer 2 – Modbus TCP client (Task 3)
  hal/register_map.py    Layer 2 – register addresses, data types, decoding
  config.py, models.py   settings and the Measurement data model
  main.py                wires everything together
simulator/inverter_sim.py  Modbus TCP simulator of the inverter
tests/                     unit tests (pytest)
docs/                      requirements, architecture diagram
```

## Setup

Requires Python 3.11 or newer and a running MQTT broker ([Mosquitto](https://mosquitto.org/download/)).

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Use three terminals (activate the virtual environment in each):

```bash
# 1. inverter simulator (Modbus TCP on port 5020)
python simulator/inverter_sim.py

# 2. gateway (REST on port 8000, publishes to the broker on port 1883)
python -m gateway

# 3. watch the MQTT messages
mosquitto_sub -h localhost -t "solar/#" -v
```

Then open <http://localhost:8000/api/measurements> (Swagger UI: <http://localhost:8000/docs>).

Example payload, identical for REST and MQTT:

```json
{
  "device_id": "inverter01",
  "timestamp": "2026-11-03T10:15:00Z",
  "dc_voltage_v": 612.4,
  "ac_power_w": 4870.0,
  "status": "ok"
}
```

`status` is `ok`, `error` (last read failed, values are the last good ones) or `stale` (no successful read for three poll intervals). Before the first reading the REST API answers with HTTP 503.

## Configuration

Set environment variables to override the defaults:

| Variable | Default | Meaning |
|---|---|---|
| `MODBUS_HOST` / `MODBUS_PORT` | `127.0.0.1` / `5020` | Inverter address (ModRSsim2 and diagslave use port 502) |
| `MODBUS_UNIT_ID` | `1` | Modbus unit ID |
| `POLL_INTERVAL_S` | `5` | Modbus polling interval |
| `MQTT_HOST` / `MQTT_PORT` | `127.0.0.1` / `1883` | MQTT broker |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | – | Broker credentials (optional) |
| `PUBLISH_INTERVAL_S` | `5` | MQTT publish interval |
| `HTTP_HOST` / `HTTP_PORT` | `127.0.0.1` / `8000` | REST API address |
| `API_KEY` | – | If set, REST clients must send it in the `X-API-Key` header (otherwise HTTP 401) |
| `GATEWAY_DEVICE_ID` | `inverter01` | Used in the payload and the MQTT topic |

The registers are assumed to hold 32-bit floats in two holding registers (high word first). For a simulator that stores 16-bit integers, change `data_type` and `scale` in `gateway/hal/register_map.py`.

## Tests

```bash
pytest
```
