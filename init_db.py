import sqlite3

conn = sqlite3.connect("lab.db")
cursor = conn.cursor()

# Apaga as tabelas existentes para garantir uma nova estrutura
cursor.execute("DROP TABLE IF EXISTS itens")
cursor.execute("DROP TABLE IF EXISTS historico")
cursor.execute("DROP TABLE IF EXISTS usuarios")
cursor.execute("DROP TABLE IF EXISTS projetos") # Adicione esta linha

# Cria a tabela de itens
cursor.execute("""
CREATE TABLE IF NOT EXISTS itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    categoria TEXT,
    status TEXT DEFAULT 'Disponível'
)
""")

# Cria a tabela de histórico
cursor.execute("""
CREATE TABLE IF NOT EXISTS historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    acao TEXT NOT NULL,
    quantidade INTEGER,
    usuario TEXT,
    destino TEXT,
    setor TEXT,
    datahora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES itens (id)
)
""")

# Cria a tabela de usuários
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    funcao TEXT
)
""")

# Adiciona a tabela de projetos
cursor.execute("""
CREATE TABLE IF NOT EXISTS projetos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    descricao TEXT,
    prioridade TEXT NOT NULL,
    status TEXT NOT NULL
)
""")

# Adiciona um projeto de exemplo para visualização
cursor.execute("INSERT INTO projetos (nome, descricao, prioridade, status) VALUES ('Robô de Coleta', 'Desenvolvimento de um robô para coletar amostras em locais de difícil acesso.', 'Alta', 'Em andamento')")

conn.commit()
conn.close()

print("Banco de dados recriado com sucesso. Execute app.py em seguida.")