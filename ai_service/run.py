"""
run.py

This file is a simple entry point to run the FastAPI application
using Uvicorn.

It allows developers to start the server using:
    python run.py

No business logic should be written here.
"""

import uvicorn


if __name__ == "__main__":
    # Start the FastAPI application
    # host="0.0.0.0" allows access from other devices if needed
    # reload=True enables auto-reload during development
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
