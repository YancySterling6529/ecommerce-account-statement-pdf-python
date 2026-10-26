from statement_service import Order, StatementRequest, client_from_environment, export_statement


def main() -> None:
    request = StatementRequest(
        customer_id="creator-204",
        period="2026-10",
        orders=(
            Order("ord-104", "Camera strap", 1, 24.0, "fulfilled", "issued"),
            Order("ord-105", "Editing presets", 2, 12.5, "fulfilled", "issued"),
            Order("ord-106", "Studio print", 1, 30.0, "packed", "issued"),
        ),
    )
    result = export_statement(request, client_from_environment())
    print(result["data"])


if __name__ == "__main__":
    main()
