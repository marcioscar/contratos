# Projeto Planilhas

Projeto para processamento de planilhas.

## Configuração do Ambiente

Este projeto usa `uv` para gerenciamento de ambiente Python.

### Ativar o ambiente virtual

```bash
source .venv/bin/activate
```

Ou com uv:

```bash
uv run python script.py
```

### Instalar dependências

Sincronizar ambiente com as dependências do pyproject.toml:

```bash
uv sync
```

### Adicionar novas dependências

Para adicionar dependências ao projeto:

```bash
uv add nome-do-pacote
```

Para adicionar dependências de desenvolvimento:

```bash
uv add --dev nome-do-pacote
```

Exemplos:

```bash
uv add pandas openpyxl jinja2 plotly streamlit
uv add --dev ipykernel
```

### Usar o ambiente

```bash
uv run python seu_script.py
```

Ou ativar o ambiente:

```bash
source .venv/bin/activate
```
# contratos
