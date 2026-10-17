# Roteiro — Pokedex CLI

Especificação: `DOC-20261001-WA0022.pdf`. Regra: primeiro o MVP funcionando de ponta a ponta, depois melhorias.

**Como trabalhamos em cada etapa:** explicação da decisão de arquitetura (o quê e por quê) →
Claude implementa em partes pequenas → Bernardo acompanha e valida → perguntas de verificação
(foco em arquitetura e responsabilidades, não em sintaxe) → commit (com aprovação) → próxima etapa.

## Etapa 0 — Ambiente e Git
- [x] Criar este roteiro
- [x] Entender venv, `requirements.txt`, `pyproject.toml`, ruff e pytest
- [x] Criar `.venv` e instalar dependências (requests, pytest, ruff)
- [x] Configurar ruff e pytest no `pyproject.toml`
- [x] `git init`, `.gitignore`, primeiro commit

## Etapa 1 — Explorar a PokéAPI
- [x] Conceitos: HTTP, GET, status codes (200/404/5xx), JSON, REST
- [x] Explorar `/pokemon/pikachu` no navegador e com `requests`
- [x] Localizar no JSON: id, name, height, weight, types, abilities, stats
- [x] Explorar a paginação: `/pokemon?limit=20&offset=0`
- [x] Unidades: altura em decímetros, peso em hectogramas

## Etapa 2 — Model `Pokemon`
- [x] Dataclass `Pokemon` com type hints
- [x] `Pokemon.from_api_data(data)` (JSON → objeto)
- [x] Testes com pytest e fixture de JSON de exemplo

## Etapa 3 — Service `PokeApiClient` (caminho feliz)
- [x] Classe com `base_url`, `timeout` e `Session` injetada
- [x] `get_pokemon(name_or_id)` e normalização da entrada
- [x] `list_pokemon(limit, offset)` → `PokemonPage`
- [x] Testes com `Mock` (sem internet)

## Etapa 4 — Tratamento de erros
- [x] Exceções próprias: `PokeApiError`, `PokemonNotFoundError`, `ApiUnavailableError`, `InvalidResponseError`
- [x] Converter timeout, erro de conexão, 404, 5xx e JSON inválido
- [x] Testes com `pytest.raises`

## Etapa 5 — CLI: exibição e busca
- [x] `format_pokemon(pokemon) -> str` (função pura, com conversão de unidades)
- [x] Fluxo de busca com validação de entrada e mensagens de erro claras
- [x] Testes da formatação

## Etapa 6 — CLI: listagem com paginação
- [x] Loop com `n` / `p` / `q` e comando inválido
- [x] Limites: não voltar antes da primeira página nem passar da última

## Etapa 7 — Menu principal
- [x] Menu (1 Search / 2 List / 3 Exit) e opção inválida
- [x] `__main__.py` e `py -m pokedex`; Ctrl+C sai de forma limpa
- [x] Teste manual de ponta a ponta

## Etapa 8 — Acabamento e portfólio
- [x] `ruff check` / `ruff format` limpos e todos os testes passando
- [x] README em inglês (o que é, como rodar, como testar)
- [ ] Criar repositório público no GitHub (com aprovação) e fazer push  ← pendente: aguarda aprovação
- [x] Lista de melhorias futuras

## Verificação final
- [x] `pytest` passa sem acesso à internet
- [x] Buscar `pikachu` e `25`
- [x] Buscar `abc123` → "Pokémon not found."
- [x] Opção de menu inválida tratada
- [x] Listagem com n/p/q, incluindo `p` na primeira página
- [x] Sem internet → mensagem clara, sem stack trace

## Etapa 9 — Além do MVP (feito em 2026-10-17)
- [x] Comandos diretos com `argparse`: `pokedex search pikachu`, `pokedex list --page 2`
- [x] Cache em memória no cliente (páginas e Pokémon já vistos não geram nova requisição)
- [x] Busca por espécie: `deoxys` → forma padrão `deoxys-normal` (via `/pokemon-species`)
- [x] Normalização de entrada: acentos, pontos, apóstrofos, espaços e zeros à esquerda
- [x] Correção do BOM do PowerShell em entrada redirecionada (com teste de regressão)
- [x] mypy em modo estrito, pytest-cov (100% de cobertura), testes de integração marcados
- [x] `pyproject.toml` instalável (`pip install -e .` cria o comando `pokedex`)
- [x] CI no GitHub Actions (Ubuntu + Windows) e licença MIT
