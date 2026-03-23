from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

class PlanoEnum(str, enum.Enum):
    gratuito = "gratuito"
    mensal   = "mensal"
    anual    = "anual"

class StatusAssinaturaEnum(str, enum.Enum):
    ativa    = "ativa"
    cancelada= "cancelada"
    expirada = "expirada"

# ── Usuários ─────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id              = Column(Integer, primary_key=True, index=True)
    nome            = Column(String(100), nullable=False)
    email           = Column(String(150), unique=True, index=True, nullable=False)
    senha_hash      = Column(String(200), nullable=False)
    plano           = Column(Enum(PlanoEnum), default=PlanoEnum.gratuito)
    ativo           = Column(Boolean, default=True)
    criado_em       = Column(DateTime, default=datetime.utcnow)

    assinatura      = relationship("Assinatura", back_populates="usuario", uselist=False)
    favoritos       = relationship("Favorito", back_populates="usuario")

# ── Assinaturas (Stripe) ──────────────────────────────────────
class Assinatura(Base):
    __tablename__ = "assinaturas"

    id                  = Column(Integer, primary_key=True, index=True)
    usuario_id          = Column(Integer, ForeignKey("usuarios.id"), unique=True)
    stripe_customer_id  = Column(String(100), unique=True)
    stripe_sub_id       = Column(String(100), unique=True)
    plano               = Column(Enum(PlanoEnum))
    status              = Column(Enum(StatusAssinaturaEnum), default=StatusAssinaturaEnum.ativa)
    valor               = Column(Integer)  # em centavos
    inicio              = Column(DateTime)
    vencimento          = Column(DateTime)
    criado_em           = Column(DateTime, default=datetime.utcnow)

    usuario             = relationship("Usuario", back_populates="assinatura")

# ── Receitas ──────────────────────────────────────────────────
class Receita(Base):
    __tablename__ = "receitas"

    id              = Column(Integer, primary_key=True, index=True)
    nome            = Column(String(200), nullable=False)
    categoria       = Column(String(50))       # Peixe, Carne, Frutos do Mar
    descricao       = Column(Text)
    tempo_preparo   = Column(String(50))
    dificuldade     = Column(String(20))       # Fácil, Média, Alta
    porcoes         = Column(String(30))
    foto_url        = Column(String(300))      # caminho da foto local ou URL
    ingredientes    = Column(JSON)             # lista de {item, quantidade}
    tecnica         = Column(JSON)             # lista de passos
    vinhos          = Column(JSON)             # lista de vinhos
    mise_en_place   = Column(JSON)             # lista de {item, sugestao}
    dica_chef       = Column(Text)
    premium         = Column(Boolean, default=True)  # só para assinantes?
    criado_em       = Column(DateTime, default=datetime.utcnow)

    favoritos       = relationship("Favorito", back_populates="receita")

# ── Favoritos ─────────────────────────────────────────────────
class Favorito(Base):
    __tablename__ = "favoritos"

    id          = Column(Integer, primary_key=True, index=True)
    usuario_id  = Column(Integer, ForeignKey("usuarios.id"))
    receita_id  = Column(Integer, ForeignKey("receitas.id"))
    salvo_em    = Column(DateTime, default=datetime.utcnow)

    usuario     = relationship("Usuario", back_populates="favoritos")
    receita     = relationship("Receita", back_populates="favoritos")
