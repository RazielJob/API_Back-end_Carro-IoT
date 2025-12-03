import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
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
    """Devuelve los últimos `n` eventos del dispositivo (con texto legible para operación/obstáculo/velocidad).
    """
    eventos = crud.get_last_n_events_data(id_dispositivo, n)
    if not eventos:
        return []
    results = []
    for ev in eventos:
        results.append({
            "id_evento": ev.get("id_evento"),
            "id_dispositivo": ev.get("id_dispositivo"),
            "id_cliente": ev.get("id_cliente"),
            "id_operacion": ev.get("id_operacion"),
            "operacion_texto": ev.get("operacion_texto"),
            "id_obstaculo": ev.get("id_obstaculo"),
            "obstaculo_texto": ev.get("obstaculo_texto"),
            "id_velocidad": ev.get("id_velocidad"),
            "velocidad_texto": ev.get("velocidad_texto"),
            "fecha_hora": ev.get("fecha_hora").isoformat() if ev.get("fecha_hora") else None
        })
    return results


@app.get("/health")
async def health():
    """Simple health check to test reachability from frontend/tools."""
    return {"ok": True}

@app.get("/api/last/{id_dispositivo}")
async def last_event(id_dispositivo: int):
    ev = crud.get_last_event_data(id_dispositivo)
    if not ev:
        return {}
    return {
        "id_evento": ev.get("id_evento"),
        "id_dispositivo": ev.get("id_dispositivo"),
        "id_cliente": ev.get("id_cliente"),
        "id_operacion": ev.get("id_operacion"),
        "operacion_texto": ev.get("operacion_texto"),
        "id_obstaculo": ev.get("id_obstaculo"),
        "obstaculo_texto": ev.get("obstaculo_texto"),
        "id_velocidad": ev.get("id_velocidad"),
        "velocidad_texto": ev.get("velocidad_texto"),
        "fecha_hora": ev.get("fecha_hora").isoformat() if ev.get("fecha_hora") else None
    }
    
@app.post("/api/speed")
async def control_velocidad(comando: dict):
    """Registra un cambio de velocidad en la BD y emite broadcast. Espera: {id_dispositivo, id_cliente, id_velocidad}
    """
    try:
        required_fields = ["id_dispositivo", "id_cliente", "id_velocidad"]
        for f in required_fields:
            if f not in comando:
                raise HTTPException(status_code=400, detail=f"Campo requerido: {f}")

        id_dispositivo = int(comando["id_dispositivo"]) 
        id_cliente = int(comando["id_cliente"]) 
        id_velocidad = int(comando["id_velocidad"]) 

        # basic validation
        if id_velocidad <= 0:
            raise HTTPException(status_code=400, detail="id_velocidad inválido")

        ev = crud.register_velocity(id_dispositivo, id_cliente, id_velocidad)
        if not ev:
            raise HTTPException(status_code=500, detail="No se pudo registrar la velocidad")

        payload = {
            "tipo": "velocidad",
            "evento": {
                "id_evento": ev.get("id_evento"),
                "id_dispositivo": ev.get("id_dispositivo"),
                "id_cliente": ev.get("id_cliente"),
                "id_velocidad": ev.get("id_velocidad"),
                "velocidad_texto": ev.get("velocidad_texto"),
                "fecha_hora": ev.get("fecha_hora").isoformat() if ev.get("fecha_hora") else None
            }
        }
        await manager.broadcast(payload)
        return payload["evento"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sequence")
async def create_sequence(comando: dict):
    """Registra y ejecuta una secuencia de movimientos. 
    Espera: {nombre, movimientos: [op_ids], id_dispositivo, id_cliente}
    Devuelve: {ok, id_secuencia, mensaje}
    """
    try:
        required_fields = ["nombre", "movimientos", "id_dispositivo", "id_cliente"]
        for f in required_fields:
            if f not in comando:
                raise HTTPException(status_code=400, detail=f"Campo requerido: {f}")

        nombre = str(comando["nombre"])
        movimientos = comando["movimientos"]
        if not isinstance(movimientos, list) or len(movimientos) == 0:
            raise HTTPException(status_code=400, detail="movimientos debe ser una lista no vacía")

        id_dispositivo = int(comando["id_dispositivo"])
        id_cliente = int(comando["id_cliente"])

        # Guardar secuencia en BD
        import json
        movimientos_json = json.dumps(movimientos)
        id_secuencia = crud.save_sequence(nombre, movimientos_json, id_cliente)

        # ✅ CAMBIO CRÍTICO: Enviar UNA SOLA VEZ toda la secuencia al carrito
        payload = {
            "tipo": "secuencia",
            "id_dispositivo": id_dispositivo,
            "id_cliente": id_cliente,
            "id_secuencia": id_secuencia,
            "nombre": nombre,
            "movimientos": movimientos  # ✅ Array completo
        }
        await manager.broadcast(payload)

        # Opcional: También registrar los eventos en la BD (sin enviar broadcasts individuales)
        eventos = crud.execute_sequence(movimientos, id_dispositivo, id_cliente)

        return {
            "ok": True,
            "id_secuencia": id_secuencia,
            "total_movimientos": len(movimientos),
            "mensaje": f"Secuencia '{nombre}' (ID {id_secuencia}) enviada al carrito con {len(movimientos)} movimientos"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
