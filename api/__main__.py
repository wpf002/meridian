"""Run the Meridian API: python -m api"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8800")),
        reload=bool(os.getenv("API_RELOAD")),
    )
