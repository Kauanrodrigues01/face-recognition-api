# Face Recognition API - Sistema de Autenticação Biométrica Facial

<p align="center">
  <img src="https://raw.githubusercontent.com/Kauanrodrigues01/Kauanrodrigues01/refs/heads/main/images/projetos/face-recognition-api/face-recognition-api.png" alt="Face Recognition Demo" width="1000"/>
</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-6BA81E?style=for-the-badge)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

</p>

## 📋 Sobre o Projeto

API RESTful completa para **autenticação biométrica facial** com alta segurança e precisão. O sistema utiliza tecnologia de ponta em reconhecimento facial (InsightFace) combinada com validações rigorosas de qualidade, detecção anti-spoofing e criptografia de dados biométricos.

## ✨ Funcionalidades

- 🔐 **Autenticação JWT** - Sistema completo de login com tokens seguros
- 👤 **Cadastro Biométrico Facial** - Registro de face com validação de qualidade
- 🎭 **Login por Reconhecimento Facial** - Autenticação usando apenas email + foto
- 🛡️ **Anti-Spoofing** - Detecção de tentativas de fraude com fotos impressas ou telas
- ⚡ **Validação de Qualidade** - Score de qualidade facial de 0-100
- 🔒 **Criptografia de Embeddings** - Dados biométricos criptografados com Fernet (AES-128)
- 📊 **Níveis de Segurança Configuráveis** - HIGH, MEDIUM, LOW
- 🖼️ **Múltiplos Formatos de Entrada** - Suporte para base64 e upload de arquivo
- 🐳 **Containerização Completa** - Deploy simples com Docker Compose
- 📚 **Documentação Interativa** - Swagger UI e ReDoc integrados

## 🛠️ Tecnologias Utilizadas

