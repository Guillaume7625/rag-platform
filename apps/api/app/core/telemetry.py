from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


def setup_telemetry(app: FastAPI) -> None:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
