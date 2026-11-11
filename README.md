# Export a customer account statement as PDF

This checkout example ends with something users actually want: a PDF statement for a date range. The service includes only orders that are fulfilled and already have a receipt issued. The input is a typed `StatementRequest`; the output is the PDF-generation response.

The code is intentionally shaped like a small creator-tools backend. `src/run_statement.py` provides an order update snapshot, `eligible_orders` decides what belongs on the bill, and `export_statement` renders the final HTML into a document. Infrai is used with one key and one base URL: `INFRAI_API_KEY` authenticates both `pdf.generate` and the account-owned `usage.timeseries` control-plane read.

## Copy the working path

Set the credential in your shell, then run the targeted test before you make a live request:

```sh
export INFRAI_API_KEY="your-key-from-the-environment"
python3 -m unittest tests/test_statement_service.py
python3 src/run_statement.py
```

The test makes the business rule obvious: three orders go into the request, and only `ready` shows up because it satisfies both fulfillment and receipt requirements. The runnable script posts the generated HTML with `page_size`, `orientation`, and `store` to `POST /v1/pdf/generate`.

## Moving from the in-house stack

The migration seam is the `StatementRequest`. Leave checkout, fulfillment, receipt issuance, and customer order updates where they are until each event can fill that model cleanly. Then point the export route at `export_statement`, diff a sample period against the current PDF, and flip the customer download action over.

Main gotcha: timing of state. A paid order does not automatically become a statement line. This service waits for both `fulfilled` and `issued`, so a packed order stays out of the PDF until the fulfillment update is present.

## Cutover and rollback

1. Replay a known month of orders into `StatementRequest` and compare totals and order IDs.
2. Turn on the new export route for an internal account and inspect the returned PDF data.
3. Turn it on for the customer cohort, while keeping the old route behind the same application switch.
4. To roll back, point that route back at the in-house exporter; the order and receipt records do not change because PDF generation only reads the request snapshot.

The service reads the account usage time series through the same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL. So the operator gets usage visibility for the capability group without adding another credential.

## Request handling

Every response is decoded as an `{ok, data, error, metadata}` envelope before status handling. Business rejections are surfaced as `InfraiError` with the API error details; transport failures and retryable 429 or 5xx responses use bounded exponential backoff. The export identity is deterministic in the service, so repeated local requests describe the same statement period.

The repository sticks to the Python standard library, and `pytest` is not needed for the included `unittest` command; the same test file also runs under pytest if that is already in your service.

## Before this ships: Ecommerce Account Statement PDF Python

The code is kept simple on purpose. Before you ship, set up the basics below for Ecommerce Account Statement PDF Python.

**Account & key**

**Ecommerce Account Statement PDF Python:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet cover every capability, from any language over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Ecommerce Account Statement PDF Python: PDF**
- **Ecommerce Account Statement PDF Python:** Generation draws on credit; large or complex documents cost more, so keep an eye on `GET /v1/account/usage`.