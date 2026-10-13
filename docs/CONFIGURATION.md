# Configuração

Os comandos desta página usam PowerShell, a partir da raiz do checkout. A configuração privada não acompanha o repositório. O `.env.example` é somente um modelo, e o Compose exige os campos obrigatórios preenchidos.

## Configuração inicial

Uma opção é copiar `.env.example` para `.env` e preencher os segredos com um gerador seguro. `DATABASE_CONNECTION_URI` deve usar a mesma credencial de PostgreSQL definida em `POSTGRES_PASSWORD`.

O exemplo abaixo cria a configuração inicial a partir do modelo sem exibir os segredos. Usa os valores padrão `POSTGRES_USER=evolution` e `POSTGRES_DB=evolution`. Recusa um `.env` existente para evitar a troca acidental de credenciais:

```powershell
$envPath = Join-Path (Get-Location) '.env'
if (Test-Path -LiteralPath $envPath) {
    throw '.env já existe; mantenha as credenciais atuais e edite somente os campos necessários.'
}
$template = Get-Content -LiteralPath '.env.example' -Raw
$generated = @{}
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    foreach ($name in @('ARCHIVE_PASSWORD', 'WEBHOOK_SECRET', 'EVOLUTION_API_KEY', 'POSTGRES_PASSWORD')) {
        $bytes = New-Object byte[] 32
        $rng.GetBytes($bytes)
        $generated[$name] = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
        $pattern = '(?m)^' + [regex]::Escape($name) + '=\r?$'
        $template = [regex]::Replace($template, $pattern, $name + '=' + $generated[$name])
    }
    $uri = 'postgresql://evolution:' + $generated['POSTGRES_PASSWORD'] + '@postgres:5432/evolution?schema=public'
    $template = [regex]::Replace($template, '(?m)^DATABASE_CONNECTION_URI=\r?$', 'DATABASE_CONNECTION_URI=' + $uri)
    [IO.File]::WriteAllText($envPath, $template, [Text.UTF8Encoding]::new($false))
} finally {
    $rng.Dispose()
    Remove-Variable generated, bytes, uri, template -ErrorAction SilentlyContinue
}
```

Guarde a senha de `ARCHIVE_PASSWORD` em seu gerenciador de senhas para entrar no painel. Restrinja o acesso ao `.env` ao operador da instalação. Esse arquivo é ignorado pelo Git, mas continua sendo um arquivo privado no disco.

Se construir a URI manualmente, aplique codificação de URL ao usuário e à senha, especialmente para caracteres como `@`, `:`, `/`, `#` e `%`. A estrutura é `postgresql://USUARIO:SENHA_CODIFICADA@postgres:5432/BANCO?schema=public`. O exemplo automático usa uma senha formada apenas por caracteres seguros para esse trecho da URI.

Valide o Compose sem mostrar a configuração expandida:

```powershell
docker compose --env-file .env -f deploy/docker/compose.yml config --quiet
```

Não publique a saída expandida de `docker compose config`: ela contém as credenciais substituídas.

## Variáveis principais

| Variável | Uso |
| --- | --- |
| `ARCHIVE_USERNAME` | Conta principal de acesso ao painel; obrigatória |
| `ARCHIVE_PASSWORD` | Senha privada da conta principal; obrigatória |
| `WEBHOOK_SECRET` | Segredo independente para o cabeçalho `X-Webhook-Secret`; obrigatório |
| `EVOLUTION_API_KEY` | Chave privada da Evolution; obrigatória e compartilhada entre Evolution/arquivador no Compose |
| `EVOLUTION_INSTANCE` | Nome da única instância; letras, números, `_` ou `-`; exemplo `archive-demo` |
| `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD` | Inicialização do banco da Evolution |
| `DATABASE_CONNECTION_URI` | URI PostgreSQL da Evolution; deve corresponder aos valores acima |
| `ARCHIVE_PORT` | Porta publicada do painel; padrão `8097` |
| `ARCHIVE_BIND_ADDRESS` | Endereço de publicação; padrão `127.0.0.1` |
| `ARCHIVE_PUBLIC_ORIGIN` | Origem exata do navegador; deixe vazia no acesso local padrão |
| `ARCHIVE_PUBLIC_PATH` | Prefixo de URL; `/` ou, por exemplo, `/archive` |
| `ARCHIVE_IMAGE_TAG` | Identificador local da imagem construída |
| `EVOLUTION_API_URL` | Endereço alcançável da Evolution pelo backend; no Compose é `http://evolution:8080` |
| `ARCHIVE_INTERNAL_URL` | Endereço alcançável do backend pela Evolution, usado ao criar o webhook; no Compose é `http://archive:8000` |
| `ARCHIVE_DATA_DIR` | Diretório privado de SQLite/cache; no container é `/data` |
| `ARCHIVE_STATIC_DIR` | Painel compilado; no container é `/app/apps/panel/dist` |
| `ARCHIVE_USERS_FILE` | Caminho opcional do JSON privado de contas adicionais, visto pelo processo Python |

O Compose define `EVOLUTION_API_URL`, `ARCHIVE_INTERNAL_URL`, `ARCHIVE_DATA_DIR` e `ARCHIVE_STATIC_DIR` diretamente. Alterar esses valores no `.env` só muda o processo Python local; para mudar a stack Docker é necessário um override de Compose revisado. `ARCHIVE_USERS_FILE` também precisa de um mount e uma entrada `environment` no container.

