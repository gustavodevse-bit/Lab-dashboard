from flask import Flask, render_template, request, redirect, url_for, flash
import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import uuid

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
            if conn.autocommit == False:
                conn.commit()
            if fetchall:
                return cursor.fetchall()
            if fetchone:
                return cursor.fetchone()
    except Exception as e:
        print(f"Erro ao executar a query: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return [] if fetchall else None

@app.route("/", methods=["GET", "POST"])
def index():
    init_db()

    if request.method == "POST":
        try:
            nome = request.form["nome"].strip()
            tipo = request.form["tipo"]
            categoria = request.form.get("categoria", "").strip()
            usuario = request.form.get("usuario", "Desconhecido")
            
            if tipo == "Consumivel":
                qtd = int(request.form.get("quantidade", 1))
                if qtd <= 0:
                    flash("Erro: A quantidade de um item consumível deve ser maior que zero.", "error")
                    return redirect(url_for("index"))

                item = execute_query("SELECT id, quantidade, tipo FROM itens WHERE nome=%s AND tipo=%s", (nome, tipo), fetchone=True)
                
                if item:
                    nova_quantidade = item["quantidade"] + qtd
                    execute_query("UPDATE itens SET quantidade = %s WHERE id = %s", (nova_quantidade, item["id"]))
                    execute_query("INSERT INTO historico (item_id, item_nome, acao, quantidade, usuario, datahora) VALUES (%s, %s, %s, %s, %s, %s)",
                                  (item["id"], nome, 'entrada', qtd, usuario, datetime.now()))
                else:
                    item_id = str(uuid.uuid4())
                    execute_query("INSERT INTO itens (id, nome, quantidade, tipo, categoria) VALUES (%s, %s, %s, %s, %s)",
                                  (item_id, nome, qtd, tipo, categoria))
                    execute_query("INSERT INTO historico (item_id, item_nome, acao, quantidade, usuario, datahora) VALUES (%s, %s, %s, %s, %s, %s)",
                                  (item_id, nome, 'entrada', qtd, usuario, datetime.now()))

            elif tipo == "Duravel":
                status = "Disponível"
                item_id = str(uuid.uuid4())
                execute_query("INSERT INTO itens (id, nome, quantidade, tipo, categoria, status) VALUES (%s, %s, %s, %s, %s, %s)",
                               (item_id, nome, 1, tipo, categoria, status))
                execute_query("INSERT INTO historico (item_id, item_nome, acao, quantidade, usuario, datahora) VALUES (%s, %s, %s, %s, %s, %s)",
                               (item_id, nome, 'entrada', 1, usuario, datetime.now()))

            flash("Item adicionado com sucesso!", "success")
        except (psycopg2.Error, ValueError) as e:
            flash(f"Ocorreu um erro ao adicionar o item: {e}", "error")
            print(f"Erro ao processar formulário: {e}")
        return redirect(url_for("index"))

    filter_acao = request.args.get('acao')
    filter_usuario = request.args.get('usuario')
    filter_data = request.args.get('data')

    query_params = []
    conditions = []
    
    base_query = """
        SELECT * FROM historico
    """

    if filter_acao:
        conditions.append("acao = %s")
        query_params.append(filter_acao)
    
    if filter_usuario:
        conditions.append("usuario = %s")
        query_params.append(filter_usuario)

    if filter_data:
        conditions.append("DATE(datahora) = %s")
        query_params.append(filter_data)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
    
    base_query += " ORDER BY datahora DESC"

    historico_hoje = execute_query(base_query, tuple(query_params), fetchall=True)

    itens = execute_query("SELECT * FROM itens ORDER BY tipo ASC, nome ASC", fetchall=True)
    usuarios = execute_query("SELECT * FROM usuarios ORDER BY nome", fetchall=True)
    
    total_itens = sum([item["quantidade"] for item in itens if item["tipo"] == "Consumivel"]) + len([item for item in itens if item["tipo"] == "Duravel" and item["status"] == "Disponível"])
    entradas_hoje = sum([h['quantidade'] for h in historico_hoje if h['acao'] == 'entrada'])
    saidas_hoje = sum([h['quantidade'] for h in historico_hoje if h['acao'] in ['saida', 'emprestimo']])
    total_usuarios = len(usuarios)

    return render_template("index.html",
                           itens=itens,
                           historico=historico_hoje,
                           usuarios=usuarios,
                           total_itens=total_itens,
                           entradas_hoje=entradas_hoje,
                           saidas_hoje=saidas_hoje,
                           total_usuarios=total_usuarios,
                           filter_acao=filter_acao,
                           filter_usuario=filter_usuario,
                           filter_data=filter_data)

@app.route("/adicionar_usuario", methods=["POST"])
def adicionar_usuario():
    try:
        if request.form.get("senha") != ADMIN_PASSWORD:
            flash("Senha incorreta. Não é possível adicionar o usuário.", "error")
            return redirect(url_for("index"))
        
        nome = request.form["nome"].strip()
        funcao = request.form["funcao"].strip()
        execute_query("INSERT INTO usuarios (nome, funcao) VALUES (%s, %s)", (nome, funcao))
        flash("Usuário adicionado com sucesso!", "success")
    except psycopg2.Error as e:
        flash(f"Ocorreu um erro ao adicionar o usuário: {e}", "error")
        print(f"Erro ao adicionar usuário: {e}")
    return redirect(url_for("index"))

@app.route("/excluir_usuario/<uuid:usuario_id>", methods=["POST"])
def excluir_usuario(usuario_id):
    try:
        if request.form.get("senha") != ADMIN_PASSWORD:
            flash("Senha incorreta. Não é possível excluir o usuário.", "error")
            return redirect(url_for("index"))
            
        usuario_para_excluir = execute_query("SELECT nome FROM usuarios WHERE id=%s", (usuario_id,), fetchone=True)
        
        if usuario_para_excluir:
            usuario_nome = usuario_para_excluir["nome"]
            execute_query("DELETE FROM usuarios WHERE id=%s", (usuario_id,))
            flash(f"Usuário '{usuario_nome}' excluído com sucesso!", "success")
        else:
            flash("Erro: Usuário não encontrado.", "error")
    except psycopg2.Error as e:
        flash(f"Ocorreu um erro ao excluir o usuário: {e}", "error")
        print(f"Erro ao excluir usuário: {e}")
    return redirect(url_for("index"))

@app.route("/retirar/<uuid:item_id>", methods=["POST"])
def retirar(item_id):
    try:
        qtd = int(request.form.get("quantidade", 1))
        usuario = request.form.get("usuario", "Desconhecido")
        destino = request.form.get("destino", "")
        setor = request.form.get("setor", "")

        item = execute_query("SELECT quantidade, tipo, status, nome FROM itens WHERE id=%s", (item_id,), fetchone=True)

        if not item:
            flash("Erro: Item não encontrado.", "error")
            return redirect(url_for("index"))

        if item["tipo"] == "Consumivel":
            if item["quantidade"] >= qtd:
                nova_quantidade = item["quantidade"] - qtd
                execute_query("UPDATE itens SET quantidade = %s WHERE id=%s", (nova_quantidade, item_id))
                execute_query("INSERT INTO historico (item_id, item_nome, acao, quantidade, usuario, destino, setor, datahora) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                               (item_id, item["nome"], 'saida', qtd, usuario, destino, setor, datetime.now()))
                flash("Item retirado com sucesso!", "success")
            else:
                flash("Erro: Quantidade insuficiente para item consumível.", "error")
        
        elif item["tipo"] == "Duravel":
            if item["status"] == "Disponível":
                execute_query("UPDATE itens SET status = 'Emprestado' WHERE id=%s", (item_id,))
                execute_query("INSERT INTO historico (item_id, item_nome, acao, quantidade, usuario, destino, setor, datahora) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                               (item_id, item["nome"], 'emprestimo', 1, usuario, destino, setor, datetime.now()))
                flash("Item emprestado com sucesso!", "success")
            else:
                flash("Erro: Item durável já está emprestado.", "error")
    except (psycopg2.Error, ValueError) as e:
        flash(f"Ocorreu um erro: {e}", "error")
        print(f"Erro ao processar retirada: {e}")
    return redirect(url_for("index"))

@app.route("/devolver/<uuid:item_id>", methods=["POST"])
def devolver(item_id):
    try:
        usuario = request.form.get("usuario", "Desconhecido")
        
        item = execute_query("SELECT status, nome FROM itens WHERE id=%s", (item_id,), fetchone=True)

        if item and item["status"] == "Emprestado":
            execute_query("UPDATE itens SET status = 'Disponível' WHERE id=%s", (item_id,))
            execute_query("INSERT INTO historico (item_id, item_nome, acao, quantidade, usuario, datahora) VALUES (%s, %s, %s, %s, %s, %s)",
                           (item_id, item["nome"], 'devolucao', 1, usuario, datetime.now()))
            flash("Item devolvido com sucesso!", "success")
        else:
            flash("Erro: Item não pode ser devolvido ou não está emprestado.", "error")
            print("Erro: Item não pode ser devolvido ou não está emprestado.")
    except psycopg2.Error as e:
        flash(f"Ocorreu um erro: {e}", "error")
        print(f"Erro ao processar devolução: {e}")
    return redirect(url_for("index"))

@app.route("/excluir/<uuid:item_id>", methods=["POST"])
def excluir(item_id):
    try:
        item_para_excluir = execute_query("SELECT nome FROM itens WHERE id=%s", (item_id,), fetchone=True)
        
        if item_para_excluir:
            item_nome = item_para_excluir["nome"]
            execute_query("INSERT INTO historico (item_id, item_nome, acao, quantidade, usuario, destino, setor, datahora) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                           (item_id, item_nome, 'exclusao', 0, "Sistema/Admin", item_nome, "Item excluído", datetime.now()))
            execute_query("DELETE FROM itens WHERE id=%s", (item_id,))
            flash(f"Item '{item_nome}' excluído com sucesso!", "success")
        else:
            flash("Erro: Item não encontrado.", "error")
    except psycopg2.Error as e:
        flash(f"Ocorreu um erro ao excluir o item: {e}", "error")
        print(f"Erro ao excluir item: {e}")
    return redirect(url_for("index"))

@app.route("/projetos")
def projetos():
    projetos = execute_query("SELECT * FROM projetos ORDER BY prioridade DESC, nome ASC", fetchall=True)
    return render_template("projetos.html", projetos=projetos)

@app.route("/adicionar_projeto", methods=["POST"])
def adicionar_projeto():
    try:
        nome = request.form["nome"].strip()
        descricao = request.form["descricao"].strip()
        prioridade = request.form["prioridade"]
        status = request.form["status"]
        
        execute_query("INSERT INTO projetos (nome, descricao, prioridade, status) VALUES (%s, %s, %s, %s)",
                       (nome, descricao, prioridade, status))
        flash("Projeto adicionado com sucesso!", "success")
    except psycopg2.Error as e:
        flash(f"Erro ao adicionar projeto: {e}", "error")
    return redirect(url_for("projetos"))

@app.route("/editar_projeto/<uuid:projeto_id>", methods=["POST"])
def editar_projeto(projeto_id):
    try:
        nome = request.form["nome"].strip()
        descricao = request.form["descricao"].strip()
        prioridade = request.form["prioridade"]
        status = request.form["status"]

        execute_query("UPDATE projetos SET nome = %s, descricao = %s, prioridade = %s, status = %s WHERE id = %s",
                       (nome, descricao, prioridade, status, projeto_id))
        flash("Projeto editado com sucesso!", "success")
    except psycopg2.Error as e:
        flash(f"Erro ao editar projeto: {e}", "error")
    return redirect(url_for("projetos"))

@app.route("/excluir_projeto/<uuid:projeto_id>", methods=["POST"])
def excluir_projeto(projeto_id):
    try:
        execute_query("DELETE FROM projetos WHERE id = %s", (projeto_id,))
        flash("Projeto excluído com sucesso!", "success")
    except psycopg2.Error as e:
        flash(f"Erro ao excluir projeto: {e}", "error")
    return redirect(url_for("projetos"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.environ.get("PORT", 5000), debug=True)