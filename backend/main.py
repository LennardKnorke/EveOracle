# backend/main.py
from config import *
import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app.api:app", 
        host=BACKEND_URL, 
        port=int(BACKEND_PORT), 
        reload=True
    )