from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Vatrogasni dispečer backend radi."}

@app.post("/dtmf-response")
async def dtmf_response(request: Request):
    data = await request.form()
    digit = data.get("Digits")
    from_number = data.get("From")
    return {"received": digit, "from": from_number}
