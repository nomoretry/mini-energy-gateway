# Mini Energy Gateway: Handover

Chuhan Zheng, 11 November 2026

I couldn't join the meeting, so here is everything I did on the lab exercise, what I tested and what I think we still have to decide together. How to install and run it is in the [User Guide](USER_GUIDE.md).

## 1. What is done

All five tasks have a first version in this repository:

- Task 1 and 2: my own requirements and architecture document in `docs/`, with the draw.io source of the diagram. We now have two documents for these tasks, see section 4.
- Task 3: Modbus reading with pymodbus, in `gateway/hal/`.
- Task 4: REST API with FastAPI, in `gateway/api/rest.py`.
- Task 5: MQTT publishing with paho-mqtt, in `gateway/mqtt/publisher.py`.

I also added a small inverter simulator (`simulator/`), unit tests (`tests/`) and a README.

Repository: <https://gitlab.lrz.de/00000000014C491E/mini-energy-gateway>

## 2. How it works

Every 5 seconds the gateway reads the DC voltage (register `0x0010`) and the AC power (register `0x0020`) over Modbus TCP and keeps the latest reading in memory. `GET /api/measurements` returns that reading as JSON, and the same JSON goes to the MQTT topic `solar/inverter01/readings` every 5 seconds.

I added a `status` field to the JSON because I wanted to see when the data is old. It is `ok` normally, `error` when the last read failed and `stale` when nothing could be read for 15 seconds. Before the first reading the REST API returns 503.

To try it: start `python simulator/inverter_sim.py`, then `python -m gateway`, then open <http://localhost:8000/api/measurements>. You need Mosquitto running for the MQTT part.

## 3. What I tested

- `pytest` runs 16 unit tests, all pass.
- With my simulator: 503 before the first reading, afterwards live values on REST and MQTT.
- REST answers in under 30 ms on my laptop.
- MQTT messages arrive every 5 seconds (I measured 5.01 s and 4.99 s).
- When I stop the simulator the status goes to `error` and then `stale`. After a restart it is back to `ok` within a second.
- With Mosquitto 2.1.2 as broker and `mosquitto_sub` as subscriber.
- With diagslave 3.5 instead of my simulator: I wrote values into the registers and got exactly the same values back on REST and MQTT.
- With an API key set: 401 without the key, 200 with it.

What I did not test: ModRSsim2, Python 3.11 (I only have 3.12), and anything other than Windows.

## 4. How it fits the team document

I compared the code with `Mini_Energy_Gateway_Tasks_1_2.docx`. As far as I can see it covers all requirements in there:

| Requirement | How the code does it |
|---|---|
| FR-01 read `0x0010` and `0x0020` | `gateway/hal/modbus_reader.py` |
| FR-02 JSON at `GET /api/measurements` | `gateway/api/rest.py` |
| FR-03 publish every 5 s to `solar/inverter01/readings` | `gateway/mqtt/publisher.py` |
| NFR-01 reconnect within 10 s | it retries on every poll, so after 5 s at the latest |
| NFR-02 answer within 200 ms | served from memory, under 30 ms |
| NFR-03 README | `README.md` and `docs/USER_GUIDE.md` |
| NFR-04 API key | set `API_KEY`, clients send it in the `X-API-Key` header |

The components in the team document are also there, just with other names: the Modbus reader is `modbus_reader.py`, the processing filter is the decoding in `register_map.py` plus the timestamp in `poller.py`, the cache is `store.py`, and REST and MQTT are the two files above.

My own document calls the architecture layered instead of Pipes & Filters. I don't think that is a conflict. The layers describe where a component sits, the pipeline describes how the data moves.

## 5. Things we should decide

1. Which Tasks 1 and 2 document we hand in. We can keep the team document and take parts from mine, for example the diagram.
2. Which code we use for Tasks 3 to 5. Henri has a solution as well, so we should look at both.
3. Where the repository lives. It is in my personal namespace right now. I can move it into the team group.
4. If the API key should be mandatory. At the moment the API is open when `API_KEY` is not set, because that makes testing easier.
5. The register format. The exercise does not say it, so I assumed a 32 bit float in two holding registers. If it is a 16 bit integer we only have to change one line in `register_map.py`.
6. Who tests ModRSsim2 and Python 3.11.

If something is unclear or does not run on your machine, write me in the group chat.
