from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, DECIMAL, JSON, Boolean, Table)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class Operations(Base):
    __tablename__ = "Operations"
    id_operation = Column(Integer, primary_key=True, autoincrement=True)
    status_texto = Column(String(50), nullable=False)

class Obstaculos(Base):
    __tablename__ = "Obstaculos"
    id_obstaculo = Column(Integer, primary_key=True, autoincrement=True)
    status_texto = Column(String(50), nullable=False)

class Dispositivos(Base):
    __tablename__ = "Dispositivos"
    id_dispositivo = Column(Integer, primary_key=True, autoincrement=True)
    nombre_dispositivo = Column(String(100), nullable=False)

class Velocidades(Base):
    __tablename__ = "Velocidades"
    id_velocidad = Column(Integer, primary_key=True, autoincrement=True)
    nivel_velocidad = Column(Integer, nullable=False)
    descripcion = Column(String(100), nullable=False)
    valor_pwm = Column(Integer, nullable=False)
    activo = Column(Boolean, default=True)

class ClientesIoT(Base):
    __tablename__ = "ClientesIoT"
    id_cliente = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(45), nullable=False)
    pais = Column(String(50), nullable=False)
    ciudad = Column(String(50), nullable=False)
    longitud = Column(DECIMAL(10,6), nullable=False)
    latitud = Column(DECIMAL(10,6), nullable=False)

class Events(Base):
    __tablename__ = "Events"
    id_evento = Column(Integer, primary_key=True, autoincrement=True)
    id_dispositivo = Column(Integer, ForeignKey("Dispositivos.id_dispositivo"), nullable=False)
    id_cliente = Column(Integer, ForeignKey("ClientesIoT.id_cliente"), nullable=False)
    id_operacion = Column(Integer, ForeignKey("Operations.id_operation"), nullable=False)
    id_velocidad = Column(Integer, ForeignKey("Velocidades.id_velocidad"), nullable=True)
    id_obstaculo = Column(Integer, ForeignKey("Obstaculos.id_obstaculo"), nullable=True)
    fecha_hora = Column(DateTime, server_default=func.now())

    dispositivo = relationship("Dispositivos")
    cliente = relationship("ClientesIoT")
    operacion = relationship("Operations")
    obstaculo = relationship("Obstaculos", lazy="joined")
    velocidad = relationship("Velocidades", lazy="joined")
