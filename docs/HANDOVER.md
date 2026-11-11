# Mini Energy Gateway – Handover

Author: Chuhan Zheng · Date: 11 November 2026

This document hands over my work on the lab exercise to the team: what exists, what was tested, how it relates to the team's Tasks 1–2 document, and what we still have to decide. For installation and usage see the [User Guide](USER_GUIDE.md).

## 1. Status in one table

| Task | Status | Where |
|---|---|---|
| 1 – Requirements | Done (second version next to the team's document, see section 5) | `docs/Mini_Energy_Gateway_Requirements_Architecture.docx` |
| 2 – Architecture | Done (same document), diagram source included | `docs/architecture.drawio`, `docs/architecture.png` |
| 3 – Read Modbus with pymodbus | Done and tested | `gateway/hal/` |
| 4 – REST API with FastAPI | Done and tested | `gateway/api/rest.py` |
| 5 – MQTT publish with paho-mqtt | Done and tested | `gateway/mqtt/publisher.py` |
| Simulator, unit tests, documentation | Done | `simulator/`, `tests/`, `docs/` |

Repository: <https://gitlab.lrz.de/00000000014C491E/mini-energy-gateway> (mirror: <https://github.com/nomoretry/mini-energy-gateway>)

## 2. What the gateway does

Every 5 seconds it reads the DC voltage (register `0x0010`) and the AC power (register `0x0020`) from the inverter over Modbus TCP. The latest reading is kept in memory and offered in two ways: `GET /api/measurements` returns it as JSON, and the same JSON is published to the MQTT topic `solar/inverter01/readings` every 5 seconds.

Beyond the three tasks it also handles failures: the payload carries a `status` field (`ok`, `error`, `stale`), the gateway reconnects on its own, and the REST API answers 503 until the first reading exists.

## 3. Try it in ten minutes

1. Install Python (3.11 or newer) and Mosquitto.
2. Clone the repository, create a virtual environment, run `pip install -r requirements.txt`.
3. Start `python simulator/inverter_sim.py` in one terminal and `python -m gateway` in another.
4. Open <http://localhost:8000/api/measurements> and run `mosquitto_sub -h localhost -t "solar/#" -v`.

The User Guide has the exact commands, the expected output and a troubleshooting table.

## 4. What was tested

| Test | Result |
|---|---|
| Unit tests (`pytest`): decoding, status logic, REST endpoint, API key | 16 passed |
| End-to-end with the bundled simulator | 503 before the first reading, then 200 with live values |
| REST response time (20 requests) | 27 ms at most |
| MQTT interval, measured at the subscriber | 5.01 s and 4.99 s |
| Inverter stopped | `status` becomes `error`, then `stale` after 15 s |
| Inverter restarted | Back to `ok` within 1 s |
| Mosquitto 2.1.2 as broker | Messages received with `mosquitto_sub` |
| diagslave 3.5 as inverter (course tool) | REST and MQTT return exactly the values written to the registers |
| API key | 401 without or with a wrong key, 200 with the correct key |

Not tested:

- ModRSsim2 (only diagslave was used).
- Python 3.11. Everything ran on Python 3.12 on Windows; the code uses no 3.12-only features.
- Linux and macOS.

## 5. How it relates to the team's Tasks 1–2 document

The team already has `Mini_Energy_Gateway_Tasks_1_2.docx`. The code fulfils every requirement in it:

| Requirement in the team document | In this implementation |
|---|---|
| FR-01 Read DC voltage `0x0010` and AC power `0x0020` over Modbus TCP | `gateway/hal/modbus_reader.py`, addresses in `register_map.py` |
| FR-02 JSON at `GET /api/measurements` | `gateway/api/rest.py` |
| FR-03 JSON to `solar/inverter01/readings` every 5 s | `gateway/mqtt/publisher.py` |
| NFR-01 Reconnect within 10 s | A reconnect is attempted on every 5 s poll; measured recovery 1 s |
| NFR-02 REST response within 200 ms from the cache | Served from memory; measured 27 ms at most |
| NFR-03 README with installation, configuration, endpoints, usage | `README.md` and `docs/USER_GUIDE.md` |
| NFR-04 REST access only with a valid API key | Environment variable `API_KEY`, header `X-API-Key`; see decision 4 below |

The architecture in the team document (Pipes & Filters for ingestion, a shared cache, two output adapters) describes the same components as the code:

| Component in the team document | Code |
|---|---|
| Modbus reader | `gateway/hal/modbus_reader.py` |
| Processing filter (validate, normalise, timestamp) | `gateway/hal/register_map.py` (decoding), check for invalid values in the reader, timestamp in `gateway/services/poller.py` |
| In-memory cache | `gateway/services/store.py` |
| REST API + MQTT | `gateway/api/rest.py`, `gateway/mqtt/publisher.py` |

My own Tasks 1–2 document describes these components as a layered architecture (application, service, hardware abstraction). The two views do not contradict each other: the layers say where a component sits, the pipeline says how data flows through them.

## 6. Decisions for the team

1. **Tasks 1–2 document.** We have two. Either submit the team document as it is, or merge parts of mine into it (the longer requirement list, the component diagram, the comparison of architecture models).
2. **Tasks 3–5 code.** Henri also has a first solution. We should compare both and either pick one or combine them. This repository is a proposal, not a decision.
3. **Repository location.** The code is in my personal namespace. If we use the team group on GitLab, I can transfer the project there or push it to a repository in the group.
4. **API key default.** Right now the API is open unless `API_KEY` is set, so that the quick start works without configuration. If we want NFR-04 to hold strictly, the gateway should refuse to start without a key. This is a one-line change.
5. **Register format.** The exercise does not say how the values are encoded. The code assumes a 32-bit float in two holding registers, high word first. Other formats (16-bit integer with a scale factor) need one changed line in `register_map.py`.
6. **Open tests.** ModRSsim2 and Python 3.11 are untested. Each takes about 15 minutes with the User Guide.

## 7. How to change things

- A new measurement: add one `Register(...)` line to `REGISTER_MAP` in `gateway/hal/register_map.py`.
- Another port, broker or interval: environment variables, listed in the User Guide.
- Any code change: feature branch, `pytest`, merge request. The workflow is in section 10 of the User Guide.
