from pydantic import BaseModel
from typing import Optional

class MovementIn(BaseModel):
    id_dispositivo: int
    id_cliente: int
    id_operacion: int
    id_obstaculo: Optional[int] = None

class MovementOut(BaseModel):
    id_evento: int
    id_dispositivo: int
    id_cliente: int
    id_operacion: int
    id_obstaculo: Optional[int]
    fecha_hora: str
