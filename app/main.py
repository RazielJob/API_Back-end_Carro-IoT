import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .websocket_manager import manager
from . import crud, schemas

app = FastAPI(title="IoT Carrito API")

# CORS - permitir cualquier origen (acepta peticiones desde cualquier IP pública)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # en producción restringir esto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints REST (Controlador) ---
# NOTE: API key verification removed for demo/testing. Endpoints are open (CORS still allows origins).

@app.post("/api/move", response_model=schemas.MovementOut)
async def post_move(mv: schemas.MovementIn):
    evento = crud.add_movement(mv.id_dispositivo, mv.id_cliente, mv.id_operacion, mv.id_obstaculo)
    # preparar payload para broadcast
    payload = {
        "tipo": "movimiento",
        "evento": {
            "id_evento": evento.id_evento,
            "id_dispositivo": evento.id_dispositivo,
            "id_cliente": evento.id_cliente,
            "id_operacion": evento.id_operacion,
            "id_obstaculo": evento.id_obstaculo,
            "fecha_hora": evento.fecha_hora.isoformat()
        }
    }
    # push
    await manager.broadcast(payload)
    return payload["evento"]

@app.post("/api/obstaculo", response_model=dict)
async def post_obstaculo(data: dict):
    # Espera: id_dispositivo, id_cliente, id_obstaculo
    evento = crud.add_movement(data["id_dispositivo"], data["id_cliente"], 3, data.get("id_obstaculo"))  # 3 = Detener
    payload = {"tipo": "obstaculo", "evento": {
        "id_evento": evento.id_evento,
        "id_operacion": evento.id_operacion,
        "id_obstaculo": evento.id_obstaculo,
        "fecha_hora": evento.fecha_hora.isoformat()
    }}
    await manager.broadcast(payload)
    return {"ok": True}


@app.get("/api/events/{id_dispositivo}")
async def get_events(id_dispositivo: int, n: int = 10):
    """Devuelve los últimos `n` eventos del dispositivo (orden descendente por fecha).
    Usado por el frontend para mostrar historial/monitoring.
    """
    eventos = crud.get_last_n_events(id_dispositivo, n)
    if not eventos:
        return []
    results = []
    for evento in eventos:
        results.append({
            "id_evento": evento.id_evento,
            "id_dispositivo": evento.id_dispositivo,
            "id_cliente": evento.id_cliente,
            "id_operacion": evento.id_operacion,
            "id_obstaculo": evento.id_obstaculo,
            "fecha_hora": evento.fecha_hora.isoformat()
        })
    return results


@app.get("/health")
async def health():
    """Simple health check to test reachability from frontend/tools."""
    return {"ok": True}

@app.get("/api/last/{id_dispositivo}")
async def last_event(id_dispositivo: int):
    evento = crud.get_last_event(id_dispositivo)
    if not evento:
        return {}
    return {
        "id_evento": evento.id_evento,
        "id_dispositivo": evento.id_dispositivo,
        "id_cliente": evento.id_cliente,
        "id_operacion": evento.id_operacion,
        "id_obstaculo": evento.id_obstaculo,
        "fecha_hora": evento.fecha_hora.isoformat()
    }

# --- WebSocket endpoint ---
@app.websocket("/ws/monitor")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # el cliente puede enviar ping u otros mensajes; aquí sólo escuchamos
            msg = await websocket.receive_text()
            # opcional: responder pong
            await websocket.send_json({"tipo": "ack", "msg": f"recibido: {msg}"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=False)
