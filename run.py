import uvicorn

if __name__ == "__main__":
    # 0.0.0.0 so the phone on the same Wi-Fi can reach the dashboard, the
    # WhatsApp ingest endpoint and the links inside notifications. The
    # dashboard password in .env is what keeps that safe.
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
