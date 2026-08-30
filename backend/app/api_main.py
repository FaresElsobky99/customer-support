from fastapi import FastAPI

from backend.app.api.routes import auth, customers, tickets


app = FastAPI(
    title="Customer Support API",
)

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(tickets.router)


@app.get("/health")
def health():
    return {"status": "ok"}