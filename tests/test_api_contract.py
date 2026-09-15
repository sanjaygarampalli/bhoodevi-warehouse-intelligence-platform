from fastapi import FastAPI

from app.main import app


CRITICAL_OPERATIONS = {
    "/": {"GET"},
    "/health": {"GET"},
    "/ready": {"GET"},
    "/auth/register": {"POST"},
    "/auth/login": {"POST"},
    "/companies/": {"GET", "POST"},
    "/companies/{company_id}/intelligence": {"GET"},
    "/companies/{company_id}/intelligence-profile": {"GET", "POST", "PATCH"},
    "/decision-makers/": {"POST"},
    "/market-signals": {"GET", "POST"},
    "/warehouses/": {"GET", "POST"},
    "/warehouse-matches/": {"GET", "POST"},
    "/leads/": {"POST"},
    "/deals/": {"GET", "POST"},
    "/follow-up-tasks/": {"GET", "POST"},
    "/commercial-intelligence/outcomes/summary": {"GET"},
    "/action-intelligence/summary": {"GET"},
}


def test_critical_api_operations_remain_in_openapi_contract():
    assert isinstance(app, FastAPI)
    paths = app.openapi()["paths"]

    for path, methods in CRITICAL_OPERATIONS.items():
        assert path in paths, f"Critical API path disappeared: {path}"
        available_methods = {method.upper() for method in paths[path]}
        assert methods <= available_methods, (
            f"Critical API methods disappeared for {path}: "
            f"{sorted(methods - available_methods)}"
        )