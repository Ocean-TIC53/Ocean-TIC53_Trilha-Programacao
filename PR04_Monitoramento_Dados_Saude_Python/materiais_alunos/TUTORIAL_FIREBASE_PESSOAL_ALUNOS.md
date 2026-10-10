# Tutorial — Usando o gerador sintético com seu próprio Firebase

Este tutorial mostra como usar o notebook `publicador_sintetico_firebase_colab.ipynb` com um **Firebase Realtime Database criado por você**.

A ideia é reproduzir, em uma conta própria, a mesma arquitetura usada na oficina:

```text
Gerador sintético em Python
        |
        | Firebase Admin SDK
        v
Firebase Realtime Database
        |
        | leitura via HTTP / SSE
        v
Notebooks clientes
```

Assim, você pode continuar praticando depois da oficina **sem usar o banco de dados do instrutor**.

---

## 1. O que você vai precisar

- uma conta Google;
- acesso ao [Google Colab](https://colab.research.google.com/);
- uma conta/projeto no [Firebase](https://firebase.google.com/);
- o notebook:
  - `publicador_sintetico_firebase_colab.ipynb`;
- os notebooks clientes da oficina, caso queira testar leitura e atualização em tempo real.

> **Importante:** não é necessário conhecer o endereço, senha ou credenciais do Firebase usado pelo instrutor.

---

## 2. Criar seu projeto no Firebase

1. Acesse o Firebase.
2. Clique em **Criar um projeto**.
3. Escolha um nome para o projeto.
4. Siga as etapas de criação.
5. O Google Analytics é opcional para este exercício.

Ao terminar, abra o projeto criado.

---

## 3. Criar o Realtime Database

No menu do projeto:

1. Entre em **Build → Realtime Database**.
2. Clique em **Create Database**.
3. Escolha uma região disponível.
4. Conclua a criação.

O Firebase mostrará uma URL semelhante a:

```text
https://SEU-PROJETO-default-rtdb.firebaseio.com/
```

ou, dependendo da região:

```text
https://SEU-PROJETO-default-rtdb.REGIAO.firebasedatabase.app/
```

Copie essa URL. Ela será usada no gerador e nos notebooks clientes.

> A URL do banco **não é uma senha**. Ela identifica o endereço do Realtime Database.

---

## 4. Configurar as regras do banco

Para reproduzir a arquitetura da oficina, deixe:

- leitura pública apenas no nó `/oficina/live`;
- escrita bloqueada para clientes comuns;
- escrita realizada apenas pelo seu gerador autenticado com Firebase Admin SDK.

No Firebase, abra:

**Realtime Database → Rules**

e use:

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

Depois clique em **Publish**.

### O que essas regras significam?

```json
".read": false
```

bloqueia leitura pública no banco inteiro.

```json
".write": false
```

bloqueia escrita pública no banco inteiro.

A exceção:

```json
"oficina": {
  "live": {
    ".read": true
  }
}
```

permite que os notebooks clientes leiam:

```text
/oficina/live
```

sem autenticação.

A escrita continua bloqueada para clientes comuns.

---

## 5. Criar uma conta de serviço para o gerador

O notebook publicador usa o **Firebase Admin SDK**.

Para que ele possa escrever no banco, você precisa gerar uma credencial administrativa.

No Firebase:

1. abra **Configurações do projeto**;
2. entre em **Contas de serviço**;
3. selecione **Firebase Admin SDK**;
4. clique em **Gerar nova chave privada**;
5. confirme.

Será baixado um arquivo `.json`.

Ele terá uma estrutura semelhante a:

```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...",
  ...
}
```

## ATENÇÃO

Esse arquivo contém uma **chave privada administrativa**.

Nunca:

- envie esse arquivo para outras pessoas;
- coloque-o em uma pasta pública;
- publique-o no GitHub;
- coloque seu conteúdo diretamente em um notebook que será compartilhado;
- envie-o junto com trabalhos ou relatórios.

---

## 6. Criar o Secret no Google Colab

O notebook fornecido na oficina procura um Secret chamado:

```text
FIREBASE_SERVICE_ACCOUNT_JSON
```

Abra o notebook:

```text
publicador_sintetico_firebase_colab.ipynb
```

no Google Colab.

Na barra lateral esquerda:

1. clique no ícone de **chave / Secrets**;
2. crie um novo Secret;
3. no campo de nome, escreva exatamente:

```text
FIREBASE_SERVICE_ACCOUNT_JSON
```

4. abra o arquivo JSON da conta de serviço em um editor de texto;
5. copie **todo o conteúdo**, desde `{` até `}`;
6. cole esse conteúdo como valor do Secret;
7. permita que o notebook acesse esse Secret.

O valor deve ser o JSON original, por exemplo:

```text
{
  "type": "service_account",
  ...
}
```

e não uma string adicional entre aspas.

---

## 7. Informar a URL do seu Firebase no gerador

No notebook do gerador, procure a variável correspondente à URL do Firebase, por exemplo:

```python
FIREBASE_URL = "https://SEU-PROJETO-default-rtdb.firebaseio.com/"
```

Substitua somente o endereço pelo endereço do seu Realtime Database.

Exemplo genérico:

```python
FIREBASE_URL = "https://meu-projeto-default-rtdb.firebaseio.com/"
```

Não coloque credenciais, chaves ou senhas nessa variável.

---

## 8. Como o gerador se autentica

O notebook já foi preparado para ler a credencial do gerenciador de Secrets do Colab.

A lógica usada é equivalente a:

```python
import json
import firebase_admin

from firebase_admin import credentials, db
from google.colab import userdata

# Lê o JSON armazenado no Secret do Colab.
cred_info = json.loads(
    userdata.get("FIREBASE_SERVICE_ACCOUNT_JSON")
)

# Cria a credencial administrativa.
cred = credentials.Certificate(cred_info)

# Inicializa o Firebase Admin SDK usando o seu banco.
firebase_admin.initialize_app(
    cred,
    {"databaseURL": FIREBASE_URL}
)
```

Como o gerador usa o **Admin SDK**, ele consegue escrever no seu banco mesmo que as regras públicas tenham:

```json
".write": false
```

Isso é intencional.

---

## 9. Onde os dados são publicados

O publicador escreve no nó:

```text
/oficina/live
```

A lógica é equivalente a:

```python
ref = db.reference("oficina/live")
ref.set(pacote)
```

Cada nova publicação substitui o pacote anterior.

Isso é adequado para a oficina porque o objetivo é disponibilizar o **estado mais recente do sinal**, e não criar um histórico infinito.

---

## 10. Executar o gerador

Execute as células do notebook na ordem.

O notebook deverá:

1. instalar/importar as bibliotecas necessárias;
2. carregar o Secret;
3. conectar ao seu Firebase;
4. gerar sinais sintéticos;
5. montar um pacote de dados;
6. publicar esse pacote em:

```text
/oficina/live
```

Quando o gerador estiver funcionando, abra:

**Firebase → Realtime Database → Data**

Você deverá ver uma estrutura semelhante a:

```text
oficina
└── live
    ├── ecg
    ├── ppg_ir
    ├── ppg_red
    ├── fs
    ├── n
    ├── sample_start
    ├── seq
    ├── session_id
    ├── source
    └── timestamp_pub
```

Os valores exatos dependem da versão do gerador.

---

## 11. Testar com os notebooks clientes

Nos notebooks clientes, localize a variável:

```python
FIREBASE_URL = "..."
```

e substitua pelo endereço do **seu** Realtime Database.

Exemplo:

```python
FIREBASE_URL = "https://meu-projeto-default-rtdb.firebaseio.com"
```

Os clientes utilizam leitura HTTP e, em alguns checkpoints, **SSE — Server-Sent Events**.

Não é necessário adicionar credenciais aos clientes porque as regras permitem leitura pública em:

```text
/oficina/live
```

---

## 12. O que é SSE neste exercício?

SSE significa:

```text
Server-Sent Events
```

É uma forma de manter uma conexão HTTP aberta para que o servidor envie atualizações ao cliente quando os dados mudam.

Na oficina, isso permite que o notebook do aluno receba novos pacotes publicados no Firebase sem precisar executar sucessivos `GET` manualmente.

Fluxo simplificado:

```text
Gerador
   |
   | publica novo pacote
   v
Firebase
   |
   | evento SSE
   v
Notebook cliente
```

---

## 13. Posso deixar o gerador funcionando?

Sim, enquanto o ambiente do Colab permanecer ativo.

Porém, o Google Colab **não deve ser tratado como um servidor permanente**.

A sessão pode ser encerrada depois de algum tempo ou por inatividade/limites do ambiente.

Para exercícios e testes, isso não é um problema.

Quando o gerador parar:

- o último pacote continua armazenado no Firebase;
- uma leitura comum ainda retorna esse pacote;
- não haverá novos eventos em tempo real até o gerador ser iniciado novamente.

---

## 14. Como parar o gerador

Se o notebook estiver executando um laço contínuo:

- use o botão **Interromper execução** do Colab; ou
- interrompa a célula em execução.

O último pacote publicado permanecerá no Firebase.

---

## 15. Como apagar os dados de teste

No Firebase:

1. abra **Realtime Database → Data**;
2. localize:

```text
/oficina
```

ou:

```text
/oficina/live
```

3. use a opção de remoção.

Você também pode apagar o nó programaticamente com o Admin SDK:

```python
db.reference("oficina/live").delete()
```

Use essa operação com cuidado.

---

## 16. Como recriar o banco depois

Como o gerador sempre escreve a estrutura completa de:

```text
/oficina/live
```

não é necessário criar manualmente todos os campos.

Depois de criar um novo Realtime Database:

1. configure as regras;
2. gere uma nova conta de serviço;
3. atualize o Secret no Colab;
4. altere `FIREBASE_URL`;
5. execute novamente o gerador.

O primeiro pacote publicado recriará automaticamente o nó:

```text
/oficina/live
```

---

## 17. Erros comuns

### `SecretNotFoundError` ou erro ao obter o Secret

Confira se o nome foi escrito exatamente como:

```text
FIREBASE_SERVICE_ACCOUNT_JSON
```

e se o notebook tem permissão para acessar o Secret.

---

### Erro ao interpretar o JSON

Confira se você copiou o conteúdo completo do arquivo da conta de serviço.

O Secret deve começar com:

```text
{
```

e terminar com:

```text
}
```

---

### `Permission denied` no publicador

Se o publicador estiver corretamente usando o Firebase Admin SDK, revise:

- a conta de serviço;
- o projeto ao qual ela pertence;
- a URL do banco;
- a inicialização do Admin SDK.

Não é necessário mudar as regras para `".write": true`.

---

### O cliente recebe `Permission denied`

Confira se a regra:

```json
"oficina": {
  "live": {
    ".read": true
  }
}
```

foi publicada.

---

### O cliente não encontra dados

Confira:

1. se o gerador publicou pelo menos um pacote;
2. se o caminho usado é:

```text
/oficina/live
```

3. se gerador e cliente apontam para o mesmo `FIREBASE_URL`.

---

## 18. Segurança

Para este exercício:

- os sinais são sintéticos;
- não há dados reais de pacientes;
- a leitura pública é limitada ao nó `/oficina/live`;
- a escrita pública fica desabilitada;
- somente o gerador usa credenciais administrativas.

Mesmo em um projeto de teste, não compartilhe sua chave privada.

Em uma aplicação clínica real, seriam necessárias medidas adicionais de:

- autenticação de usuários e dispositivos;
- autorização por perfil;
- criptografia;
- registro de acessos;
- proteção e gestão de credenciais;
- políticas de retenção;
- conformidade com requisitos de privacidade e segurança aplicáveis.

A configuração deste tutorial tem finalidade **didática**.

---

## 19. Resumo

Para usar o gerador com seu próprio Firebase:

```text
1. Criar projeto no Firebase
        ↓
2. Criar Realtime Database
        ↓
3. Aplicar regras:
   leitura em /oficina/live
   escrita pública bloqueada
        ↓
4. Gerar conta de serviço
        ↓
5. Criar no Colab o Secret
   FIREBASE_SERVICE_ACCOUNT_JSON
        ↓
6. Colocar sua FIREBASE_URL no gerador
        ↓
7. Executar o publicador
        ↓
8. Colocar a mesma FIREBASE_URL
   nos notebooks clientes
        ↓
9. Testar GET e SSE
```

Com isso, todo o exercício passa a utilizar **exclusivamente o seu próprio projeto Firebase**.
