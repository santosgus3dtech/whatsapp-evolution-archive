# Avisos de terceiros

Este arquivo documenta componentes externos usados na distribuição técnica de Whatsapp Evolution Manager. A licença do código próprio permanece **pendente de definição pelo titular**. Estes avisos não escolhem uma licença para o projeto nem atribuem a terceiros a autoria do código próprio. Os termos e direitos de cada componente continuam nos respectivos arquivos integrais abaixo.

Inventário conferido em 13/10/2026 a partir de `apps/panel/package-lock.json`, `archive_service/requirements.lock` e dos avisos dos artefatos das mesmas versões. Não se incluem `node_modules`, ambientes Python, binários de dependências, bancos, sessões, mensagens ou mídias privadas neste repositório. A pasta de referência `evolution-manager-main` e o ZIP original estão excluídos.

## Frontend e ferramentas de build

O navegador recebe componentes Vue, ícones Lucide e arquivos de fonte Manrope/Space Grotesk quando o painel é compilado. Os avisos completos de Vue/MIT, Lucide/ISC e das partes Feather/MIT, bem como as duas licenças SIL Open Font License 1.1, devem acompanhar uma distribuição compilada. As fontes não foram modificadas. O copyright dos projetos Manrope e Space Grotesk é preservado nos textos OFL.

A coluna de uso segue a declaração de dependências do lockfile; não afirma que toda dependência transitiva esteja presente no JavaScript final. Ferramentas Vite, Rolldown e Lightning CSS são utilizadas no build. Vite inclui outros avisos de código incorporado em seu `LICENSE.md`; esse arquivo foi preservado integralmente. Rolldown inclui `THIRD-PARTY-LICENSE`, também preservado. Os termos MPL de Lightning CSS são mantidos, sem alegar que se aplicam automaticamente ao código próprio.

As variantes opcionais para outras plataformas permanecem no lockfile para instalação reproduzível. Quando não havia um texto próprio disponível no artefato local, a tabela aponta explicitamente para os avisos comuns do mesmo projeto/versão. Nenhum binário dessas variantes é distribuído aqui.

