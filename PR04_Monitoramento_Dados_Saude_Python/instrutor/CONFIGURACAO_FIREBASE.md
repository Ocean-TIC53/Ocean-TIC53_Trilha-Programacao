# Firebase — configuração recomendada para a oficina

Este documento descreve a configuração do **Firebase Realtime Database** compatível com o código atual da oficina, **sem alterar o publicador do instrutor nem os notebooks dos alunos**.

A arquitetura adotada é:

```text
PUBLICADOR DO INSTRUTOR
Google Colab + Firebase Admin SDK
Secret: FIREBASE_SERVICE_ACCOUNT_JSON
             |
             | escrita administrativa
             v
Firebase Realtime Database
/oficina/live
             |
             | leitura pública (GET + SSE)
             v
NOTEBOOKS DOS ALUNOS
requests + Server-Sent Events (SSE)
```

O ponto principal é separar as permissões:

- os **alunos** podem apenas **ler** `/oficina/live`;
- o **publicador do instrutor** pode escrever usando uma **conta de serviço** e o Firebase Admin SDK;
- os alunos não recebem chave privada, senha ou credencial administrativa;
- a URL do Realtime Database pode aparecer nos notebooks e slides, pois ela **não é o segredo**.

---

## 1. Regras do Realtime Database

### Configuração recomendada

No Firebase Console, abra:

**Realtime Database → Rules**

Use:

```json
{
  "rules": {
    ".read": false,
    ".write": false,

    "oficina": {
      "live": {
        ".read": true
      }
    }
  }
}
```

Com essa configuração:

- o restante do banco fica bloqueado por padrão;
- `/oficina/live` pode ser lido sem autenticação pelos notebooks dos alunos;
- clientes comuns não podem escrever em `/oficina/live`;
- o publicador do instrutor continua conseguindo escrever porque usa o Firebase Admin SDK com uma conta de serviço.

### Variante com leitura limitada no tempo

Se for desejável que os dados deixem de ser públicos depois da oficina, pode-se usar uma condição de tempo:

```json
{
  "rules": {
    ".read": false,
    ".write": false,

    "oficina": {
      "live": {
        ".read": "now < 1798772399000"
      }
    }
  }
}
```

O valor `1798772399000` corresponde a **31/12/2026 às 23:59:59 no horário de Brasília**.

Após essa data, os clientes deixarão de conseguir ler `/oficina/live`, mas o Admin SDK continuará podendo acessar o banco com as credenciais administrativas.

---

## 2. Por que não usar as regras antigas com escrita temporária

Uma configuração como esta:

```json
{
  "rules": {
    ".read": true,
    ".write": false,
    "oficina": {
      "live": {
        ".read": "now < 1798772399000",
        ".write": "now < 1798772399000"
      }
    }
  }
}
```

não é adequada para a oficina por dois motivos:

1. `".read": true` na raiz torna todo o banco legível publicamente. Uma regra mais profunda não serve para retirar uma permissão já concedida em um nível superior.
2. `".write": "now < ..."` em `/oficina/live` permite que qualquer cliente que conheça a URL escreva nesse nó enquanto a condição for verdadeira. Um aluno poderia, mesmo sem acesso ao Firebase Console, sobrescrever ou apagar os dados usando a API REST.

Por isso, a recomendação é deixar a escrita bloqueada nas Security Rules e reservar a escrita ao Admin SDK do instrutor.

---

## 3. Compatibilidade com o publicador atual

O notebook atual do instrutor é:

```text
instrutor/publicador_sintetico_firebase_admin.ipynb
```

Ele já usa o **Firebase Admin SDK** e espera um Secret do Google Colab chamado exatamente:

```text
FIREBASE_SERVICE_ACCOUNT_JSON
```

Trecho atual do notebook:

```python
cred_info = json.loads(userdata.get("FIREBASE_SERVICE_ACCOUNT_JSON"))
cred = credentials.Certificate(cred_info)
firebase_admin.initialize_app(cred, {"databaseURL": firebase_url})
```

Depois, o código obtém a referência:

```python
return db.reference("oficina/live")
```

E publica cada pacote com:

```python
ref.set(pacote)
```

Portanto, **não é necessário alterar esse código**.

O Admin SDK autenticado por conta de serviço opera como ambiente administrativo/confiável. Por isso, o publicador consegue escrever mesmo quando as regras normais do Realtime Database contêm:

```json
".write": false
```

---

## 4. Criar a credencial no Firebase

É necessário gerar uma **conta de serviço** para o projeto Firebase usado pela oficina.

No Firebase Console:

1. Abra o projeto da oficina.
2. Clique no ícone de engrenagem e abra **Configurações do projeto**.
3. Abra a aba **Contas de serviço**.
4. Selecione **Firebase Admin SDK**.
5. Clique em **Gerar nova chave privada**.
6. Confirme a geração da chave.
7. Será baixado um arquivo `.json`.

