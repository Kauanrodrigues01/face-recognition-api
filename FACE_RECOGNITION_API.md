# Face Recognition API - Guia de Integração

## Visão Geral

A API agora possui sistema completo de reconhecimento facial com:
- ✅ Cadastro biométrico facial
- ✅ Login com email + foto
- ✅ Anti-spoofing e validação de qualidade
- ✅ Criptografia de embeddings
- ✅ Níveis de segurança configuráveis

## Configuração Inicial

### 1. Gerar chave de criptografia

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Adicione a chave gerada no arquivo `.env`:

```env
FACE_ENCRYPTION_KEY=sua-chave-gerada-aqui
```

### 2. Executar migração do banco de dados

```bash
poetry run task migrate
```

## Endpoints Disponíveis

### 1. Cadastro de Usuário (Tradicional)

**POST** `/api/v1/users/`

```json
{
  "email": "user@example.com",
  "name": "João Silva",
  "password": "senha123"
}
```

**Resposta:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "João Silva",
  "is_active": true,
  "face_enrolled": false,
  "created_at": "2025-01-15T10:30:00"
}
```

---

### 2. Login Tradicional (Email + Senha)

**POST** `/api/v1/auth/login`

```json
{
  "email": "user@example.com",
  "password": "senha123"
}
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

---

### 3. Cadastrar Biometria Facial

**POST** `/api/v1/auth/face/enroll`

**Headers:**
```
Authorization: Bearer {seu_token_jwt}
```

**Body:**
```json
{
  "face_image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
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

**Possíveis Erros:**
- `400 Bad Request` - No face detected
- `400 Bad Request` - Multiple faces detected
- `400 Bad Request` - Face quality too low
- `400 Bad Request` - Potential spoofing detected

---

### 4. Login com Reconhecimento Facial

**POST** `/api/v1/auth/face/login`

**Body:**
```json
{
  "email": "user@example.com",
  "face_image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "João Silva",
    "face_enrolled": true
  }
}
```

**Notas:**
- Usa nível de segurança **HIGH** por padrão
- Realiza verificação de liveness (anti-spoofing)
- Retorna `401 Unauthorized` se face não corresponder

---

## Fluxo de Uso Completo

### 1️⃣ Cadastro com Biometria Facial

```bash
# 1. Criar usuário
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "João Silva",
    "password": "senha123"
  }'

# 2. Login tradicional para obter token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "senha123"
  }' | jq -r '.access_token')

# 3. Cadastrar face
curl -X POST http://localhost:8000/api/v1/auth/face/enroll \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "face_image_base64": "data:image/jpeg;base64,...sua_imagem_aqui..."
  }'
```

### 2️⃣ Login com Reconhecimento Facial

```bash
# Login direto com email + foto
curl -X POST http://localhost:8000/api/v1/auth/face/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "face_image_base64": "data:image/jpeg;base64,...sua_imagem_aqui..."
  }'
```

---

## Formato de Imagem

### Formatos Aceitos

O campo `face_image_base64` aceita:

1. **Base64 com prefixo (recomendado)**
   ```
   data:image/jpeg;base64,/9j/4AAQSkZJRg...
   ```

2. **Base64 puro**
   ```
   /9j/4AAQSkZJRg...
   ```

### Requisitos da Imagem

- ✅ **Resolução mínima:** 200x200 pixels
- ✅ **Formato:** JPEG, PNG, BMP, WEBP
- ✅ **Conteúdo:** Apenas 1 rosto visível
- ✅ **Qualidade:** Boa iluminação, foco nítido
- ✅ **Pose:** Frontal, sem ângulos extremos
- ❌ **Evitar:** Fotos impressas, telas de celular (anti-spoofing)

### Converter Imagem para Base64

**Python:**
```python
import base64

