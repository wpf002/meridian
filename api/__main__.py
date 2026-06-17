"""Run the Meridian API: python -m api"""

import os

import uvicorn

if __name__ == "__main__":
    # Railway (and most PaaS) inject the port to bind via $PORT; fall back to
    # API_PORT / 8800 for local runs. API_HOST stays loopback locally and is set
    # to 0.0.0.0 in the container so the platform can route to it.
    port = int(os.getenv("PORT") or os.getenv("API_PORT") or "8800")
    uvicorn.run(
        "api.app:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=port,
        reload=bool(os.getenv("API_RELOAD")),
    )
