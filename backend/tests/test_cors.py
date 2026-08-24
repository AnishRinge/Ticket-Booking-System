from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_preflight_vercel_origin_v1():
    response = client.options(
        "/api/v1/auth/register",
        headers={
            "Origin": "https://ticketflow-rust-kappa.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://ticketflow-rust-kappa.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_preflight_vercel_preview_domain():
    response = client.options(
        "/api/v1/auth/register",
        headers={
            "Origin": "https://ticketflow-preview-xyz.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://ticketflow-preview-xyz.vercel.app"

def test_cors_preflight_localhost_origin():
    response = client.options(
        "/api/v1/auth/register",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

def test_cors_preflight_localhost_5173_origin():
    response = client.options(
        "/api/v1/events",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

def test_cors_actual_request_headers():
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "https://ticketflow-rust-kappa.vercel.app"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://ticketflow-rust-kappa.vercel.app"
