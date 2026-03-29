from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
import shutil, os, uuid, stripe, json, re, sqlite3, urllib.request, urllib.parse
from dotenv import load_dotenv

from database import engine, get_db, Base
import models, auth

load_dotenv()

# ── Claude AI ────────────────────────────────────────────────
try:
    import anthropic as _anthropic
    _ai_client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
except ImportError:
    _ai_client = None
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ── Criar tabelas no banco ────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Rate limiter (proteção contra força bruta) ────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="Chef IA Premium",
    version="1.0",
    docs_url=None,       # Desativa /docs em produção
    redoc_url=None,      # Desativa /redoc em produção
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
)

# ── Servir arquivos estáticos ─────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOTOS_DIR = os.path.join(BASE_DIR, "fotos")
os.makedirs(FOTOS_DIR, exist_ok=True)

app.mount("/fotos", StaticFiles(directory=FOTOS_DIR), name="fotos")
app.mount("/js",   StaticFiles(directory=os.path.join(BASE_DIR, "js")), name="js")

@app.get("/")
def index():
    return FileResponse(os.path.join(BASE_DIR, "encontro_premium.html"))

@app.get("/auth.html")
def auth_page():
    return FileResponse(os.path.join(BASE_DIR, "auth.html"))

@app.get("/login.html")
def login_page():
    return FileResponse(os.path.join(BASE_DIR, "auth.html"))

@app.get("/cadastro.html")
def cadastro_page():
    return FileResponse(os.path.join(BASE_DIR, "auth.html"))

# ════════════════════════════════════════════════════════════
# SCHEMAS (Pydantic)
# ════════════════════════════════════════════════════════════
class UsuarioCriar(BaseModel):
    nome: str
    email: EmailStr
    senha: str

class LoginInput(BaseModel):
    email: EmailStr
    senha: str

class ReceitaCriar(BaseModel):
    nome: str
    categoria: str
    descricao: str
    tempo_preparo: str
    dificuldade: str
    porcoes: str
    ingredientes: list
    tecnica: list
    vinhos: list
    mise_en_place: list
    dica_chef: str
    premium: bool = True

class AssinarInput(BaseModel):
    plano: str       # "mensal" ou "anual"
    token_stripe: str

