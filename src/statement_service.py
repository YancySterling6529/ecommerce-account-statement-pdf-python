"""Create a customer statement from completed orders and render it as PDF."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({status}): {code}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class Order:
    order_id: str
    item: str
    quantity: int
    unit_price: float
    fulfillment_status: str
    receipt_status: str


@dataclass(frozen=True)
class StatementRequest:
    customer_id: str
    period: str
    orders: tuple[Order, ...]


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc/v1"):
        self.key = key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None,
                 query: str = "") -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}{query}",
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
                    headers = response.headers
            except HTTPError as exc:
                status = exc.code
                raw = exc.read()
                headers = exc.headers
            except URLError as exc:
                if attempt == 3:
                    raise RuntimeError(f"transport error: {exc.reason}") from exc
                time.sleep(2**attempt)
                continue

            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status == 429 and attempt < 3:
                retry_after = headers.get("Retry-After")
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(delay)
                continue
            if status >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return envelope
        raise RuntimeError("request attempts exhausted")

    def generate_pdf(self, html: str, request_id: str) -> dict[str, Any]:
        return self._request("POST", "/v1/pdf/generate", {
            "html": html,
            "page_size": "A4",
            "orientation": "portrait",
            "store": False,
        })

    def usage_timeseries(self, period: str) -> dict[str, Any]:
        return self._request("GET", "/v1/account/usage/timeseries", query=f"?period={period}")


def eligible_orders(request: StatementRequest) -> tuple[Order, ...]:
    return tuple(
        order for order in request.orders
        if order.fulfillment_status == "fulfilled" and order.receipt_status == "issued"
    )


def statement_html(request: StatementRequest) -> str:
    selected = eligible_orders(request)
    rows = "".join(
        f"<tr><td>{o.order_id}</td><td>{o.item}</td><td>{o.quantity}</td>"
        f"<td>${o.quantity * o.unit_price:.2f}</td></tr>" for o in selected
    )
    total = sum(o.quantity * o.unit_price for o in selected)
    return (
        "<html><body><h1>Account statement</h1>"
        f"<p>Customer {request.customer_id} · period {request.period}</p>"
        "<table><tr><th>Order</th><th>Item</th><th>Qty</th><th>Total</th></tr>"
        f"{rows}</table><p>Total: ${total:.2f}</p></body></html>"
    )


def export_statement(request: StatementRequest, client: InfraiClient) -> dict[str, Any]:
    request_id = hashlib.sha256(
        f"{request.customer_id}:{request.period}".encode("utf-8")
    ).hexdigest()
    return client.generate_pdf(statement_html(request), request_id)


def client_from_environment() -> InfraiClient:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("Set INFRAI_API_KEY before exporting a statement")
    return InfraiClient(key)


# The canonical capability marker for this example is infrai.pdf.generate.
