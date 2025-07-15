from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from pydantic import BaseModel
from typing import List, Optional
import json
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather

app = FastAPI()

# Twilio podaci - zamijeni s tvojim!
TWILIO_ACCOUNT_SID = "TVOJ_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "TVOJ_AUTH_TOKEN"
TWILIO_PHONE_NUMBER = "+1234567890"

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

DATA_FILE = "data.json"

class Firefighter(BaseModel):
    id: int
    name: str
    phone: str
    status: Optional[str] = "nije odgovorio"

class Group(BaseModel):
    id: int
    name: str
    firefighters: List[Firefighter]

def load_data() -> List[Group]:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            groups = json.load(f)
            return [Group(**g) for g in groups]
    except FileNotFoundError:
        return []

def save_data(groups: List[Group]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([g.dict() for g in groups], f, indent=4, ensure_ascii=False)

@app.get("/groups", response_model=List[Group])
def get_groups():
    return load_data()

@app.post("/groups", response_model=Group)
def create_group(group: Group):
    groups = load_data()
    if any(g.id == group.id for g in groups):
        raise HTTPException(status_code=400, detail="Grupa s tim ID već postoji")
    groups.append(group)
    save_data(groups)
    return group

@app.post("/call-group/{group_id}")
def call_group(group_id: int, background_tasks: BackgroundTasks):
    groups = load_data()
    group = next((g for g in groups if g.id == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail="Grupa nije pronađena")

    for ff in group.firefighters:
        background_tasks.add_task(call_firefighter, ff.phone, ff.id, group.id)
    return {"message": f"Pozivi su pokrenuti za grupu {group.name}"}

def call_firefighter(phone: str, firefighter_id: int, group_id: int):
    # Zamijeni ovaj URL sa stvarnim URL-om tvoje deployane aplikacije na Renderu
    app_url = "https://vatrogasni-dispecer-backend.onrender.com"  
    twilio_client.calls.create(
        to=phone,
        from_=TWILIO_PHONE_NUMBER,
        url=f"{app_url}/voice?firefighter_id={firefighter_id}&group_id={group_id}"
    )

@app.post("/voice")
async def voice_webhook(request: Request):
    params = request.query_params
    firefighter_id = int(params.get("firefighter_id"))
    group_id = int(params.get("group_id"))

    response = VoiceResponse()
    gather = Gather(num_digits=1, action=f"/dtmf?firefighter_id={firefighter_id}&group_id={group_id}", method="POST")
    gather.say("Pozdrav, ovo je vatrogasni dispečer. Pritisnite 1 ako dolazite, ili 9 ako ne dolazite.")
    response.append(gather)
    response.say("Nismo primili vaš odgovor. Doviđenja.")
    return Response(content=str(response), media_type="application/xml")

@app.post("/dtmf")
async def dtmf_response(request: Request):
    form = await request.form()
    params = request.query_params
    firefighter_id = int(params.get("firefighter_id"))
    group_id = int(params.get("group_id"))
    digit = form.get("Digits")

    groups = load_data()
    group = next((g for g in groups if g.id == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail="Grupa nije pronađena")

    firefighter = next((f for f in group.firefighters if f.id == firefighter_id), None)
    if not firefighter:
        raise HTTPException(status_code=404, detail="Vatrogasac nije pronađen")

    if digit == "1":
        firefighter.status = "dolazi"
    elif digit == "9":
        firefighter.status = "ne dolazi"
    else:
        firefighter.status = "nije odgovorio"

    save_data(groups)
    return Response(content="<Response></Response>", media_type="application/xml")

@app.post("/send-sms/{group_id}")
def send_sms(group_id: int, message: str):
    groups = load_data()
    group = next((g for g in groups if g.id == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail="Grupa nije pronađena")

    for ff in group.firefighters:
        twilio_client.messages.create(
            to=ff.phone,
            from_=TWILIO_PHONE_NUMBER,
            body=message
        )
    return {"message": f"SMS poslan svim vatrogascima iz {group.name}"}