### Backend
- **[FastAPI](https://fastapi.tiangolo.com/)** - Framework web moderno e de alta performance
- **[Python 3.12+](https://www.python.org/)** - Linguagem de programação
- **[SQLAlchemy](https://www.sqlalchemy.org/)** - ORM para gerenciamento do banco de dados
- **[Alembic](https://alembic.sqlalchemy.org/)** - Migrations do banco de dados
- **[Pydantic](https://docs.pydantic.dev/)** - Validação de dados e schemas

### Reconhecimento Facial
- **[InsightFace](https://github.com/deepinsight/insightface)** - Framework de reconhecimento facial
- **[OpenCV](https://opencv.org/)** - Processamento de imagens
- **[MediaPipe](https://mediapipe.dev/)** - Detecção de landmarks faciais
- **[NumPy](https://numpy.org/)** - Computação científica

### Banco de Dados
- **[PostgreSQL](https://www.postgresql.org/)** - Banco de dados relacional
- **[AsyncPG](https://github.com/MagicStack/asyncpg)** - Driver assíncrono para PostgreSQL

### Segurança
- **[Python-JOSE](https://github.com/mpdavis/python-jose)** - Geração e validação de tokens JWT
- **[Passlib](https://passlib.readthedocs.io/)** - Hashing de senhas com bcrypt
- **[Cryptography](https://cryptography.io/)** - Criptografia de embeddings faciais

### DevOps
- **[Docker](https://www.docker.com/)** - Containerização
- **[Docker Compose](https://docs.docker.com/compose/)** - Orquestração de containers
- **[Poetry](https://python-poetry.org/)** - Gerenciamento de dependências
- **[Pytest](https://pytest.org/)** - Testes automatizados

## 📋 Pré-requisitos

- **Docker** e **Docker Compose** (recomendado)
- **Python 3.12+** (para desenvolvimento local)
- **PostgreSQL 17+** (para desenvolvimento local)
- **Poetry** ou **uv** (gerenciador de pacotes Python)

## 🚀 Instalação e Execução

### 🐳 Usando Docker (Recomendado)

```bash
# 1. Clone o repositório
git clone https://github.com/Kauanrodrigues01/face-recognition-api.git
cd face-recognition-api

# 2. Configure as variáveis de ambiente
cp .env.example .env

# 3. Gere uma chave de criptografia para os embeddings faciais
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 4. Adicione a chave gerada no arquivo .env
# FACE_ENCRYPTION_KEY=sua-chave-gerada-aqui

# 5. Inicie os containers
docker-compose up -d --build

# 6. Visualize os logs
docker-compose logs -f app

# 7. Acesse a API
# http://localhost:8000
```

### 💻 Desenvolvimento Local

```bash
# 1. Clone o repositório
git clone https://github.com/Kauanrodrigues01/face-recognition-api.git
cd face-recognition-api

# 2. Instale as dependências com Poetry
poetry install

# 3. Configure as variáveis de ambiente
cp .env.example .env

# 4. Gere a chave de criptografia
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 5. Execute as migrações do banco de dados
poetry run task migrate

# 6. Inicie o servidor de desenvolvimento
poetry run task run

# 7. Acesse a API
# http://localhost:8000
```

## 📖 Uso da API

### Documentação Interativa

Após iniciar o servidor, acesse:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Fluxo Completo de Autenticação

#### 1️⃣ Cadastrar Usuário

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "name": "João Silva",
    "password": "senha123"
  }'
```

#### 2️⃣ Login Tradicional (Email + Senha)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "password": "senha123"
  }'
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

#### 3️⃣ Cadastrar Biometria Facial

```bash
curl -X POST http://localhost:8000/api/v1/auth/face/enroll \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "face_image_base64": "data:image/jpeg;base64,/9j/4AAQ..."
  }'
```

**Resposta:**
```json
{
  "success": true,
  "message": "Face enrolled successfully",
  "quality_score": 87,
  "face_enrolled": true
}
```

#### 4️⃣ Login com Reconhecimento Facial

```bash
curl -X POST http://localhost:8000/api/v1/auth/face/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@example.com",
    "face_image_base64": "data:image/jpeg;base64,/9j/4AAQ..."
  }'
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "usuario@example.com",
    "name": "João Silva",
    "face_enrolled": true
  }
}
```

### 📸 Requisitos da Imagem

- ✅ **Resolução mínima:** 200x200 pixels
- ✅ **Formato:** JPEG, PNG, BMP, WEBP
- ✅ **Conteúdo:** Apenas 1 rosto visível
- ✅ **Qualidade:** Boa iluminação e foco nítido
- ✅ **Pose:** Frontal (ângulos < 30°)
- ❌ **Evitar:** Fotos impressas, telas de celular (anti-spoofing)

### 🔒 Níveis de Segurança

| Nível | Threshold | Uso Recomendado |
|-------|-----------|-----------------|
| `HIGH` | 0.35 | Login, transações sensíveis |
| `MEDIUM` | 0.45 | Acesso geral |
| `LOW` | 0.55 | Identificação com baixo risco |

## 📁 Estrutura do Projeto

```
face-recognition-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── api.py           # Roteador principal da API
│   ├── core/
│   │   └── config.py            # Configurações do projeto
│   ├── db/
│   │   └── database.py          # Configuração do banco de dados
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── router.py        # Endpoints de autenticação
│   │   │   ├── schemas.py       # Schemas Pydantic de auth
│   │   │   └── service.py       # Lógica de negócio de auth
│   │   └── user/
│   │       ├── models.py        # Modelo SQLAlchemy de usuário
│   │       ├── router.py        # Endpoints de usuário
│   │       ├── schemas.py       # Schemas Pydantic de usuário
│   │       └── service.py       # Lógica de negócio de usuário
│   ├── services/
│   │   ├── auth.py              # Serviço de autenticação JWT
│   │   ├── encryption_service.py # Criptografia de embeddings
│   │   └── face_recognition_service.py # Reconhecimento facial
│   └── main.py                  # Aplicação FastAPI
├── alembic/
│   └── versions/                # Migrações do banco de dados
├── tests/
│   ├── conftest.py              # Configuração de testes
│   ├── test_auth.py             # Testes de autenticação
│   └── test_users.py            # Testes de usuários
├── .env.example                 # Exemplo de variáveis de ambiente
├── docker-compose.yml           # Configuração Docker Compose
├── Dockerfile                   # Imagem Docker da aplicação
├── pyproject.toml               # Dependências e configurações
└── README.md                    # Este arquivo
```

## 🧪 Testes

```bash
# Executar todos os testes
poetry run task test

# Executar testes com cobertura
poetry run task test-cov

# Executar testes em modo watch
poetry run task test-watch
```

## ⚙️ Variáveis de Ambiente

```env
# Projeto
PROJECT_NAME=Face Recognition API
VERSION=0.1.0
DESCRIPTION=API for face recognition with PostgreSQL backend
API_V1_STR=/api/v1

# Banco de Dados
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/face_recognition
DATABASE_TEST_URL=postgresql+asyncpg://postgres:password@localhost:5432/face_recognition_test

# Segurança
SECRET_KEY=sua-chave-secreta-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Criptografia de Face
FACE_ENCRYPTION_KEY=sua-chave-fernet-aqui

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## 📊 Performance

### Tempos Médios de Resposta

- **Face Detection:** ~100-300ms
- **Embedding Extraction:** ~50-150ms
- **Face Comparison:** ~5-10ms
- **Total (Enrollment):** ~200-500ms
- **Total (Login):** ~250-600ms

### Otimizações

- 🚀 GPU acelera detecção em ~3-5x
- 💾 Cache de modelos reduz tempo de inicialização
- ⚡ Singleton de serviços evita recarregamento

## 🔐 Segurança

### Práticas Implementadas

1. ✅ **Criptografia de embeddings** com Fernet (AES-128)
2. ✅ **Hashing de senhas** com bcrypt
3. ✅ **Tokens JWT** com expiração configurável
4. ✅ **Validação de qualidade facial** (score mínimo 80/100)
5. ✅ **Anti-spoofing** para detecção de fraudes
6. ✅ **Validação de pose** (ângulos < 30°)
7. ✅ **CORS** configurável

### Recomendações para Produção

- 🔒 Use HTTPS em produção
- 🔑 Rotacione chaves de criptografia periodicamente
- 📝 Implemente logs de auditoria
- ⏱️ Configure rate limiting
- 🛡️ Use variáveis de ambiente seguras

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👨‍💻 Autor

**Kauan Rodrigues Lima**

- GitHub: [Kauanrodrigues01](https://github.com/Kauanrodrigues01)
- LinkedIn: [Kauan Rodrigues](https://www.linkedin.com/in/kauan-rodrigues-lima/)

---

<p align="center">Desenvolvido com ❤️ e ☕</p>
