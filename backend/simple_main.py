from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="AskTrabaajo API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AskTrabaajo API is running! 🚀", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "asktrabaajo-api"}

@app.post("/api/auth/register")
async def register():
    return {"message": "Registration endpoint - coming soon!"}

@app.post("/api/auth/login")
async def login():
    return {"message": "Login endpoint - coming soon!"}

@app.get("/api/auth/me")
async def get_user():
    return {"message": "User endpoint - coming soon!"}

if __name__ == "__main__":
    uvicorn.run("simple_main:app", host="0.0.0.0", port=8000, reload=True) 