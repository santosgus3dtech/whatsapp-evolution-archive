# Operação

Esta página descreve a stack genérica do repositório. Use apenas uma instância e dados sob sua responsabilidade. Vincular, reconectar e alterar configuração de uma instância deve ser uma decisão explícita do operador.

## Instância e captura

O painel solicita a preparação da instância antes do vínculo. Quando o nome não existe na Evolution, cria uma instância `WHATSAPP-BAILEYS`, solicita histórico disponível e configura webhook em `ARCHIVE_INTERNAL_URL/webhook/evolution`, com `X-Webhook-Secret`. Não solicita leitura automática de mensagens/status nem mídia em base64.

Quando a instância já existe, retorna `preserved: true` e `webhook_configured: null`. Isso significa **configuração preservada**, não confirmação de que o webhook existente aponta para o arquivador. O setup não substitui webhook, sessão ou parâmetros de uma instância existente.

Para reutilizar uma instância, o operador deve conferir sua configuração na Evolution: URL alcançável, segredo no cabeçalho, eventos de mensagens e conexão, e base64 desativado. Eventos suportados pelo setup são `MESSAGES_SET`, `MESSAGES_UPSERT`, `MESSAGES_UPDATE`, `MESSAGES_EDITED`, `MESSAGES_DELETE`, `SEND_MESSAGE` e `CONNECTION_UPDATE`. Um webhook incorreto impede a captura ao vivo; a reconciliação ainda pode recuperar mensagens que a Evolution conserve.

O QR de vínculo é apresentado ao usuário autenticado e não é persistido pelo arquivador. Trate o QR e códigos de pareamento como privados. Vincular a conta cria uma sessão de dispositivo na integração; a disponibilidade de histórico depende do que ela consegue sincronizar.

## Verificar o serviço

Na raiz do repositório:

```powershell
docker compose --env-file .env -f deploy/docker/compose.yml ps
Invoke-RestMethod http://127.0.0.1:8097/healthz
```

`/healthz` responde `200` com `status: ok` quando o SQLite pode ser consultado e há a reserva mínima de espaço. Responde `503` quando o arquivo está degradado. Esse teste não confirma a conexão com o WhatsApp nem a completude da captura.

Entre no painel para verificar Conexão, Histórico e a indicação de espaço. `/api/status` exige autenticação e informa contagens, estado observado, captura inicial, cobertura e progresso. O backend consulta o estado da Evolution periodicamente; uma indicação antiga pode demorar até o próximo intervalo para mudar.

Confira a captura com um evento de teste controlado, sem utilizar dados pessoais em testes públicos. Uma mensagem já existente não deve criar uma nova cópia quando chega novamente. O comando de testes do README cobre esse comportamento com dados sintéticos.

## Importação, interrupções e retomada

“Importação concluída” significa que a consulta ao conjunto disponibilizado pela Evolution terminou naquela passagem. O início/fim dos registros não comprovam o histórico completo anterior. O serviço mantém a cobertura como não verificada.

Uma tentativa interrompida conserva o checkpoint e pode retomar com uma página de sobreposição. Uma tentativa que atinge o limite fica `limited`; a seguinte continua a passagem. Se o tamanho de página mudou, a passagem volta ao início. Uma passagem concluída é seguida por outra completa, para lidar com deslocamentos de paginação.

O progresso conta registros processados, inclusive duplicatas relidas. Não interprete esse número como total de novas mensagens inseridas. Dados que a Evolution não possui ou não retorna não podem ser recuperados pelo arquivador.

