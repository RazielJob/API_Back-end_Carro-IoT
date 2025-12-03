from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .models import Base, Events, Dispositivos, ClientesIoT, Operations, Obstaculos, Velocidades
from .config import settings
from datetime import datetime

DB_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# (opcional) crear tablas si no existen
# Base.metadata.create_all(bind=engine)

def add_movement(id_dispositivo:int, id_cliente:int, id_operacion:int, id_obstaculo:int|None=None):
    session = SessionLocal()
    try:
        evento = Events(
            id_dispositivo=id_dispositivo,
            id_cliente=id_cliente,
            id_operacion=id_operacion,
            id_obstaculo=id_obstaculo,
            fecha_hora=datetime.utcnow()
        )
        session.add(evento)
        session.commit()
        session.refresh(evento)
        return evento
    except SQLAlchemyError as e:
        session.rollback()
        raise
    finally:
        session.close()

def get_last_event(id_dispositivo:int):
    session = SessionLocal()
    try:
        return session.query(Events).filter(Events.id_dispositivo == id_dispositivo).order_by(Events.fecha_hora.desc()).first()
    finally:
        session.close()

def get_last_n_events(id_dispositivo:int, n:int=10):
    session = SessionLocal()
    try:
        return session.query(Events).filter(Events.id_dispositivo == id_dispositivo).order_by(Events.fecha_hora.desc()).limit(n).all()
    finally:
        session.close()


def get_last_event_data(id_dispositivo:int):
    session = SessionLocal()
    try:
        row = session.query(Events, Operations, Obstaculos, Velocidades).outerjoin(Obstaculos, Events.id_obstaculo == Obstaculos.id_obstaculo).outerjoin(Velocidades, Events.__table__.c.get('id_velocidad') == Velocidades.id_velocidad).join(Operations, Events.id_operacion == Operations.id_operation).filter(Events.id_dispositivo == id_dispositivo).order_by(Events.fecha_hora.desc()).first()
        if not row:
            return None
        evento, operacion, obstaculo, velocidad = row
        return {
            "id_evento": evento.id_evento,
            "id_dispositivo": evento.id_dispositivo,
            "id_cliente": evento.id_cliente,
            "id_operacion": evento.id_operacion,
            "operacion_texto": operacion.status_texto if operacion else None,
            "id_obstaculo": evento.id_obstaculo,
            "obstaculo_texto": obstaculo.status_texto if obstaculo else None,
            "id_velocidad": velocidad.id_velocidad if velocidad else None,
            "velocidad_texto": velocidad.descripcion if velocidad else None,
            "fecha_hora": evento.fecha_hora
        }
    finally:
        session.close()


def get_last_n_events_data(id_dispositivo:int, n:int=10):
    session = SessionLocal()
    try:
        rows = session.query(Events, Operations, Obstaculos, Velocidades).outerjoin(Obstaculos, Events.id_obstaculo == Obstaculos.id_obstaculo).outerjoin(Velocidades, Events.__table__.c.get('id_velocidad') == Velocidades.id_velocidad).join(Operations, Events.id_operacion == Operations.id_operation).filter(Events.id_dispositivo == id_dispositivo).order_by(Events.fecha_hora.desc()).limit(n).all()
        results = []
        for row in rows:
            evento, operacion, obstaculo, velocidad = row
            results.append({
                "id_evento": evento.id_evento,
                "id_dispositivo": evento.id_dispositivo,
                "id_cliente": evento.id_cliente,
                "id_operacion": evento.id_operacion,
                "operacion_texto": operacion.status_texto if operacion else None,
                "id_obstaculo": evento.id_obstaculo,
                "obstaculo_texto": obstaculo.status_texto if obstaculo else None,
                "id_velocidad": velocidad.id_velocidad if velocidad else None,
                "velocidad_texto": velocidad.descripcion if velocidad else None,
                "fecha_hora": evento.fecha_hora
            })
        return results
    finally:
        session.close()


def register_velocity(id_dispositivo:int, id_cliente:int, id_velocidad:int):
    """Insert an event recording a speed change. Uses direct SQL INSERT so we don't need to modify ORM models.
    Returns the inserted event as dict via get_last_event_data.
    """
    session = SessionLocal()
    try:
        # use operation 1 (Adelante) as base per stored-procedure convention
        session.execute(text("INSERT INTO Events (id_dispositivo, id_cliente, id_operacion, id_velocidad, fecha_hora) VALUES (:d, :c, :op, :v, NOW())"), {"d": id_dispositivo, "c": id_cliente, "op": 1, "v": id_velocidad})
        session.commit()
        # return the most recent event for that device
        return get_last_event_data(id_dispositivo)
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def save_sequence(nombre: str, movimientos_json: str, id_cliente: int = 1):
    """Save a sequence to SecuenciasDemo table.
    Returns the sequence ID (id_secuencia).
    """
    session = SessionLocal()
    try:
        session.execute(text(
            "INSERT INTO SecuenciasDemo (nombre_secuencia, movimientos, activa) VALUES (:n, :m, 1)"
        ), {"n": nombre, "m": movimientos_json})
        session.commit()
        # get the last inserted id
        result = session.execute(text("SELECT LAST_INSERT_ID() as id")).fetchone()
        return result[0] if result else None
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def execute_sequence(movimientos: list, id_dispositivo: int, id_cliente: int):
    """Execute a sequence: insert an event for each operation in movimientos.
    Returns list of inserted event dicts.
    """
    eventos = []
    try:
        for id_operacion in movimientos:
            evento = add_movement(id_dispositivo, id_cliente, id_operacion, None)
            eventos.append({
                "id_evento": evento.id_evento,
                "id_operacion": evento.id_operacion,
                "id_dispositivo": evento.id_dispositivo,
                "fecha_hora": evento.fecha_hora.isoformat() if evento.fecha_hora else None
            })
        return eventos
    except SQLAlchemyError:
        raise