# ════════════════════════════════════════════════════════════
# AUTH — Cadastro e Login
# ════════════════════════════════════════════════════════════
@app.post("/auth/cadastro", status_code=201)
@limiter.limit("5/minute")   # máximo 5 cadastros por minuto por IP
def cadastro(request: Request, dados: UsuarioCriar, db: Session = Depends(get_db)):
    # Valida tamanho do nome
    if len(dados.nome.strip()) < 2:
        raise HTTPException(400, "Nome deve ter pelo menos 2 caracteres")

    # Valida senha mínima
    if len(dados.senha) < 6:
        raise HTTPException(400, "Senha deve ter pelo menos 6 caracteres")

    # Normaliza e-mail
    email = dados.email.strip().lower()

    if db.query(models.Usuario).filter(models.Usuario.email == email).first():
        raise HTTPException(400, "E-mail já cadastrado")

    usuario = models.Usuario(
        nome       = dados.nome.strip(),
        email      = email,
        senha_hash = auth.hash_senha(dados.senha),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    token = auth.criar_token({"sub": usuario.email})
    return {"token": token, "nome": usuario.nome, "plano": usuario.plano}

@app.post("/auth/login")
@limiter.limit("10/minute")  # máximo 10 tentativas de login por minuto por IP
def login(request: Request, dados: LoginInput, db: Session = Depends(get_db)):
    email   = dados.email.strip().lower()
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()

    # Mesmo erro para email ou senha inválidos (não revela qual está errado)
    if not usuario or not auth.verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(401, "E-mail ou senha incorretos")

    if not usuario.ativo:
        raise HTTPException(403, "Conta desativada. Entre em contato com o suporte.")

    token = auth.criar_token({"sub": usuario.email})
    return {"token": token, "nome": usuario.nome, "plano": usuario.plano}

@app.get("/auth/perfil")
def perfil(usuario = Depends(auth.usuario_atual)):
    return {
        "id":       usuario.id,
        "nome":     usuario.nome,
        "email":    usuario.email,
        "plano":    usuario.plano,
        "ativo":    usuario.ativo,
    }

# ════════════════════════════════════════════════════════════
# RECEITAS
# ════════════════════════════════════════════════════════════
@app.get("/receitas")
def listar_receitas(
    categoria: Optional[str] = None,
    dificuldade: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario = Depends(auth.usuario_atual)
):
    query = db.query(models.Receita)

    # Usuário gratuito só vê receitas não-premium
    if usuario.plano == "gratuito":
        query = query.filter(models.Receita.premium == False)

    if categoria:
        query = query.filter(models.Receita.categoria == categoria)
    if dificuldade:
        query = query.filter(models.Receita.dificuldade == dificuldade)

    return query.all()

@app.get("/receitas/{id}")
def detalhe_receita(id: int, db: Session = Depends(get_db), usuario = Depends(auth.usuario_atual)):
    receita = db.query(models.Receita).filter(models.Receita.id == id).first()
    if not receita:
        raise HTTPException(404, "Receita não encontrada")
    if receita.premium and usuario.plano == "gratuito":
        raise HTTPException(403, "Receita exclusiva para assinantes premium")
    return receita

@app.post("/receitas", status_code=201)
def criar_receita(
    dados: ReceitaCriar,
    db: Session = Depends(get_db),
    usuario = Depends(auth.requer_plano(["mensal", "anual"]))
):
    receita = models.Receita(**dados.dict())
    db.add(receita)
    db.commit()
    db.refresh(receita)
    return receita

@app.post("/receitas/{id}/foto")
def upload_foto(
    id: int,
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario = Depends(auth.usuario_atual)
):
    receita = db.query(models.Receita).filter(models.Receita.id == id).first()
    if not receita:
        raise HTTPException(404, "Receita não encontrada")

    ext      = foto.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(FOTOS_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(foto.file, f)

    receita.foto_url = f"/fotos/{filename}"
    db.commit()
    return {"foto_url": receita.foto_url}

# ════════════════════════════════════════════════════════════
# FAVORITOS
# ════════════════════════════════════════════════════════════
@app.get("/favoritos")
def listar_favoritos(usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    favs = db.query(models.Favorito).filter(models.Favorito.usuario_id == usuario.id).all()
    return [{"receita": f.receita, "salvo_em": f.salvo_em} for f in favs]

@app.post("/favoritos/{receita_id}", status_code=201)
def salvar_favorito(receita_id: int, usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    existe = db.query(models.Favorito).filter_by(usuario_id=usuario.id, receita_id=receita_id).first()
    if existe:
        raise HTTPException(400, "Já está nos favoritos")
    fav = models.Favorito(usuario_id=usuario.id, receita_id=receita_id)
    db.add(fav)
    db.commit()
    return {"ok": True}

@app.delete("/favoritos/{receita_id}")
def remover_favorito(receita_id: int, usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    fav = db.query(models.Favorito).filter_by(usuario_id=usuario.id, receita_id=receita_id).first()
    if not fav:
        raise HTTPException(404, "Favorito não encontrado")
    db.delete(fav)
    db.commit()
    return {"ok": True}

# ════════════════════════════════════════════════════════════
# ASSINATURAS — Stripe
# ════════════════════════════════════════════════════════════
PRECOS = {
    "mensal": {"valor": 2990, "stripe_price": "price_mensal"},   # R$ 29,90
    "anual":  {"valor": 24900, "stripe_price": "price_anual"},   # R$ 249,00
}

@app.get("/planos")
def listar_planos():
    return [
        {"id": "mensal", "nome": "Mensal", "valor": "R$ 29,90/mês", "destaque": False},
        {"id": "anual",  "nome": "Anual",  "valor": "R$ 249,00/ano", "desconto": "30% off", "destaque": True},
    ]

@app.post("/assinaturas/assinar")
def assinar(dados: AssinarInput, usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    if dados.plano not in PRECOS:
        raise HTTPException(400, "Plano inválido")

    preco = PRECOS[dados.plano]

    try:
        # Cria ou recupera cliente no Stripe
        assinatura_db = db.query(models.Assinatura).filter_by(usuario_id=usuario.id).first()
        if assinatura_db and assinatura_db.stripe_customer_id:
            customer_id = assinatura_db.stripe_customer_id
        else:
            customer = stripe.Customer.create(email=usuario.email, name=usuario.nome)
            customer_id = customer.id

        # Cria a assinatura
        sub = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": preco["stripe_price"]}],
        )

        # Salva no banco
        if assinatura_db:
            assinatura_db.stripe_sub_id     = sub.id
            assinatura_db.plano             = dados.plano
            assinatura_db.status            = "ativa"
            assinatura_db.valor             = preco["valor"]
            assinatura_db.stripe_customer_id= customer_id
        else:
            nova = models.Assinatura(
                usuario_id          = usuario.id,
                stripe_customer_id  = customer_id,
                stripe_sub_id       = sub.id,
                plano               = dados.plano,
                status              = "ativa",
                valor               = preco["valor"],
                inicio              = datetime.utcnow(),
            )
            db.add(nova)

        usuario.plano = dados.plano
        db.commit()
        return {"ok": True, "plano": dados.plano}

    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e.user_message))

@app.post("/assinaturas/cancelar")
def cancelar(usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    assinatura = db.query(models.Assinatura).filter_by(usuario_id=usuario.id).first()
    if not assinatura:
        raise HTTPException(404, "Nenhuma assinatura ativa")

    try:
        stripe.Subscription.cancel(assinatura.stripe_sub_id)
        assinatura.status = "cancelada"
        usuario.plano     = "gratuito"
        db.commit()
        return {"ok": True}
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e.user_message))

# ════════════════════════════════════════════════════════════
# PRODUTOS — busca no SQLite
# ════════════════════════════════════════════════════════════
PRODUTOS_DB = os.path.join(BASE_DIR, "arquivos", "produtos.db")

@app.get("/produtos/buscar")
@limiter.limit("60/minute")
def buscar_produtos(request: Request, q: str, limite: int = 20):
    if len(q.strip()) < 2:
        raise HTTPException(400, "Digite pelo menos 2 caracteres para buscar")
    if limite > 100:
        limite = 100

    conn = sqlite3.connect(PRODUTOS_DB)
    cur  = conn.cursor()
    cur.execute(
        "SELECT id, nome FROM produtos WHERE nome LIKE ? ORDER BY nome LIMIT ?",
        (f"%{q.upper()}%", limite)
    )
    resultados = [{"id": row[0], "nome": row[1]} for row in cur.fetchall()]
    conn.close()
    return {"total": len(resultados), "produtos": resultados}

# ════════════════════════════════════════════════════════════
# IMPORTAR RECEITAS DO JSON EXISTENTE
# ════════════════════════════════════════════════════════════
@app.post("/admin/importar-json")
def importar_json(db: Session = Depends(get_db)):
    json_path = os.path.join(BASE_DIR, "receitas_premium.json")
    with open(json_path, encoding="utf-8") as f:
        dados = json.load(f)

    importadas = 0
    for r in dados["receitas"]:
        existe = db.query(models.Receita).filter(models.Receita.nome == r["nome"]).first()
        if not existe:
            receita = models.Receita(
                nome          = r["nome"],
                categoria     = r["categoria"],
                descricao     = r["descricao"],
                tempo_preparo = r["tempo_preparo"],
                dificuldade   = r["dificuldade"],
                porcoes       = r["porcoes"],
                ingredientes  = r["ingredientes"],
                tecnica       = r["tecnica"],
                vinhos        = r["harmonizacao"]["vinhos"],
                mise_en_place = r["mise_en_place"],
                dica_chef     = r["dica_chef"],
                premium       = True,
            )
            db.add(receita)
            importadas += 1

    db.commit()
    return {"importadas": importadas}

# ════════════════════════════════════════════════════════════
# IA — Geração de receitas com Claude
# ════════════════════════════════════════════════════════════
class GerarReceitaInput(BaseModel):
    tipo: str
    pessoas: str
    proteinas: list
    dificuldade: str
    ambiente: str
    restricoes: list
    vinhos: list
    contexto: str = ""

@app.post("/ia/gerar-receita")
@limiter.limit("3/minute")
def gerar_receita_ia(
    request: Request,
    dados: GerarReceitaInput,
    usuario = Depends(auth.requer_plano(["mensal", "anual"]))
):
    if not _ai_client:
        raise HTTPException(503, "Módulo de IA não instalado no servidor")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "coloque_sua_chave_anthropic_aqui":
        raise HTTPException(503, "Serviço de IA não configurado")

    proteinas_str  = ", ".join(dados.proteinas)  if dados.proteinas  else "qualquer proteína"
    restricoes_str = ", ".join(dados.restricoes) if dados.restricoes else "nenhuma"
    vinhos_str     = ", ".join(dados.vinhos)     if dados.vinhos     else "qualquer vinho"

    prompt = f"""Você é um chef executivo de alta gastronomia. Crie 3 receitas premium sofisticadas.

Tipo de encontro: {dados.tipo}
Número de pessoas: {dados.pessoas}
Proteínas preferidas: {proteinas_str}
Nível de dificuldade: {dados.dificuldade}
Ambiente e clima: {dados.ambiente}
Restrições alimentares: {restricoes_str}
Preferências de vinho: {vinhos_str}
Contexto adicional: {dados.contexto or "nenhum"}

Retorne APENAS um JSON válido (sem markdown, sem texto fora do JSON) com esta estrutura exata:
{{
  "intro": "texto introdutório elegante de 2-3 frases",
  "nota_sommelier": "nota do sommelier sobre os vinhos selecionados",
  "receitas": [
    {{
      "numero": 1,
      "nome": "Nome Elegante da Receita",
      "foto_busca": "realistic gourmet dish photo search term in english (ex: seared sea bass champagne sauce)",
      "categoria": "Peixe",
      "clima": "como esta receita combina com o encontro (1 frase)",
      "descricao": "descrição sofisticada da receita em 2-3 frases",
      "tempo": "XX min",
      "dificuldade": "Alta",
      "porcoes": "2 pessoas",
      "ingredientes": ["Ingrediente Premium — quantidade"],
      "tecnica": ["Passo técnico essencial"],
      "vinhos": ["Vinho Sugerido 1", "Vinho Sugerido 2"],
      "mesa": [{{"nome": "Item da Mesa", "desc": "Sugestão de apresentação"}}],
      "dica_chef": "dica técnica exclusiva e surpreendente do chef"
    }}
  ]
}}"""

    try:
        msg = _ai_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        texto = msg.content[0].text.strip()
        # Remove blocos markdown se presentes
        if "```" in texto:
            m = re.search(r'```(?:json)?\s*([\s\S]*?)```', texto)
            if m:
                texto = m.group(1).strip()
        # Extrai apenas o objeto JSON principal
        inicio = texto.find('{')
        fim    = texto.rfind('}')
        if inicio != -1 and fim != -1:
            texto = texto[inicio:fim+1]
        # Corrige vírgulas extras antes de } ou ] (erro comum de LLMs)
        texto = re.sub(r',\s*([}\]])', r'\1', texto)
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Erro ao processar resposta da IA. Tente novamente. Detalhe: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Erro no serviço de IA: {str(e)}")


# ════════════════════════════════════════════════════════════
# FOTOS — Unsplash
# ════════════════════════════════════════════════════════════
@app.get("/ia/foto")
@limiter.limit("30/minute")
def buscar_foto(request: Request, q: str, usuario = Depends(auth.usuario_atual)):
    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        return {"url": None}

    params = urllib.parse.urlencode({"query": q, "per_page": 1, "orientation": "landscape"})
    url = f"https://api.unsplash.com/search/photos?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Client-ID {access_key}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("results"):
                return {"url": data["results"][0]["urls"]["regular"]}
    except Exception:
        pass
    return {"url": None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