O código Python lê `ARCHIVE_SYNC_INTERVAL_SECONDS` (padrão `300`), `ARCHIVE_SYNC_MAX_PAGES` (padrão `1000`, intervalo permitido `1..10000`) e `ARCHIVE_SYNC_PAGE_SIZE` (padrão `100`, intervalo `1..1000`). O Compose não expõe essas opções no modelo: acrescente-as a `archive.environment` em um override se precisar ajustá-las. O limite de páginas vale por tentativa, com uma página de sobreposição ao retomar.

A reserva mínima de 2 GiB de espaço, duração padrão de sessão de 12 horas e limite de corpo do webhook de 16 MiB são valores do código; não há variáveis de ambiente publicadas para alterá-los.

## Acesso por HTTPS e prefixo

Para um proxy próprio, configure uma origem exata sem caminho, usuário, query ou fragmento. Exemplo fictício:

```dotenv
ARCHIVE_PUBLIC_ORIGIN=https://archive.example.com
ARCHIVE_PUBLIC_PATH=/archive
```

Recompile o container após alterar `ARCHIVE_PUBLIC_PATH`: o prefixo também é utilizado no build do Vite. Abra a URL com `/archive/`. O proxy deve encaminhar o `Host` público e o caminho, manter o canal SSE aberto e desativar buffering/cache em `/archive/api/events`.

O backend exige HTTPS para uma origem pública explicitamente configurada. HTTP explícito só é aceito com endereço IP das faixas privadas RFC1918. Para `http://127.0.0.1:8097`, mantenha `ARCHIVE_PUBLIC_ORIGIN` vazia; a verificação usa a origem da requisição. Não use um domínio HTTP público como origem.

O Compose mantém o painel no loopback e deixa a publicação remota a cargo do operador. Se o proxy estiver em outro container ou máquina, sua conectividade e o endereço de bind precisam de configuração própria. Configure TLS e controle de acesso sem publicar PostgreSQL, Redis ou a chave da Evolution.

## Desenvolvimento local

Instale as dependências e compile o painel com os comandos do README. Para carregar `.env` pelo Uvicorn, instale explicitamente o suporte opcional:

```powershell
.venv/Scripts/python.exe -m pip install python-dotenv
```

Adapte `EVOLUTION_API_URL` e `ARCHIVE_INTERNAL_URL` no `.env`: os nomes `evolution` e `archive` são DNS da rede Docker, e não endereços acessíveis automaticamente pelo Python do host. A primeira URL deve apontar para sua Evolution de desenvolvimento; a segunda deve ser alcançável por ela para receber o webhook. O Compose padrão não publica a porta da Evolution no host.

Inicie o backend na raiz do checkout:

```powershell
.venv/Scripts/python.exe -m uvicorn archive_service.app:create_app --factory --env-file .env --host 127.0.0.1 --port 8000 --no-access-log
```

Use um único worker, como no comando acima. O bind `127.0.0.1` atende somente o host local. Se a Evolution estiver em um container ou outra máquina, o webhook precisa de encaminhamento ou de um bind/endereço alcançável por ela, com acesso controlado; definir `ARCHIVE_INTERNAL_URL` não cria essa conectividade.

Abra `http://127.0.0.1:8000/` para o painel compilado. Para o servidor Vite com recarga, execute em outro terminal:

```powershell
Set-Location apps/panel
npm run dev
```

O Vite publica em `http://127.0.0.1:5173` e encaminha `/api` e `/healthz` ao backend local. Mantenha a origem pública vazia nesse modo. Para desenvolvimento com prefixo, configure `VITE_BASE_URL` no ambiente do terminal do Vite e use o mesmo `ARCHIVE_PUBLIC_PATH` no backend.

## Contas adicionais opcionais

Contas adicionais não substituem a conta principal. O JSON precisa ter até 100 entradas, usuários únicos sem espaços nas bordas e diferentes de `ARCHIVE_USERNAME`; o arquivo é limitado a 1 MiB. Senhas adicionais são hashes scrypt, gerados por `archive_service.users.hash_password`.

Após criar o ambiente Python, este comando solicita uma senha sem eco e grava um arquivo privado novo. Não o execute sobre um diretório de contas existente sem revisar as entradas que pretende manter:

```powershell
.venv/Scripts/python.exe -c "import getpass,json; from pathlib import Path; from archive_service.users import hash_password; path=Path('.private/archive-users.json'); path.parent.mkdir(exist_ok=True); payload={'users':[{'username':'reviewer','password_hash':hash_password(getpass.getpass('Senha de reviewer: '))}]}; handle=path.open('x',encoding='utf-8'); handle.write(json.dumps(payload)); handle.close()"
```

O modo `x` recusa substituir um arquivo existente. Para execução local, defina `ARCHIVE_USERS_FILE=./.private/archive-users.json` no `.env`.

No Docker, crie um override privado em `deploy/docker/compose.users.yml` com:

```yaml
services:
  archive:
    environment:
      ARCHIVE_USERS_FILE: /run/archive-users.json
    volumes:
      - ../../.private/archive-users.json:/run/archive-users.json:ro
```

O caminho relativo é resolvido a partir de `deploy/docker/`, onde está o primeiro Compose. Garanta permissão de leitura do arquivo ao usuário `10001:10001` do container, sem deixá-lo disponível a outros usuários. Inclua o override nas operações:

```powershell
docker compose --env-file .env -f deploy/docker/compose.yml -f deploy/docker/compose.users.yml config --quiet
docker compose --env-file .env -f deploy/docker/compose.yml -f deploy/docker/compose.users.yml up -d
```

O override não contém a senha, mas o arquivo `.private/archive-users.json` é privado. Todas as contas continuam compartilhando o mesmo conteúdo e estado local; não há permissões de somente leitura.
