from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_NAME = "lab.db"
app.secret_key = 'sua_chave_secreta_aqui'
ADMIN_PASSWORD = "Lab8858"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()
    cursor = conn.cursor()

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

                cursor.execute("SELECT id, quantidade, tipo FROM itens WHERE nome=? AND tipo=?", (nome, tipo))
                item = cursor.fetchone()

                if item:
                    nova_quantidade = item["quantidade"] + qtd
                    cursor.execute("UPDATE itens SET quantidade = ? WHERE id = ?", (nova_quantidade, item["id"]))
                    cursor.execute("INSERT INTO historico (item_id, acao, quantidade, usuario) VALUES (?, 'entrada', ?, ?)",
                                   (item["id"], qtd, usuario))
                else:
                    cursor.execute("INSERT INTO itens (nome, quantidade, tipo, categoria) VALUES (?, ?, ?, ?)",
                                   (nome, qtd, tipo, categoria))
                    item_id = cursor.lastrowid
                    cursor.execute("INSERT INTO historico (item_id, acao, quantidade, usuario) VALUES (?, 'entrada', ?, ?)",
                                   (item_id, qtd, usuario))
            
            elif tipo == "Duravel":
                status = "Disponível"
                cursor.execute("INSERT INTO itens (nome, quantidade, tipo, categoria, status) VALUES (?, ?, ?, ?, ?)",
                               (nome, 1, tipo, categoria, status))
                item_id = cursor.lastrowid
                cursor.execute("INSERT INTO historico (item_id, acao, quantidade, usuario) VALUES (?, 'entrada', ?, ?)",
                               (item_id, 1, usuario))

            conn.commit()
            flash("Item adicionado com sucesso!", "success")
        except (sqlite3.Error, ValueError) as e:
            flash(f"Ocorreu um erro ao adicionar o item: {e}", "error")
            print(f"Erro ao processar formulário: {e}")
        finally:
            conn.close()
        return redirect(url_for("index"))

    # -- Lógica de Filtro para o Histórico --
    filter_acao = request.args.get('acao')
    filter_usuario = request.args.get('usuario')
    filter_data = request.args.get('data')

    query = """
        SELECT h.*, i.nome as item_nome FROM historico h
        LEFT JOIN itens i ON h.item_id = i.id
    """
    conditions = []
    params = []

    if filter_acao:
        conditions.append("h.acao = ?")
        params.append(filter_acao)
    
    if filter_usuario:
        conditions.append("h.usuario = ?")
        params.append(filter_usuario)

    if filter_data:
        conditions.append("date(h.datahora) = ?")
        params.append(filter_data)
    else:
        conditions.append("date(h.datahora) = ?")
        params.append(datetime.now().strftime('%Y-%m-%d'))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY h.datahora DESC"

    cursor.execute(query, params)
    historico_hoje = cursor.fetchall()
    # -- Fim da Lógica de Filtro --

    cursor.execute("SELECT * FROM itens ORDER BY tipo ASC, nome ASC")
    itens = cursor.fetchall()

    cursor.execute("SELECT * FROM usuarios ORDER BY nome")
    usuarios = cursor.fetchall()
    
    total_itens = sum([item["quantidade"] for item in itens if item["tipo"] == "Consumivel"]) + len([item for item in itens if item["tipo"] == "Duravel" and item["status"] == "Disponível"])
    entradas_hoje = sum([h['quantidade'] for h in historico_hoje if h['acao'] == 'entrada'])
    saidas_hoje = sum([h['quantidade'] for h in historico_hoje if h['acao'] in ['saida', 'emprestimo']])
    total_usuarios = len(usuarios)

    conn.close()
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
    conn = None  # Inicializa a conexão como nula
    try:
        if request.form.get("senha") != ADMIN_PASSWORD:
            flash("Senha incorreta. Não é possível adicionar o usuário.", "error")
            return redirect(url_for("index"))

        conn = get_db()
        cursor = conn.cursor()
        
        nome = request.form["nome"].strip()
        funcao = request.form["funcao"].strip()
        
        cursor.execute("INSERT INTO usuarios (nome, funcao) VALUES (?, ?)", (nome, funcao))
        conn.commit()
        flash("Usuário adicionado com sucesso!", "success")
    except sqlite3.Error as e:
        flash(f"Ocorreu um erro ao adicionar o usuário: {e}", "error")
        print(f"Erro ao adicionar usuário: {e}")
    finally:
        if conn:  # Verifica se a conexão existe antes de fechar
            conn.close()
    return redirect(url_for("index"))

@app.route("/excluir_usuario/<int:usuario_id>", methods=["POST"])
def excluir_usuario(usuario_id):
    conn = None # Inicializa a conexão como nula
    try:
        if request.form.get("senha") != ADMIN_PASSWORD:
            flash("Senha incorreta. Não é possível excluir o usuário.", "error")
            return redirect(url_for("index"))
            
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT nome FROM usuarios WHERE id=?", (usuario_id,))
        usuario_para_excluir = cursor.fetchone()
        
        if usuario_para_excluir:
            usuario_nome = usuario_para_excluir["nome"]
            cursor.execute("DELETE FROM usuarios WHERE id=?", (usuario_id,))
            conn.commit()
            flash(f"Usuário '{usuario_nome}' excluído com sucesso!", "success")
        else:
            flash("Erro: Usuário não encontrado.", "error")
    except sqlite3.Error as e:
        flash(f"Ocorreu um erro ao excluir o usuário: {e}", "error")
        print(f"Erro ao excluir usuário: {e}")
    finally:
        if conn: # Verifica se a conexão existe antes de fechar
            conn.close()
    return redirect(url_for("index"))