with open("foto.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()
    # Adicionar prefixo
    image_data_uri = f"data:image/jpeg;base64,{image_base64}"
```

**JavaScript:**
```javascript
// Do input file
const file = document.getElementById('fileInput').files[0];
const reader = new FileReader();
reader.onload = (e) => {
  const base64 = e.target.result; // Já inclui prefixo
  console.log(base64);
};
reader.readAsDataURL(file);
```

---

## Níveis de Segurança

O serviço suporta 3 níveis de segurança para comparação facial:

| Nível | Threshold | Uso Recomendado |
|-------|-----------|-----------------|
| `HIGH` | 0.35 | Login, transações sensíveis |
| `MEDIUM` | 0.45 | Acesso geral |
| `LOW` | 0.55 | Identificação com baixo risco |

**Padrão usado:**
- Enrollment: `GOOD` quality (80/100)
- Login: `HIGH` security (0.35)

---

## Validações e Qualidade

### Checagens Automáticas

1. **Detecção de Rosto**
   - Pelo menos 1 rosto detectado
   - Apenas 1 rosto na imagem

2. **Qualidade da Imagem**
   - Resolução adequada (≥ 200px)
   - Iluminação balanceada
   - Contraste suficiente
   - Nitidez (sem blur)

3. **Anti-Spoofing (Liveness)**
   - Análise de textura
   - Distribuição de cores
   - Detecção de padrões suspeitos

4. **Pose Facial**
   - Ângulos não extremos (pitch, yaw, roll < 30°)

### Score de Qualidade

O sistema retorna um score de 0-100:

- **95-100:** Excelente
- **80-94:** Bom ✅ (mínimo para enrollment)
- **65-79:** Aceitável (mínimo para login)
- **50-64:** Pobre
- **0-49:** Muito baixo ❌

---

## Segurança

### Criptografia

- Embeddings faciais são criptografados com **Fernet** (AES 128-bit)
- Chave de criptografia deve ser armazenada em variável de ambiente
- Embeddings nunca são armazenados em texto plano

### Boas Práticas

1. **Nunca expor embeddings descriptografados**
2. **Rotacionar chave de criptografia periodicamente**
3. **Usar HTTPS em produção**
4. **Implementar rate limiting nos endpoints de face**
5. **Logs detalhados de tentativas de login facial**

---

## Tratamento de Erros

### Erros Comuns

| Código | Erro | Solução |
|--------|------|---------|
| 400 | No face detected | Enviar foto com rosto visível |
| 400 | Multiple faces detected | Enviar foto com apenas 1 rosto |
| 400 | Face quality too low | Melhorar iluminação e qualidade |
| 400 | Potential spoofing | Usar foto ao vivo, não impressa |
| 401 | Face authentication failed | Face não corresponde ao cadastro |
| 500 | Services not configured | Verificar variáveis de ambiente |

---

## Exemplo Completo (Python)

```python
import requests
import base64

BASE_URL = "http://localhost:8000/api/v1"

# 1. Criar usuário
user_data = {
    "email": "teste@example.com",
    "name": "Teste User",
    "password": "senha123"
}
response = requests.post(f"{BASE_URL}/users/", json=user_data)
user = response.json()
print(f"Usuário criado: {user['id']}")

# 2. Login tradicional
login_data = {
    "email": "teste@example.com",
    "password": "senha123"
}
response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
token = response.json()["access_token"]
print(f"Token: {token[:20]}...")

# 3. Cadastrar face
with open("foto.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()

enroll_data = {
    "face_image_base64": f"data:image/jpeg;base64,{image_base64}"
}
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    f"{BASE_URL}/auth/face/enroll",
    json=enroll_data,
    headers=headers
)
print(f"Face cadastrada: {response.json()}")

# 4. Login com face
with open("foto_login.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()

face_login_data = {
    "email": "teste@example.com",
    "face_image_base64": f"data:image/jpeg;base64,{image_base64}"
}
response = requests.post(f"{BASE_URL}/auth/face/login", json=face_login_data)
result = response.json()
print(f"Login facial bem-sucedido!")
print(f"Token: {result['access_token'][:20]}...")
print(f"Usuário: {result['user']}")
```

---

## Performance

### Tempos Médios

- **Face Detection:** ~100-300ms
- **Embedding Extraction:** ~50-150ms
- **Face Comparison:** ~5-10ms
- **Total (Enrollment):** ~200-500ms
- **Total (Login):** ~250-600ms

### Otimização

- GPU acelera detecção em ~3-5x
- Cache de modelos reduz tempo de inicialização
- Singleton de serviços evita recarregamento

---

## Próximos Passos

1. ✅ Sistema básico funcionando
2. 🔄 Implementar rate limiting
3. 🔄 Adicionar logs de auditoria
4. 🔄 Melhorar anti-spoofing com modelos especializados
5. 🔄 Suporte a liveness ativo (piscar, movimento de cabeça)
6. 🔄 Dashboard de métricas de qualidade

---

## Suporte

Para dúvidas ou problemas, verifique:
- Logs da aplicação
- Variáveis de ambiente configuradas
- Modelos InsightFace baixados corretamente
- Permissões de GPU (se usando CUDA)