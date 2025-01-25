import json
import logging
from time import sleep
from ulid import ULID
from pathlib import Path
# import os

import httpx
from logfmter import Logfmter

# from registry import registry
from flask import Flask, request
from pydantic import BaseSettings
from cloudevents.http import CloudEvent, from_http
# from cloudevents.http.conversion import from_http
from cloudevents.conversion import to_structured#, from_http
from cloudevents.exceptions import InvalidStructuredJSON

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger(__name__)
L.setLevel(logging.INFO)

class Settings(BaseSettings):
    host: str = '0.0.0.0'
    port: int = 8787
    debug: bool = False
    knative_broker: str = (
        "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default"
    )
    dry_run: bool = False

    class Config:
        env_prefix = "VERIFIER_"
        case_sensitive = False


app = Flask(__name__)
config = Settings()

# L.info("knative-broker", extra={"broker": config.knative_broker})
def route_message(data: dict):

    msg_type_sensor_handle = "uasdaq.sensor.handle.request"
    msg_type_event_handle = "uasdaq.event.handle.request"
    msg_type_manage_handle = "uasdaq.manage.handle.request"
    msg_source = "uasdaq.verifier"

    parts = data["source-path"].split("/")
    acct = parts[0]
    sampling_system_id = parts[1]
    data_format = parts[2]
    message_type = parts[3]

    payload = data["payload"]
    
    if message_type == "sensor":

        attributes = {
                "type": msg_type_sensor_handle,
                "source": msg_source,
                "id": str(ULID()),
                "datacontenttype": "application/json; charset=utf-8",
            }
        
        ce = CloudEvent(attributes=attributes, data=data)
    elif message_type == "event":
        L.info("handle event", extra={"payload": payload})
        return "handle event"

    elif message_type == "manage":
        L.info("handle event", extra={"payload": payload})
        attributes = {
            "type": msg_type_manage_handle,
            "source": msg_source,
            "id": str(ULID()),
            "datacontenttype": "application/json; charset=utf-8",
        }
        
        ce = CloudEvent(attributes=attributes, data=data)
    else:
        return "no content"

    try:
        headers, body = to_structured(ce)
        # send to knative kafkabroker
        with httpx.Client() as client:
            r = client.post(
                config.knative_broker, headers=headers, data=body
                # config.knative_broker, headers=headers, data=body.decode()
            )
            L.info("verifier send", extra={"verifier-request": r.request.content})
            r.raise_for_status()
    except InvalidStructuredJSON:
        L.error(f"INVALID MSG: {ce}")
    except httpx.HTTPError as e:
        L.error(f"HTTP Error when posting to {e.request.url!r}: {e}")

    return "message verified and handled"

@app.route("/", methods=["POST"])
def verify_message():
    L.info("verify message")
    L.info("verify request", extra={"verify-request": request.data})
    try:
        ce = from_http(headers=request.headers, data=request.get_data())
        # to support local testing...
        if isinstance(ce.data, str):
            ce.data = json.loads(ce.data)
    except InvalidStructuredJSON:
        L.error("not a valid cloudevent")
        return "not a valid cloudevent", 400

    parts = Path(ce["source"]).parts
    L.info(
        "verify message",
        extra={"ce-source": ce["source"], "ce-type": ce["type"], "ce-data": ce.data},
    )

    # # mock verification - TODO: need verification method
    # # for now, sleep for a second to simulate some action
    # sleep(0.01)

    # result = route_message(data)
    result = ""
    result = route_message(ce.data)
    return result
    # make = parts[2]
    # model = parts[3]
    # sn = parts[4]
    # registry_id = f"{make}_{model}"

    # # Send to a specific datasets based on the `type`
    # # CloudEvent field.
    # send_all_vars = False
    # erddap_dataset = f"{make}_{model}"

    # if "type" in ce and ce["type"].endswith(".qc"):
    #     erddap_dataset += "_QC"
    #     send_all_vars = True

    # url = f"{config.url}/{erddap_dataset}.insert"

    # params = {"make": make, "model": model, "serial_number": sn}

    # try:
    #     variables = registry[registry_id]["variables"].keys()
    # except KeyError:
    #     params["options"] = list(registry.keys())
    #     params["registry_id"] = registry_id
    #     L.error("Unknown sensor", extra=params)
    #     return f"Unknown sensor, not in {registry.keys()}", 400

    # data = ce.data["data"]

    # if send_all_vars is False:
    #     # Base this on defined metadata variables, which don't include QC vars
    #     for var in variables:
    #         try:
    #             values = data[var]
    #             if isinstance(values, list):
    #                 # changed to allow httpx to encode properly...I think it was being encoded twice
    #                 # params[var] = f"%5B{','.join([str(x) for x in values])}%5D"
    #                 params[var] = f"[{','.join([str(x) for x in values])}]"
    #             else:
    #                 params[var] = data[var]
    #         except KeyError:
    #             L.debug("Empty variable", extra=params)
    #             params[var] = "NaN"
    # else:
    #     # Base the data coming in the message
    #     params.update(data)

    # # had to move this to the end of the params - erddap requires is to be the last parameter
    # params["author"] = config.author
    # L.info(params)

    # if config.dry_run is False:
    #     try:
    #         r = httpx.post(url, params=params, verify=False)
    #         L.info(f"Sent POST to ERRDAP @ {r.url}", extra=params)
    #         r.raise_for_status()
    #         return r.json()
    #     except httpx.HTTPError as e:
    #         L.error(str(e))
    #         return str(e)
    # else:
    #     msg = L.info(f"[DRY_RUN] - Didn't send POST to ERRDAP @ {url}")
    #     L.info(msg, extra=params)
    #     return msg


if __name__ == "__main__":
    app.run(debug=config.debug, host=config.host, port=config.port)
    # app.run()
