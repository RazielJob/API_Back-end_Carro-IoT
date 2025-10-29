from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .models import Base, Events, Dispositivos, ClientesIoT, Operations, Obstaculos
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
