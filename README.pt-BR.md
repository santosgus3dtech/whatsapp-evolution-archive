# Whatsapp Evolution Manager

[README principal](README.md) · Português (Brasil)

Arquivo pessoal de mensagens disponibilizadas pela Evolution API, com serviço Python/FastAPI, armazenamento SQLite e painel Vue. O nome acima é técnico; o nome definitivo do produto permanece em definição.

O painel permite consultar conversas, buscar mensagens, acompanhar a importação disponível e organizar o arquivo local. Esta distribuição contém fonte e configuração genérica, sem mensagens, credenciais, sessões, fotos ou dados de uma instalação real.

## O que está disponível

- Conversas e mensagens com paginação e busca por texto ou legenda.
- Busca global por período, conversa, tipo e direção recebida/enviada.
- Favoritos, etiquetas e conversas arquivadas no painel.
- Indicador de mensagens recebidas ainda não vistas no arquivo.
- Captura por webhook e reconciliação periódica com o banco da Evolution API.
- Importação com checkpoint, retomada e deduplicação.
- Atualização do painel por eventos SSE persistidos.
- Fotos de perfil consultadas sob demanda, quando disponíveis, com cache privado limitado.
- Login por sessão; contas adicionais opcionais com senha armazenada como hash scrypt.

## Limites do arquivo

A integração **não comprova nem garante todo o histórico anterior do WhatsApp**. A aba Histórico mostra a primeira e a última mensagem disponíveis, o início da captura e o progresso da consulta. Uma consulta concluída à Evolution não comprova que todos os dados do telefone estejam disponíveis.

O serviço preserva textos, legendas e alguns metadados de mensagens. Não salva o conteúdo binário de fotos, vídeos, áudios, documentos ou stickers enviados nas conversas, nem acessa a coleção pessoal de stickers salvos. Fotos de perfil são um cache separado e limitado.

Não há envio de mensagens pelo painel. Mensagens enviadas por outros clientes podem aparecer quando a integração as disponibiliza. Marcar como visto, favoritar, etiquetar ou arquivar altera somente o arquivo local. O estado “arquivada no WhatsApp” permanece desconhecido quando a API não o informa.

Todos os usuários autenticados acessam a mesma instância e compartilham mensagens, estado de visto e preferências. Não há isolamento por usuário, papéis de acesso ou separação entre clientes.

## Instalação com Docker

Use Docker com Compose v2 e suporte a containers Linux `amd64`. O Compose inclui o arquivador, Evolution API 2.3.7, PostgreSQL e Redis; o Dockerfile compila o painel e instala as dependências Python fixadas por hash. Há limites de memória por serviço, além do consumo do build e do próprio Docker.

Execute os comandos a partir da raiz do repositório:

```powershell
git clone https://github.com/santosgus3dtech/whatsapp-evolution-archive.git
Set-Location whatsapp-evolution-archive
```

Crie a configuração privada seguindo [Configuração](docs/CONFIGURATION.md#configuração-inicial). O arquivo `.env.example` contém campos obrigatórios vazios; a aplicação não inicia sem preenchê-los.

```powershell
docker compose --env-file .env -f deploy/docker/compose.yml config --quiet
docker compose --env-file .env -f deploy/docker/compose.yml up -d --build
docker compose --env-file .env -f deploy/docker/compose.yml ps
Invoke-RestMethod http://127.0.0.1:8097/healthz
```

Abra [http://127.0.0.1:8097](http://127.0.0.1:8097) e entre com o usuário e a senha de `ARCHIVE_USERNAME` e `ARCHIVE_PASSWORD`. O painel é publicado apenas no endereço local por padrão; bancos e Evolution não têm portas publicadas pelo Compose.

Na aba Conexão, use **Vincular WhatsApp** para a instância escolhida. Para uma instância nova, o serviço configura os eventos e o webhook com segredo no cabeçalho, sem mídia em base64. Se a instância já existir, sua configuração é preservada: o serviço **não troca o webhook nem redefine a instância**. Veja [Operação](docs/OPERATIONS.md#instância-e-captura) antes de reutilizar uma instância.

Após o vínculo, a captura depende dos eventos entregues pela integração. A reconciliação consulta as mensagens já armazenadas na Evolution e tenta recuperar eventos que não chegaram por webhook. Use a aba Histórico para acompanhar a cobertura e solicitar a importação disponível.

Os dados ficam em volumes Docker nomeados. A configuração publicada não utiliza nem importa dados de outra instalação.

## Desenvolvimento e verificações

Para trabalhar fora do container, use Python 3.12+ e Node.js compatível com `apps/panel/package.json` (`>=22.12.0`). O container usa Python 3.12; a verificação local também utilizou Python 3.13. Os comandos abaixo usam PowerShell e criam um ambiente local:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install --require-hashes -r archive_service/requirements.lock
.venv/Scripts/python.exe -m pip install pytest==8.4.2
.venv/Scripts/python.exe -m pytest -q tests
Set-Location apps/panel
npm ci
npm run build
Set-Location ../..
```

Os testes usam dados sintéticos, clientes simulados e diretórios temporários. Cobrem ingestão, duplicatas, edições/exclusões recebidas, autenticação, CSRF, eventos, retomada de importação, preferências locais e cache de fotos. Eles não pareiam um telefone nem provam compatibilidade de uma instalação real do WhatsApp.

Para executar a aplicação localmente, configure os endereços acessíveis pelo processo Python, conforme [Desenvolvimento local](docs/CONFIGURATION.md#desenvolvimento-local). O `.env` não é carregado automaticamente pelo código Python.

## Documentação

- [Configuração](docs/CONFIGURATION.md): variáveis, segredos, acesso por HTTPS, execução local e usuários adicionais.
- [Arquitetura](docs/ARCHITECTURE.md): fluxo de dados, persistência, eventos e contratos principais.
- [Operação](docs/OPERATIONS.md): verificação de saúde, cobertura, erros e conservação dos dados.
- [Avisos de terceiros](THIRD_PARTY_NOTICES.md): componentes, versões e textos de licença preservados.

## Licença e atribuição

Esta aplicação utiliza a **Evolution API 2.3.7** como serviço externo. Consulte o [projeto oficial](https://github.com/evolution-foundation/evolution-api), a [licença exata da versão 2.3.7](https://github.com/evolution-foundation/evolution-api/blob/2.3.7/LICENSE), incluindo suas condições adicionais, e o texto preservado em [licenses/external/evolution-api-2.3.7-LICENSE.txt](licenses/external/evolution-api-2.3.7-LICENSE.txt).

A licença de reutilização do código próprio está pendente de escolha pelo titular. A disponibilidade pública não concede, por si só, permissão de redistribuição, modificação ou sublicenciamento. Veja [LICENSE.md](LICENSE.md). As dependências conservam suas próprias licenças e avisos; eles não definem a licença do código próprio.