| Sinal ou código | Verificação necessária |
| --- | --- |
| `evolution_unreachable` | Endereço, resolução de nome e conectividade entre os serviços |
| `evolution_http_error`, status `401`/`403` | Correspondência e validade da chave da Evolution |
| `history_page_limit` | Limite por tentativa; aguarde a rotina ou solicite retomada |
| `history_invalid_records` ou `evolution_invalid_history` | Contrato/resposta da Evolution; mantenha o checkpoint para tentar novamente |
| `history_page_mismatch`, `history_empty_page`, `history_repeated_page` | Paginação inconsistente; investigue a resposta upstream antes de assumir cobertura |
| `storage_below_minimum` | Espaço livre no volume do arquivador |
| `service_restarted` ou `service_stopped` | Serviço interrompido; a próxima tentativa pode retomar |
| `panel_not_built` | Build do painel ausente no diretório estático |
| `origin_not_allowed` | Origem/prefixo/proxy configurados com o endereço exato do navegador |

A rotina automática começa após três segundos e repete a tentativa a cada cinco minutos por padrão. Há apenas uma reconciliação ativa por processo. Ela não pareia ou reconecta automaticamente o WhatsApp.

## Espaço e conservação dos dados

Quando o volume de dados tem menos de 2 GiB livres, o serviço bloqueia gravações de captura/importação e sinaliza degradação. Um webhook nessa situação recebe `503`; o arquivador não promete que o emissor tentará novamente. Depois de recuperar espaço, acompanhe a reconciliação e a cobertura disponível.

O Compose conserva quatro volumes: `archive-data`, `postgres-data`, `redis-data` e `evolution-instances`, com prefixo do projeto Docker. O primeiro contém o SQLite/cache; os demais pertencem à integração e sua sessão. Não há política automática de retenção ou exportação das mensagens do arquivo.

Planeje backups privados desses volumes e do `.env`. Faça backup consistente do SQLite com a API de backup do SQLite ou com o serviço parado; copiar somente `archive.sqlite3` durante uma gravação pode omitir dados presentes no WAL. Use mecanismos apropriados para PostgreSQL e, para um snapshot de todos os volumes, interrompa as gravações da stack. Valide a restauração em ambiente separado antes de depender do backup.

Para parar os serviços preservando os volumes:

```powershell
docker compose --env-file .env -f deploy/docker/compose.yml stop
```

Para iniciar novamente:

```powershell
docker compose --env-file .env -f deploy/docker/compose.yml start
```

Não remova os volumes nem use `down -v` como procedimento de atualização: isso remove o arquivo e dados de sessão. Backups, bancos, mídias, logs, QR e configurações reais devem permanecer fora do Git e de tickets públicos.

## Atualizações

Conserve as credenciais e os volumes existentes. Faça um backup verificado, revise alterações de dependências/configuração e os avisos de terceiros, então reconstrua o serviço do arquivador:

```powershell
docker compose --env-file .env -f deploy/docker/compose.yml up -d --build archive
docker compose --env-file .env -f deploy/docker/compose.yml ps
Invoke-RestMethod http://127.0.0.1:8097/healthz
```

Mudanças de imagem da Evolution ou banco precisam de revisão própria de compatibilidade e restauração. Alterar somente `POSTGRES_PASSWORD` no `.env` não troca a senha de um PostgreSQL já inicializado. Alterar a chave da Evolution exige que cliente e serviço correspondam. Não gere novamente a configuração inicial para atualizar uma instalação.

## Interface e privacidade

“Novas mensagens” identifica entradas recebidas que o arquivo classifica como novas e ainda não vistas localmente. O estado de visto no painel é compartilhado e não confirma a leitura no WhatsApp. Favoritos, etiquetas e arquivamento também pertencem ao arquivo; uma conversa arquivada continua consultável na aba Arquivadas e na busca global.

O cache de fotos de perfil pode falhar por indisponibilidade, permissões upstream ou limites. Nesse caso o painel usa uma representação alternativa; a ausência de foto não indica erro no arquivo de mensagens.

Compartilhe com outro usuário somente se ele puder acessar todas as conversas e alterar o estado local. Não há uma conta restrita a leitura ou a uma única conversa. Ao relatar um problema publicamente, use exemplos sintéticos e códigos de erro; mantenha conteúdo real, identificadores, cabeçalhos de autenticação e logs operacionais em ambiente privado.