@app.route("/retirar/<int:item_id>", methods=["POST"])
def retirar(item_id):
    try:
        qtd = int(request.form.get("quantidade", 1))
        usuario = request.form.get("usuario", "Desconhecido")
        destino = request.form.get("destino", "")
        setor = request.form.get("setor", "")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT quantidade, tipo, status FROM itens WHERE id=?", (item_id,))
        item = cursor.fetchone()

        if not item:
            flash("Erro: Item não encontrado.", "error")
            return redirect(url_for("index"))

        if item["tipo"] == "Consumivel":
            if item["quantidade"] >= qtd:
                nova_quantidade = item["quantidade"] - qtd
                cursor.execute("UPDATE itens SET quantidade = ? WHERE id=?", (nova_quantidade, item_id))
                cursor.execute("INSERT INTO historico (item_id, acao, quantidade, usuario, destino, setor) VALUES (?, 'saida', ?, ?, ?, ?)",
                               (item_id, qtd, usuario, destino, setor))
                conn.commit()
                flash("Item retirado com sucesso!", "success")
            else:
                flash("Erro: Quantidade insuficiente para item consumível.", "error")
        
        elif item["tipo"] == "Duravel":
            if item["status"] == "Disponível":
                cursor.execute("UPDATE itens SET status = 'Emprestado' WHERE id=?", (item_id,))
                cursor.execute("INSERT INTO historico (item_id, acao, quantidade, usuario, destino, setor) VALUES (?, ?, ?, ?, ?, ?)",
                               (item_id, 'emprestimo', 1, usuario, destino, setor))
                conn.commit()
                flash("Item emprestado com sucesso!", "success")
            else:
                flash("Erro: Item durável já está emprestado.", "error")
        
    except (sqlite3.Error, ValueError) as e:
        flash(f"Ocorreu um erro: {e}", "error")
        print(f"Erro ao processar retirada: {e}")
    finally:
        conn.close()
    return redirect(url_for("index"))

@app.route("/devolver/<int:item_id>", methods=["POST"])
def devolver(item_id):
    try:
        usuario = request.form.get("usuario", "Desconhecido")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM itens WHERE id=?", (item_id,))
        item = cursor.fetchone()

        if item and item["status"] == "Emprestado":
            cursor.execute("UPDATE itens SET status = 'Disponível' WHERE id=?", (item_id,))
            cursor.execute("INSERT INTO historico (item_id, acao, quantidade, usuario) VALUES (?, 'devolucao', 1, ?)",
                           (item_id, usuario))
            conn.commit()
            flash("Item devolvido com sucesso!", "success")
        else:
            flash("Erro: Item não pode ser devolvido ou não está emprestado.", "error")
            print("Erro: Item não pode ser devolvido ou não está emprestado.")
    except sqlite3.Error as e:
        flash(f"Ocorreu um erro: {e}", "error")
        print(f"Erro ao processar devolução: {e}")
    finally:
        conn.close()
    return redirect(url_for("index"))

@app.route("/excluir/<int:item_id>", methods=["POST"])
def excluir(item_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT nome FROM itens WHERE id=?", (item_id,))
        item_para_excluir = cursor.fetchone()
        
        if item_para_excluir:
            item_nome = item_para_excluir["nome"]
            
            cursor.execute("INSERT INTO historico (item_id, acao, quantidade, usuario, destino, setor) VALUES (?, 'exclusao', ?, ?, ?, ?)",
                           (item_id, 0, "Sistema/Admin", item_nome, "Item excluído"))
            
            cursor.execute("DELETE FROM itens WHERE id=?", (item_id,))
            conn.commit()
            flash(f"Item '{item_nome}' excluído com sucesso!", "success")
        else:
            flash("Erro: Item não encontrado.", "error")
    except sqlite3.Error as e:
        flash(f"Ocorreu um erro ao excluir o item: {e}", "error")
        print(f"Erro ao excluir item: {e}")
    finally:
        conn.close()
    return redirect(url_for("index"))

@app.route("/projetos")
def projetos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projetos ORDER BY prioridade DESC, nome ASC")
    projetos = cursor.fetchall()
    conn.close()
    return render_template("projetos.html", projetos=projetos)

@app.route("/adicionar_projeto", methods=["POST"])
def adicionar_projeto():
    try:
        nome = request.form["nome"].strip()
        descricao = request.form["descricao"].strip()
        prioridade = request.form["prioridade"]
        status = request.form["status"]
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projetos (nome, descricao, prioridade, status) VALUES (?, ?, ?, ?)",
                       (nome, descricao, prioridade, status))
        conn.commit()
        flash("Projeto adicionado com sucesso!", "success")
    except sqlite3.Error as e:
        flash(f"Erro ao adicionar projeto: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("projetos"))

@app.route("/editar_projeto/<int:projeto_id>", methods=["POST"])
def editar_projeto(projeto_id):
    try:
        nome = request.form["nome"].strip()
        descricao = request.form["descricao"].strip()
        prioridade = request.form["prioridade"]
        status = request.form["status"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projetos SET nome = ?, descricao = ?, prioridade = ?, status = ? WHERE id = ?",
                       (nome, descricao, prioridade, status, projeto_id))
        conn.commit()
        flash("Projeto editado com sucesso!", "success")
    except sqlite3.Error as e:
        flash(f"Erro ao editar projeto: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("projetos"))

@app.route("/excluir_projeto/<int:projeto_id>", methods=["POST"])
def excluir_projeto(projeto_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projetos WHERE id = ?", (projeto_id,))
        conn.commit()
        flash("Projeto excluído com sucesso!", "success")
    except sqlite3.Error as e:
        flash(f"Erro ao excluir projeto: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for("projetos"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)