# Dashboard PowerX

## Como fazdr o seutp

### 1. Instalar dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar secrets
Crie o arquivo `.streamlit/secrets.toml`:
```toml
[paths]
data_dir = "./data/vendas"

[settings]
debug_mode = true
```

### 3. Adicionar dados
Algo nesse estilo: 
```
data/vendas/
├── sp1_mclarty_maia.xlsx
├── sp1_jeep_pacaembu.xlsx
└── sp2_mercedes_pacaembu.xlsx
```

### 4. Rodar aplicação
```bash
streamlit run py/streamlit_app.py
```

## Como adicionar novas loja? Vamo que vamo ensinar

### Passo 1: Adicionar arquivo XLSX (o nome em si é tanto faz, porém é legal seguir esse estilo)
```
data/vendas/sp1_nova_loja.xlsx
```

### Passo 2: Editar o aqurivbo `config/lojas.yaml`
```yaml
regioes:
  XXX:
    lojas:
      - nome: "Nova Loja"
        nome_completo: "Nome Completo da Loja"
        arquivo: "arquivo_que_contem_os_dados.xlsx"
        filtro_cliente: "Nome no Campo Cliente"
        sheet: "Sheet0"
        ativa: true
```

### Passo 3: Reiniciar app
Fecha a aplicação e rode ela de novo com streamlitrun. Depois disso deve aparecer normalmente

## Deploy no Streamlit Cloud

1. Fazer push do código (sem secrets.toml)
2. No painel do Streamlit Cloud, adicionar secrets:
```toml
   [paths]
   data_dir = "./data/vendas"
```
3. Fazer upload dos arquivos XLSX via GitHub ou interface do Streamlit

## Estrutura de Arquivos XLSX

Colunas obrigatórias:
- Mês (formato: ANO-MÊS-DIA, ex: 2025-04-15)
- N° Doc
- Cliente
- Vendedor
- Produto
- Descrição
- Quantidade
- Valor_Unidade
- Valor_Total
