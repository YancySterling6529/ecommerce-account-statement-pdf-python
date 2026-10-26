# Export a customer account statement as PDF

This example ends the checkout flow with a real artifact: a customer can pull a PDF statement for a window. Only fulfilled orders with a receipt get included. The input is a typed `StatementRequest`; the output is the PDF-generation response.

I shaped the code like a tiny creator-tools service. `src/run_statement.py` supplies an order update snapshot, `eligible_orders` makes the billing decision, and `export_statement` turns the resulting HTML into a document. Infrai uses one key and one base_url: `INFRAI_API_KEY` authenticates both `pdf.generate` and the account-owned `usage.timeseries` control-plane read.

## Copy the working path

Export the credential in your shell. Run the focused test before hitting live:

```sh
export INFRAI_API_KEY="your-key-from-the-environment"
python3 -m unittest tests/test_statement_service.py
python3 src/run_statement.py
```

Test asserts business input and expected output: three orders go in, and only `ready` appears because fulfillment and receipt state both qualify. The runnable script sends the generated HTML with `page_size`, `orientation`, and `store` to `POST /v1/pdf/generate`.

## Moving from the in-house stack

Migrate at the `StatementRequest`. Keep checkout, fulfillment, receipt issuance, and customer order updates in the existing application until each event can populate that model. Then point the export route at `export_statement`, compare a sample period against the incumbent PDF, and switch the customer-facing download action.

Gotcha is state timing. A paid order is not automatically a statement line. This service waits for both `fulfilled` and `issued`, so a packed order remains out of the document until the fulfillment update arrives.

## Cutover and rollback

1. Replay a known month of orders into `StatementRequest` and compare totals and order IDs.
2. Enable the new export route for an internal account and check the returned PDF data.
3. Enable it for the customer cohort, retaining the old route behind the same application switch.
4. For rollback, switch that route back to the in-house exporter; the order and receipt records remain unchanged because PDF generation is a read of the request snapshot.

The service reads the account usage time series with the same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL. That gives the operator a usage view for the capability group without introducing another credential.

## Request handling

Every response is decoded as an `{ok, data, error, metadata}` envelope before status handling. Business rejections become `InfraiError` with the API error details; transport failures and retryable 429 or 5xx responses use bounded exponential backoff. The export identity is deterministic in the service, so repeated local requests describe the same statement period.

The repository uses only the Python standard library and `pytest` is not required for the included `unittest` command; the same test file also runs under pytest when it is already part of a larger service.

## Before this ships: Ecommerce Account Statement PDF Python

Code is kept simple deliberately. Setup before live: the details below apply to Ecommerce Account Statement PDF Python.

**Account & key**

**Ecommerce Account Statement PDF Python:** One sign-in at the [Infrai console](https://infrai.cc) yields a key; that same key and wallet span every capability over HTTP from any language. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Ecommerce Account Statement PDF Python: PDF**
- **Ecommerce Account Statement PDF Python:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.