O conteúdo terá uma estrutura semelhante a:

```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "...",
  "client_id": "..."
}
```

Esse arquivo é uma **credencial administrativa**.

### Armazenamento separado do Git

Guarde o JSON real nu pasta `credenciais-ocean do repositório` com o nome `conta-servico-firebase.json`. Essa pasta e o nome original
`oficina-python-saude-teste-firebase-adminsdk-chave-privada.json` é
bloqueado pelo `.gitignore`, mas a exclusão do Git **não** protege
chaves que já foram incluídas em commits anteriores.

Para usar o publicador no Google Colab, abra **Secrets** (ícone de chave),
crie `FIREBASE_SERVICE_ACCOUNT_JSON`, cole o conteúdo **da nova chave JSON**
e habilite o acesso do notebook ao Secret. O notebook do instrutor já lê
a credencial dessa forma e não precisa de alteração de código.


### Muito importante

Não deve ser:

- entregue aos alunos;
- colocado na pasta compartilhada do curso;
- incluído no ZIP dos materiais;
- inserido diretamente em uma célula do notebook;
- enviado para um repositório Git;
- publicado em slides ou capturas de tela.

Se essa chave for exposta, ela deve ser revogada e substituída por uma nova.

---

## 5. Criar o Secret no Google Colab

O Secret é criado pela interface do Colab, não pelo código Python.

Abra **somente o notebook do publicador do instrutor** no Google Colab.

Na barra lateral esquerda:

1. Clique no ícone de **chave / Secrets**.
2. Adicione um novo Secret.
3. Use exatamente este nome:

```text
FIREBASE_SERVICE_ACCOUNT_JSON
```

4. Abra o arquivo `.json` baixado do Firebase.
5. Copie **todo o conteúdo**, desde `{` até `}`.
6. Cole esse conteúdo como valor do Secret.
7. Ative a opção que permite ao notebook acessar esse Secret.

O valor deve ser o JSON completo, por exemplo:

```text
{
  "type": "service_account",
  "project_id": "...",
  ...
}
```

Não coloque aspas adicionais ao redor de todo o JSON.

### O que o código faz com o Secret

O notebook executa:

```python
userdata.get("FIREBASE_SERVICE_ACCOUNT_JSON")
```

Essa chamada recupera o Secret como texto.

Em seguida:

```python
json.loads(...)
```

transforma o texto JSON em um dicionário Python.

Finalmente:

```python
credentials.Certificate(cred_info)
```

cria a credencial usada pelo Firebase Admin SDK.

---

## 6. URL do Firebase

O banco usado atualmente é:

```text
https://oficina-python-saude-teste-default-rtdb.firebaseio.com
```

No publicador atual:

```python
FIREBASE_URL = "https://oficina-python-saude-teste-default-rtdb.firebaseio.com"
```

Essa URL **não é uma senha nem um segredo**.

Ela precisa ser conhecida pelos clientes porque identifica o Realtime Database que será consultado.

O que deve permanecer secreto é a chave privada da conta de serviço usada pelo Admin SDK.

---

## 7. Compatibilidade com os notebooks dos alunos

Os notebooks dos alunos continuam funcionando sem nenhuma alteração.

### Leitura pontual por HTTP

O cliente monta uma URL terminada em `.json` e usa `requests.get(...)`.

Exemplo conceitual:

```python
requests.get(
    "https://oficina-python-saude-teste-default-rtdb.firebaseio.com/oficina/live.json"
)
```

Como `/oficina/live` possui permissão de leitura, essa requisição funciona sem login.

### Leitura em tempo real por SSE

Nos checkpoints que usam atualização contínua, o cliente abre uma conexão HTTP com:

```python
headers = {"Accept": "text/event-stream"}
```

O Firebase envia eventos pela conexão SSE (**Server-Sent Events**).

Também nesse caso o cliente apenas lê os dados. Nenhuma credencial administrativa é necessária.

### Consequência prática

Os alunos podem:

- visualizar `/oficina/live`;
- executar os `GET` dos checkpoints;
- acompanhar os dados em tempo real por SSE;
- processar e visualizar ECG e PPG.

Eles não podem, usando clientes comuns:

- fazer `PUT`;
- fazer `POST`;
- fazer `PATCH`;
- fazer `DELETE`;
- sobrescrever o pacote publicado pelo instrutor.

---

## 8. Teste recomendado antes da oficina

Depois de aplicar as regras e configurar o Secret, faça dois testes.

### Teste 1 — publicador

Execute o notebook:

```text
publicador_sintetico_firebase_admin.ipynb
```

Ao iniciar a publicação, deverá aparecer algo semelhante a:

```text
Destino: /oficina/live (Admin SDK)
Sessão: ...
```

No Firebase Console, o conteúdo de `/oficina/live` deverá começar a ser atualizado.

