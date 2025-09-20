from flask import Flask, render_template, request, redirect, url_for, flash
import os
import psycopg2
import psycopg2.extras
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
ADMIN_PASSWORD = "Lab8858"

# Conexão com o Banco de Dados (PostgreSQL)
def get_db_connection():
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Inicializar o banco de dados e as tabelas, se não existirem
def init_db():
    conn = get_db_connection()
    if conn is not None:
        try:
            with conn.cursor() as cursor:
                # Cria a extensão uuid-ossp se ainda não existir
                cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
                conn.commit()
                
                # Verifica se a tabela 'itens' existe
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS itens (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        nome VARCHAR(255) NOT NULL,
                        tipo VARCHAR(50) NOT NULL,
                        quantidade INTEGER,
                        categoria VARCHAR(255),
                        status VARCHAR(50)
                    );
                """)
                
                # Verifica se a tabela 'historico' existe
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS historico (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        item_id UUID,
                        item_nome VARCHAR(255),
                        acao VARCHAR(50) NOT NULL,
                        quantidade INTEGER,
                        usuario VARCHAR(255),
                        destino TEXT,
                        setor TEXT,
                        datahora TIMESTAMP
                    );
                """)
                
                # Verifica se a tabela 'usuarios' existe
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        nome VARCHAR(255) NOT NULL,
                        funcao VARCHAR(255) NOT NULL
                    );
                """)
                
                # Verifica se a tabela 'projetos' existe
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS projetos (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        nome VARCHAR(255) NOT NULL,
                        descricao TEXT,
                        prioridade VARCHAR(50),
                        status VARCHAR(50)
                    );
                """)
                conn.commit()
        except Exception as e:
            print(f"Erro ao inicializar o banco de dados: {e}")
        finally:
            conn.close()

def execute_query(query, params=None, fetchall=False, fetchone=False):
    conn = get_db_connection()
    if conn is None:
        return [] if fetchall else None

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(query, params)
            conn.commit()
            if fetchall:
                return cursor.fetchall()
            if fetchone:
                return cursor.fetchone()
    except Exception as e:
        print(f"Erro ao executar a query: {e}")
        conn.rollback()
    finally:
        conn.close()
    return [] if fetchall else None


@app.route("/", methods=["GET", "POST"])
def index():
    init_db()

    if request.method == "POST":
        # ... (Sua lógica de adicionar item) ...
        # (Aqui você deve substituir as chamadas a 'cursor.execute' por 'execute_query')
        # ...

    historico_hoje = execute_query("""
        SELECT h.*, i.nome as item_nome FROM historico h
        LEFT JOIN itens i ON h.item_id = i.id
        WHERE date(h.datahora) = CURRENT_DATE
        ORDER BY h.datahora DESC
    """, fetchall=True)

    itens = execute_query("SELECT * FROM itens ORDER BY tipo ASC, nome ASC", fetchall=True)
    usuarios = execute_query("SELECT * FROM usuarios ORDER BY nome", fetchall=True)

    total_itens = sum([item["quantidade"] for item in itens if item["tipo"] == "Consumivel"]) if itens else 0
    total_itens += len([item for item in itens if item["tipo"] == "Duravel" and item["status"] == "Disponível"])
    entradas_hoje = sum([h['quantidade'] for h in historico_hoje if h['acao'] == 'entrada']) if historico_hoje else 0
    saidas_hoje = sum([h['quantidade'] for h in historico_hoje if h['acao'] in ['saida', 'emprestimo']]) if historico_hoje else 0
    total_usuarios = len(usuarios) if usuarios else 0

    return render_template("index.html",
                           itens=itens,
                           historico=historico_hoje,
                           usuarios=usuarios,
                           total_itens=total_itens,
                           entradas_hoje=entradas_hoje,
                           saidas_hoje=saidas_hoje,
                           total_usuarios=total_usuarios)

@app.route("/adicionar_usuario", methods=["POST"])
def adicionar_usuario():
    # ... (Sua lógica de adicionar usuário, mas usando 'execute_query') ...
    return redirect(url_for("index"))

@app.route("/excluir_usuario/<uuid:usuario_id>", methods=["POST"])
def excluir_usuario(usuario_id):
    # ... (Sua lógica de excluir usuário, mas usando 'execute_query') ...
    return redirect(url_for("index"))
    
@app.route("/retirar/<uuid:item_id>", methods=["POST"])
def retirar(item_id):
    # ... (Sua lógica de retirar item, mas usando 'execute_query') ...
    return redirect(url_for("index"))
    
@app.route("/devolver/<uuid:item_id>", methods=["POST"])
def devolver(item_id):
    # ... (Sua lógica de devolver item, mas usando 'execute_query') ...
    return redirect(url_for("index"))

@app.route("/excluir/<uuid:item_id>", methods=["POST"])
def excluir(item_id):
    # ... (Sua lógica de excluir item, mas usando 'execute_query') ...
    return redirect(url_for("index"))

@app.route("/projetos")
def projetos():
    projetos = execute_query("SELECT * FROM projetos ORDER BY prioridade DESC, nome ASC", fetchall=True)
    return render_template("projetos.html", projetos=projetos)

@app.route("/adicionar_projeto", methods=["POST"])
def adicionar_projeto():
    # ... (Sua lógica de adicionar projeto, mas usando 'execute_query') ...
    return redirect(url_for("projetos"))

@app.route("/editar_projeto/<uuid:projeto_id>", methods=["POST"])
def editar_projeto(projeto_id):
    # ... (Sua lógica de editar projeto, mas usando 'execute_query') ...
    return redirect(url_for("projetos"))

@app.route("/excluir_projeto/<uuid:projeto_id>", methods=["POST"])
def excluir_projeto(projeto_id):
    # ... (Sua lógica de excluir projeto, mas usando 'execute_query') ...
    return redirect(url_for("projetos"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)