| Pacote | Versão fixada | Licença declarada | Uso | Avisos integrais | Origem do texto |
| --- | --- | --- | --- | --- | --- |
| @babel/helper-string-parser | 7.29.7 | MIT | frontend (transitiva) | [babel-helper-string-parser-7.29.7-LICENSE.txt](licenses/npm/babel-helper-string-parser-7.29.7-LICENSE.txt) | artefato instalado da versão fixada |
| @babel/helper-validator-identifier | 7.29.7 | MIT | frontend (transitiva) | [babel-helper-validator-identifier-7.29.7-LICENSE.txt](licenses/npm/babel-helper-validator-identifier-7.29.7-LICENSE.txt) | artefato instalado da versão fixada |
| @babel/parser | 7.29.9 | MIT | frontend (transitiva) | [babel-parser-7.29.9-LICENSE.txt](licenses/npm/babel-parser-7.29.9-LICENSE.txt) | artefato instalado da versão fixada |
| @babel/types | 7.29.8 | MIT | frontend (transitiva) | [babel-types-7.29.8-LICENSE.txt](licenses/npm/babel-types-7.29.8-LICENSE.txt) | artefato instalado da versão fixada |
| @fontsource/manrope | 5.3.0 | OFL-1.1 | frontend (direta) | [fontsource-manrope-5.3.0-LICENSE.txt](licenses/npm/fontsource-manrope-5.3.0-LICENSE.txt) | artefato instalado da versão fixada |
| @fontsource/space-grotesk | 5.3.0 | OFL-1.1 | frontend (direta) | [fontsource-space-grotesk-5.3.0-LICENSE.txt](licenses/npm/fontsource-space-grotesk-5.3.0-LICENSE.txt) | artefato instalado da versão fixada |
| @jridgewell/sourcemap-codec | 1.6.0 | MIT | frontend (transitiva) | [jridgewell-sourcemap-codec-1.6.0-LICENSE.txt](licenses/npm/jridgewell-sourcemap-codec-1.6.0-LICENSE.txt) | artefato instalado da versão fixada |
| @oxc-project/types | 0.153.0 | MIT | build (transitiva) | [oxc-project-types-0.153.0-LICENSE.txt](licenses/npm/oxc-project-types-0.153.0-LICENSE.txt) | artefato instalado da versão fixada |
| @rolldown/binding-android-arm-eabi | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-android-arm64 | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-darwin-arm64 | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-darwin-x64 | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-freebsd-x64 | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-linux-arm-gnueabihf | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-linux-arm64-gnu | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-linux-arm64-musl | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-linux-ppc64-gnu | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-linux-s390x-gnu | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-linux-x64-gnu | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-linux-x64-musl | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-openharmony-arm64 | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-win32-arm64-msvc | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/binding-win32-x64-msvc | 1.2.13 | MIT | build (transitiva); opcional | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | aviso comum do projeto Rolldown; variante opcional sem aviso próprio no artefato local |
| @rolldown/pluginutils | 1.0.1 | MIT | build (transitiva) | [rolldown-pluginutils-1.0.1-LICENSE.txt](licenses/npm/rolldown-pluginutils-1.0.1-LICENSE.txt) | artefato instalado da versão fixada |
| @vitejs/plugin-vue | 6.0.10 | MIT | build (direta) | [vitejs-plugin-vue-6.0.10-LICENSE.txt](licenses/npm/vitejs-plugin-vue-6.0.10-LICENSE.txt) | artefato instalado da versão fixada |
| @vue/compiler-core | 3.5.44 | MIT | frontend (transitiva) | [vue-compiler-core-3.5.44-LICENSE.txt](licenses/npm/vue-compiler-core-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |
| @vue/compiler-dom | 3.5.44 | MIT | frontend (transitiva) | [vue-compiler-dom-3.5.44-LICENSE.txt](licenses/npm/vue-compiler-dom-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |
| @vue/compiler-sfc | 3.5.44 | MIT | frontend (transitiva) | [vue-compiler-sfc-3.5.44-LICENSE.txt](licenses/npm/vue-compiler-sfc-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |
| @vue/compiler-ssr | 3.5.44 | MIT | frontend (transitiva) | [vue-compiler-ssr-3.5.44-LICENSE.txt](licenses/npm/vue-compiler-ssr-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |
| @vue/reactivity | 3.5.44 | MIT | frontend (transitiva) | [vue-reactivity-3.5.44-LICENSE.txt](licenses/npm/vue-reactivity-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |
| @vue/runtime-core | 3.5.44 | MIT | frontend (transitiva) | [vue-runtime-core-3.5.44-LICENSE.txt](licenses/npm/vue-runtime-core-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |
| @vue/runtime-dom | 3.5.44 | MIT | frontend (transitiva) | [vue-runtime-dom-3.5.44-LICENSE.txt](licenses/npm/vue-runtime-dom-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |
| @vue/server-renderer | 3.5.44 | MIT | frontend (transitiva) | [vue-server-renderer-3.5.44-LICENSE.txt](licenses/npm/vue-server-renderer-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |
| @vue/shared | 3.5.44 | MIT | frontend (transitiva) | [vue-shared-3.5.44-LICENSE.txt](licenses/npm/vue-shared-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |
| csstype | 3.2.3 | MIT | frontend (transitiva) | [csstype-3.2.3-LICENSE.txt](licenses/npm/csstype-3.2.3-LICENSE.txt) | artefato instalado da versão fixada |
| detect-libc | 2.1.2 | Apache-2.0 | build (transitiva) | [detect-libc-2.1.2-LICENSE.txt](licenses/npm/detect-libc-2.1.2-LICENSE.txt) | artefato instalado da versão fixada |
| entities | 7.0.1 | BSD-2-Clause | frontend (transitiva) | [entities-7.0.1-LICENSE.txt](licenses/npm/entities-7.0.1-LICENSE.txt) | artefato instalado da versão fixada |
| estree-walker | 2.0.2 | MIT | frontend (transitiva) | [estree-walker-2.0.2-LICENSE.txt](licenses/npm/estree-walker-2.0.2-LICENSE.txt) | artefato instalado da versão fixada |
| fdir | 6.5.0 | MIT | build (transitiva) | [fdir-6.5.0-LICENSE.txt](licenses/npm/fdir-6.5.0-LICENSE.txt) | artefato instalado da versão fixada |
| fsevents | 2.3.3 | MIT | build (transitiva); opcional | [fsevents-2.3.3-LICENSE.txt](licenses/npm/fsevents-2.3.3-LICENSE.txt) | licença do tag oficial v2.3.3; variante opcional não instalada neste sistema |
| lightningcss | 1.33.0 | MPL-2.0 | build (transitiva) | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | artefato instalado da versão fixada |
| lightningcss-android-arm64 | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-darwin-arm64 | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-darwin-x64 | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-freebsd-x64 | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-linux-arm-gnueabihf | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-linux-arm64-gnu | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-linux-arm64-musl | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-linux-x64-gnu | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-linux-x64-musl | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-win32-arm64-msvc | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-1.33.0-LICENSE.txt](licenses/npm/lightningcss-1.33.0-LICENSE.txt) | licença comum do Lightning CSS; variante opcional não instalada neste sistema |
| lightningcss-win32-x64-msvc | 1.33.0 | MPL-2.0 | build (transitiva); opcional | [lightningcss-win32-x64-msvc-1.33.0-LICENSE.txt](licenses/npm/lightningcss-win32-x64-msvc-1.33.0-LICENSE.txt) | artefato instalado da versão fixada |
| lucide-vue-next | 1.0.0 | ISC + MIT (Feather) | frontend (direta) | [lucide-vue-next-1.0.0-LICENSE.txt](licenses/npm/lucide-vue-next-1.0.0-LICENSE.txt) | artefato instalado da versão fixada |
| magic-string | 0.30.21 | MIT | frontend (transitiva) | [magic-string-0.30.21-LICENSE.txt](licenses/npm/magic-string-0.30.21-LICENSE.txt) | artefato instalado da versão fixada |
| nanoid | 3.3.20 | MIT | frontend (transitiva) | [nanoid-3.3.20-LICENSE.txt](licenses/npm/nanoid-3.3.20-LICENSE.txt) | artefato instalado da versão fixada |
| picocolors | 1.1.1 | ISC | frontend (transitiva) | [picocolors-1.1.1-LICENSE.txt](licenses/npm/picocolors-1.1.1-LICENSE.txt) | artefato instalado da versão fixada |
| picomatch | 4.0.7 | MIT | build (transitiva) | [picomatch-4.0.7-LICENSE.txt](licenses/npm/picomatch-4.0.7-LICENSE.txt) | artefato instalado da versão fixada |
| postcss | 8.5.30 | MIT | frontend (transitiva) | [postcss-8.5.30-LICENSE.txt](licenses/npm/postcss-8.5.30-LICENSE.txt) | artefato instalado da versão fixada |
| rolldown | 1.2.13 | MIT | build (transitiva) | [rolldown-1.2.13-LICENSE.txt](licenses/npm/rolldown-1.2.13-LICENSE.txt), [rolldown-1.2.13-THIRD-PARTY-LICENSE.txt](licenses/npm/rolldown-1.2.13-THIRD-PARTY-LICENSE.txt) | artefato instalado da versão fixada |
| source-map-js | 1.2.2 | BSD-3-Clause | frontend (transitiva) | [source-map-js-1.2.2-LICENSE.txt](licenses/npm/source-map-js-1.2.2-LICENSE.txt) | artefato instalado da versão fixada |
| tinyglobby | 0.2.17 | MIT | build (transitiva) | [tinyglobby-0.2.17-LICENSE.txt](licenses/npm/tinyglobby-0.2.17-LICENSE.txt) | artefato instalado da versão fixada |
| vite | 8.3.4 | MIT | build (direta) | [vite-8.3.4-LICENSE.md](licenses/npm/vite-8.3.4-LICENSE.md) | artefato instalado da versão fixada |
| vue | 3.5.44 | MIT | frontend (direta) | [vue-3.5.44-LICENSE.txt](licenses/npm/vue-3.5.44-LICENSE.txt) | artefato instalado da versão fixada |

## Runtime Python

Os pacotes abaixo são instalados das versões e hashes do lockfile. Seus arquivos de licença foram preservados dos metadados dos artefatos correspondentes. As páginas do PyPI listadas fornecem os arquivos da versão, inclusive a distribuição fonte quando publicada. Pacotes de testes presentes no ambiente local não foram adicionados a este inventário de runtime.

Certifi contém certificados derivados da coleção Mozilla e seu aviso refere-se à MPL 2.0. O [texto integral da MPL 2.0](licenses/MPL-2.0.txt) acompanha o aviso do pacote. Preserve os avisos e a disponibilidade do código fonte correspondente ao distribuir o pacote; consulte a página da versão na tabela. OpenTelemetry API usa Apache 2.0; typing-extensions usa PSF 2.0. Nenhum pacote deste conjunto foi modificado por esta distribuição.

| Pacote | Versão fixada | Licença | Avisos integrais | Artefatos/fontes da versão |
| --- | --- | --- | --- | --- |
| annotated-doc | 0.0.5 | MIT | [annotated-doc-0.0.5-LICENSE.txt](licenses/python/annotated-doc-0.0.5-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/annotated-doc/0.0.5/#files) |
| annotated-types | 0.8.0 | MIT | [annotated-types-0.8.0-LICENSE.txt](licenses/python/annotated-types-0.8.0-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/annotated-types/0.8.0/#files) |
| anyio | 4.15.1 | MIT | [anyio-4.15.1-LICENSE.txt](licenses/python/anyio-4.15.1-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/anyio/4.15.1/#files) |
| certifi | 2026.7.22 | MPL-2.0 | [certifi-2026.7.22-LICENSE.txt](licenses/python/certifi-2026.7.22-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/certifi/2026.7.22/#files) |
| click | 8.5.0 | BSD-3-Clause | [click-8.5.0-LICENSE.txt](licenses/python/click-8.5.0-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/click/8.5.0/#files) |
| fastapi | 0.143.0 | MIT | [fastapi-0.143.0-LICENSE.txt](licenses/python/fastapi-0.143.0-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/fastapi/0.143.0/#files) |
| h11 | 0.16.0 | MIT | [h11-0.16.0-LICENSE.txt](licenses/python/h11-0.16.0-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/h11/0.16.0/#files) |
| httpcore | 1.0.9 | BSD-3-Clause | [httpcore-1.0.9-LICENSE.md](licenses/python/httpcore-1.0.9-LICENSE.md) | [PyPI da versão](https://pypi.org/project/httpcore/1.0.9/#files) |
| httpx | 0.28.1 | BSD-3-Clause | [httpx-0.28.1-LICENSE.md](licenses/python/httpx-0.28.1-LICENSE.md) | [PyPI da versão](https://pypi.org/project/httpx/0.28.1/#files) |
| idna | 3.20 | BSD-3-Clause | [idna-3.20-LICENSE.md](licenses/python/idna-3.20-LICENSE.md) | [PyPI da versão](https://pypi.org/project/idna/3.20/#files) |
| opentelemetry-api | 1.45.1 | Apache-2.0 | [opentelemetry-api-1.45.1-LICENSE.txt](licenses/python/opentelemetry-api-1.45.1-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/opentelemetry-api/1.45.1/#files) |
| pydantic | 2.14.1 | MIT | [pydantic-2.14.1-LICENSE.txt](licenses/python/pydantic-2.14.1-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/pydantic/2.14.1/#files) |
| pydantic-core | 2.50.1 | MIT | [pydantic-core-2.50.1-LICENSE.txt](licenses/python/pydantic-core-2.50.1-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/pydantic-core/2.50.1/#files) |
| starlette | 1.8.0 | BSD-3-Clause | [starlette-1.8.0-LICENSE.md](licenses/python/starlette-1.8.0-LICENSE.md) | [PyPI da versão](https://pypi.org/project/starlette/1.8.0/#files) |
| typing-extensions | 4.16.0 | PSF-2.0 | [typing-extensions-4.16.0-LICENSE.txt](licenses/python/typing-extensions-4.16.0-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/typing-extensions/4.16.0/#files) |
| typing-inspection | 0.4.4 | MIT | [typing-inspection-0.4.4-LICENSE.txt](licenses/python/typing-inspection-0.4.4-LICENSE.txt) | [PyPI da versão](https://pypi.org/project/typing-inspection/0.4.4/#files) |
| uvicorn | 0.54.0 | BSD-3-Clause | [uvicorn-0.54.0-LICENSE.md](licenses/python/uvicorn-0.54.0-LICENSE.md) | [PyPI da versão](https://pypi.org/project/uvicorn/0.54.0/#files) |

## Evolution API externa

O serviço integra-se por HTTP à Evolution API 2.3.7. A imagem externa é obtida separadamente pelo operador; seu binário e seu código fonte não são incluídos neste repositório. [Projeto oficial](https://github.com/evolution-foundation/evolution-api), [fonte da versão 2.3.7](https://github.com/evolution-foundation/evolution-api/tree/2.3.7) e [licença exata dessa versão](https://github.com/evolution-foundation/evolution-api/blob/2.3.7/LICENSE).

O [texto original da licença](licenses/external/evolution-api-2.3.7-LICENSE.txt) declara Apache License 2.0 com condições adicionais; o [texto da Apache 2.0](licenses/Apache-2.0.txt) também está incluído. Não se deve descrever essa licença como Apache 2.0 sem mencionar as condições adicionais. A versão exige aviso claro de uso da Evolution API, visível aos administradores e acessível pela documentação ou configurações. Ao usar componentes do frontend upstream, há condições de preservação de logo e copyright. Este painel tem frontend próprio; a documentação e a interface devem conservar o aviso da integração.

Evolution Manager 0.4.13 foi consultado como referência local e está excluído desta distribuição. Seu [upstream](https://github.com/evolution-foundation/evolution-manager) declara [MIT, copyright 2023 Gabriel Pastori](https://github.com/evolution-foundation/evolution-manager/blob/main/LICENSE.md). Essa licença não é adotada como licença do código próprio. Se uma distribuição futura incorporar cópias ou porções substanciais do Manager, deverá incluir seus avisos integrais.

## Empacotamento e distribuição

Ao publicar o código, conserve este arquivo e a pasta `licenses/`. Ao gerar o container do arquivador, copie ambos para um local estável, por exemplo `/app/THIRD_PARTY_NOTICES.md` e `/app/licenses/`, preservando também os metadados `.dist-info` que o instalador Python deixa em `site-packages`.

Como o build do painel gera e distribui fontes e JavaScript de terceiros, os avisos precisam acompanhar seus arquivos também. Uma opção para o Dockerfile é copiar a pasta `licenses/` e este inventário para a pasta estática do painel depois do build. A interface pode fornecer um link persistente para os avisos. Exemplos de linhas de empacotamento:

```dockerfile
COPY THIRD_PARTY_NOTICES.md /app/THIRD_PARTY_NOTICES.md
COPY licenses/ /app/licenses/
COPY THIRD_PARTY_NOTICES.md /app/apps/panel/dist/THIRD_PARTY_NOTICES.md
COPY licenses/ /app/apps/panel/dist/licenses/
```

Imagens externas Node, Python, Evolution API, PostgreSQL e Redis possuem seus próprios componentes e termos; não foram reconstruídas nem incorporadas como binários neste repositório. Quem redistribuir essas imagens deve conservar seus avisos e verificar os componentes efetivamente presentes. Este inventário cobre os lockfiles da aplicação e os avisos citados; não é um inventário de todos os pacotes do sistema operacional das imagens externas.

## Limites da revisão

Este inventário não determina titularidade de marcas, não concede licença sobre o código próprio e não certifica todas as dependências internas de imagens externas. As versões fixadas são a base da revisão; alterações de dependências ou redistribuição de binários exigem atualizar os avisos. Para variantes opcionais não instaladas, os textos comuns apontados não substituem a conferência de eventuais avisos adicionais quando o artefato for efetivamente redistribuído.