Isso confirma que:

- o Secret foi lido corretamente;
- a conta de serviço é válida;
- o Admin SDK está conectado ao banco;
- a escrita administrativa funciona mesmo com `.write: false`.

### Teste 2 — cliente

Abra um dos notebooks dos alunos e execute a leitura de `/oficina/live`.

O cliente deve conseguir ler os dados normalmente.

Se desejar verificar o bloqueio de escrita, faça esse teste apenas em um ambiente controlado. Uma requisição de escrita sem autenticação deverá ser recusada pelo Firebase com erro de permissão.

Não é necessário incluir esse teste de escrita nos notebooks dos alunos.

---

## 9. Backup e restauração dos dados

Antes da oficina, é recomendável salvar uma cópia dos dados e das regras.

### Exportar os dados

No Firebase Console:

1. Abra **Realtime Database → Data**.
2. Selecione a raiz ou o nó desejado.
3. Abra o menu de opções.
4. Escolha **Export JSON**.

O arquivo exportado contém os dados do banco, mas **não substitui as Security Rules**.

Por isso, mantenha também uma cópia das regras utilizadas.

### Restaurar os dados

Para restaurar:

1. pare temporariamente o publicador;
2. abra **Realtime Database → Data**;
3. selecione o nó adequado;
4. escolha **Import JSON**;
5. selecione o arquivo de backup.

### Caso específico desta oficina

`/oficina/live` contém apenas o pacote corrente publicado pelo instrutor.

Se esse nó for apagado, em geral não é necessário importar backup: basta executar novamente o publicador. O próximo:

```python
ref.set(pacote)
```

recriará `/oficina/live` automaticamente.

---

## 10. Criar outro banco para repetir a oficina

Para criar outro Realtime Database com a mesma estrutura:

1. Crie ou abra um projeto no Firebase.
2. Habilite **Realtime Database**.
3. Defina a região desejada quando solicitado.
4. Aplique as regras descritas neste documento.
5. Gere uma nova chave privada em **Configurações do projeto → Contas de serviço → Firebase Admin SDK**.
6. Substitua o valor do Secret `FIREBASE_SERVICE_ACCOUNT_JSON` no Colab pela credencial do novo projeto.
7. Atualize `FIREBASE_URL` no publicador e nos notebooks dos alunos para a URL do novo banco.
8. Execute o publicador; ele criará `/oficina/live` automaticamente.

Não é necessário criar manualmente a estrutura interna de `/oficina/live` antes da primeira publicação.

O primeiro `ref.set(pacote)` cria o nó com campos como:

```text
/oficina/live
    ecg
    fs
    n
    ppg_ir
    ppg_red
    sample_start
    seq
    session_id
    source
    timestamp_pub
```

---

## 11. Não é necessário configurar Firebase Authentication para os alunos

Para a arquitetura atual da oficina, não é necessário:

- criar usuários no Firebase Authentication;
- criar senha para os alunos;
- fornecer tokens individuais;
- criar uma chave ou segredo em cada notebook;
- colocar a conta de serviço nos notebooks dos alunos.

A separação é feita pelas Security Rules:

```text
alunos   -> leitura pública de /oficina/live
instrutor -> escrita administrativa via Admin SDK
```

Isso mantém a atividade simples para os participantes e evita que vários alunos publiquem simultaneamente no mesmo nó.

---

## 12. Resumo da configuração final

### Firebase Realtime Database — Rules

```json
{
  "rules": {
    ".read": false,
    ".write": false,
    "oficina": {
      "live": {
        ".read": true
      }
    }
  }
}
```

Ou, se quiser expiração da leitura:

```json
{
  "rules": {
    ".read": false,
    ".write": false,
    "oficina": {
      "live": {
        ".read": "now < 1798772399000"
      }
    }
  }
}
```

### Secret do Colab do instrutor

Nome:

```text
FIREBASE_SERVICE_ACCOUNT_JSON
```

Valor:

```text
conteúdo completo do JSON da conta de serviço
```

### Publicador

```text
instrutor/publicador_sintetico_firebase_admin.ipynb
```

Nenhuma alteração de código necessária.

### Clientes dos alunos

Continuam usando:

- `requests.get(...)` para leitura REST;
- SSE para acompanhamento em tempo real;
- a URL pública do Realtime Database;
- nenhuma credencial administrativa.

---

## Referências oficiais

- Firebase Admin SDK — configuração: https://firebase.google.com/docs/admin/setup
- Firebase Realtime Database — Security Rules: https://firebase.google.com/docs/database/security
- Realtime Database Rules — comportamento: https://firebase.google.com/docs/database/security/core-syntax
- Realtime Database REST — streaming/SSE: https://firebase.google.com/docs/database/rest/retrieve-data#section-rest-streaming
- Segurança de projetos Firebase: https://firebase.google.com/support/guides/security-checklist
