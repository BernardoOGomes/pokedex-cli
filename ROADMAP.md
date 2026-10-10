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
- [ ] `git init`, `.gitignore`, primeiro commit

## Etapa 1 — Explorar a PokéAPI
- [ ] Conceitos: HTTP, GET, status codes (200/404/5xx), JSON, REST
- [ ] Explorar `/pokemon/pikachu` no navegador e com `requests`
- [ ] Localizar no JSON: id, name, height, weight, types, abilities, stats
- [ ] Explorar a paginação: `/pokemon?limit=20&offset=0`
- [ ] Unidades: altura em decímetros, peso em hectogramas

## Etapa 2 — Model `Pokemon`
- [ ] Dataclass `Pokemon` com type hints
- [ ] `Pokemon.from_api_data(data)` (JSON → objeto)
- [ ] Testes com pytest e fixture de JSON de exemplo

## Etapa 3 — Service `PokeApiClient` (caminho feliz)
- [ ] Classe com `base_url`, `timeout` e `Session` injetada
- [ ] `get_pokemon(name_or_id)` e normalização da entrada
- [ ] `list_pokemon(limit, offset)` → `PokemonPage`
- [ ] Testes com `Mock` (sem internet)

## Etapa 4 — Tratamento de erros
- [ ] Exceções próprias: `PokeApiError`, `PokemonNotFoundError`, `ApiUnavailableError`, `InvalidResponseError`
- [ ] Converter timeout, erro de conexão, 404, 5xx e JSON inválido
- [ ] Testes com `pytest.raises`

## Etapa 5 — CLI: exibição e busca
- [ ] `format_pokemon(pokemon) -> str` (função pura, com conversão de unidades)
- [ ] Fluxo de busca com validação de entrada e mensagens de erro claras
- [ ] Testes da formatação

## Etapa 6 — CLI: listagem com paginação
- [ ] Loop com `n` / `p` / `q` e comando inválido
- [ ] Limites: não voltar antes da primeira página nem passar da última

## Etapa 7 — Menu principal
- [ ] Menu (1 Search / 2 List / 3 Exit) e opção inválida
- [ ] `__main__.py` e `py -m pokedex`; Ctrl+C sai de forma limpa
- [ ] Teste manual de ponta a ponta

## Etapa 8 — Acabamento e portfólio
- [ ] `ruff check` / `ruff format` limpos e todos os testes passando
- [ ] README em inglês (o que é, como rodar, como testar)
- [ ] Criar repositório público no GitHub (com aprovação) e fazer push
- [ ] Lista de melhorias futuras

## Verificação final
- [ ] `pytest` passa sem acesso à internet
- [ ] Buscar `pikachu` e `25`
- [ ] Buscar `abc123` → "Pokémon not found."
- [ ] Opção de menu inválida tratada
- [ ] Listagem com n/p/q, incluindo `p` na primeira página
- [ ] Sem internet → mensagem clara, sem stack trace
