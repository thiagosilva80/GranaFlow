from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt 
from datetime import datetime

from database.conexao import criar_conexao


app = Flask(__name__)
app.secret_key = "granaflow-chave-secreta"

bcrypt = Bcrypt(app)


# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        senha = request.form["senha"]

        conexao = criar_conexao()
        cursor = conexao.cursor()

        usuario = cursor.execute(
            """
            SELECT * FROM usuarios
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conexao.close()

        if usuario and bcrypt.check_password_hash(usuario["senha"], senha):

            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]

            return redirect(url_for("dashboard"))

        flash("E-mail ou senha incorretos.")

    return render_template("login.html")


# =========================
# CADASTRO
# =========================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        senha_hash = bcrypt.generate_password_hash(
            senha
        ).decode("utf-8")

        conexao = criar_conexao()
        cursor = conexao.cursor()

        usuario_existente = cursor.execute(
            """
            SELECT * FROM usuarios
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if usuario_existente:

            conexao.close()

            flash("Este e-mail já está cadastrado.")

            return redirect(url_for("cadastro"))

        cursor.execute(
            """
            INSERT INTO usuarios
            (nome, email, senha)
            VALUES (?, ?, ?)
            """,
            (
                nome,
                email,
                senha_hash
            )
        )

        conexao.commit()
        conexao.close()

        flash("Conta criada com sucesso!")

        return redirect(url_for("login"))

    return render_template("cadastro.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()


    # -------------------------
    # TOTAL DE RECEITAS
    # -------------------------

    resultado_receitas = cursor.execute(
        """
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM receitas
        WHERE usuario_id = ?
        """,
        (usuario_id,)
    ).fetchone()

    total_receitas = resultado_receitas["total"]


    # -------------------------
    # TOTAL DE DESPESAS
    # -------------------------

    resultado_despesas = cursor.execute(
        """
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM despesas
        WHERE usuario_id = ?
        """,
        (usuario_id,)
    ).fetchone()

    total_despesas = resultado_despesas["total"]


    # -------------------------
    # SALDO
    # -------------------------

    saldo = total_receitas - total_despesas


    # -------------------------
    # ÚLTIMAS MOVIMENTAÇÕES
    # -------------------------

    movimentacoes = cursor.execute(
        """
        SELECT
            descricao,
            valor,
            categoria,
            data,
            'receita' AS tipo
        FROM receitas
        WHERE usuario_id = ?

        UNION ALL

        SELECT
            descricao,
            valor,
            categoria,
            data,
            'despesa' AS tipo
        FROM despesas
        WHERE usuario_id = ?

        ORDER BY data DESC
        LIMIT 5
        """,
        (
            usuario_id,
            usuario_id
        )
    ).fetchall()


    # -------------------------
    # GASTOS POR CATEGORIA
    # -------------------------

    gastos_categoria = cursor.execute(
        """
        SELECT
            categoria,
            SUM(valor) AS total
        FROM despesas
        WHERE usuario_id = ?
        GROUP BY categoria
        ORDER BY total DESC
        """,
        (usuario_id,)
    ).fetchall()


    categorias_dashboard = []

    for item in gastos_categoria:

        total_categoria = item["total"]

        if total_despesas > 0:

            porcentagem = (
                total_categoria / total_despesas
            ) * 100

        else:

            porcentagem = 0

        categorias_dashboard.append({
            "categoria": item["categoria"],
            "total": total_categoria,
            "porcentagem": porcentagem
        })


    # -------------------------
    # CONTAS PENDENTES
    # -------------------------

    resultado_contas = cursor.execute(
        """
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM contas
        WHERE usuario_id = ?
        AND status = 'pendente'
        """,
        (usuario_id,)
    ).fetchone()

    total_contas = resultado_contas["total"]

    meta_principal = cursor.execute(
    """
    SELECT *
    FROM metas
    WHERE usuario_id = ?
    ORDER BY id DESC
    LIMIT 1
    """,
    (usuario_id,)
    ).fetchone()
    
    
    meta_dashboard = None

    if meta_principal:

        if meta_principal["valor_meta"] > 0:
            porcentagem_meta = (
            meta_principal["valor_atual"] /
            meta_principal["valor_meta"]
        ) * 100
    else:
        porcentagem_meta = 0

    porcentagem_meta = min(porcentagem_meta, 100)

    meta_dashboard = {
        "nome": meta_principal["nome"],
        "valor_meta": meta_principal["valor_meta"],
        "valor_atual": meta_principal["valor_atual"],
        "porcentagem": porcentagem_meta
    }
    


    conexao.close()


    return render_template(
        "dashboard.html",

        nome=session["usuario_nome"],

        total_receitas=total_receitas,

        total_despesas=total_despesas,

        saldo=saldo,

        movimentacoes=movimentacoes,

        categorias_dashboard=categorias_dashboard,

        total_contas=total_contas,
        
        meta_dashboard=meta_dashboard
    )


# =========================
# RECEITAS
# =========================

@app.route("/receitas", methods=["GET", "POST"])
def receitas():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()


    if request.method == "POST":

        descricao = request.form["descricao"]

        valor = float(
            request.form["valor"]
        )

        categoria = request.form["categoria"]

        data = request.form["data"]


        cursor.execute(
            """
            INSERT INTO receitas
            (
                usuario_id,
                descricao,
                valor,
                categoria,
                data
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                usuario_id,
                descricao,
                valor,
                categoria,
                data
            )
        )

        conexao.commit()
        conexao.close()

        return redirect(
            url_for("receitas")
        )


    receitas_usuario = cursor.execute(
        """
        SELECT *
        FROM receitas
        WHERE usuario_id = ?
        ORDER BY data DESC, id DESC
        """,
        (usuario_id,)
    ).fetchall()


    conexao.close()


    return render_template(
        "receitas.html",
        receitas=receitas_usuario
    )


# =========================
# DESPESAS
# =========================

@app.route("/despesas", methods=["GET", "POST"])
def despesas():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()


    if request.method == "POST":

        descricao = request.form["descricao"]

        valor = float(
            request.form["valor"]
        )

        categoria = request.form["categoria"]

        data = request.form["data"]


        cursor.execute(
            """
            INSERT INTO despesas
            (
                usuario_id,
                descricao,
                valor,
                categoria,
                data
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                usuario_id,
                descricao,
                valor,
                categoria,
                data
            )
        )

        conexao.commit()
        conexao.close()

        return redirect(
            url_for("despesas")
        )


    despesas_usuario = cursor.execute(
        """
        SELECT *
        FROM despesas
        WHERE usuario_id = ?
        ORDER BY data DESC, id DESC
        """,
        (usuario_id,)
    ).fetchall()


    conexao.close()


    return render_template(
        "despesas.html",
        despesas=despesas_usuario
    )


# =========================
# CONTAS
# =========================

@app.route("/contas", methods=["GET", "POST"])
def contas():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()


    if request.method == "POST":

        descricao = request.form["descricao"]

        valor = float(
            request.form["valor"]
        )

        categoria = request.form["categoria"]

        vencimento = request.form["vencimento"]


        cursor.execute(
            """
            INSERT INTO contas
            (
                usuario_id,
                descricao,
                valor,
                categoria,
                vencimento
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                usuario_id,
                descricao,
                valor,
                categoria,
                vencimento
            )
        )

        conexao.commit()
        conexao.close()

        return redirect(
            url_for("contas")
        )


    contas_usuario = cursor.execute(
        """
        SELECT *
        FROM contas
        WHERE usuario_id = ?

        ORDER BY

        CASE
            WHEN status = 'pendente'
            THEN 0
            ELSE 1
        END,

        vencimento ASC
        """,
        (usuario_id,)
    ).fetchall()


    conexao.close()


    return render_template(
        "contas.html",
        contas=contas_usuario
    )


# =========================
# MARCAR CONTA COMO PAGA
# =========================

@app.route("/contas/<int:conta_id>/pagar")
def pagar_conta(conta_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()


    conta = cursor.execute(
        """
        SELECT *
        FROM contas
        WHERE id = ?
        AND usuario_id = ?
        """,
        (
            conta_id,
            usuario_id
        )
    ).fetchone()


    if conta and conta["status"] == "pendente":

        cursor.execute(
            """
            UPDATE contas
            SET status = 'paga'
            WHERE id = ?
            AND usuario_id = ?
            """,
            (
                conta_id,
                usuario_id
            )
        )

        conexao.commit()


    conexao.close()


    return redirect(
        url_for("contas")
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )

@app.route("/metas", methods=["GET", "POST"])
def metas():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()

    if request.method == "POST":

        nome = request.form["nome"]
        valor_meta = float(request.form["valor_meta"])
        valor_atual = float(request.form.get("valor_atual") or 0)
        data_limite = request.form.get("data_limite") or None

        if valor_atual > valor_meta:
            valor_atual = valor_meta

        cursor.execute(
            """
            INSERT INTO metas
            (
                usuario_id,
                nome,
                valor_meta,
                valor_atual,
                data_limite
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                usuario_id,
                nome,
                valor_meta,
                valor_atual,
                data_limite
            )
        )

        conexao.commit()
        conexao.close()

        return redirect(url_for("metas"))

    metas_usuario = cursor.execute(
        """
        SELECT *
        FROM metas
        WHERE usuario_id = ?
        ORDER BY id DESC
        """,
        (usuario_id,)
    ).fetchall()

    metas_formatadas = []

    for meta in metas_usuario:

        if meta["valor_meta"] > 0:
            porcentagem = (
                meta["valor_atual"] /
                meta["valor_meta"]
            ) * 100
        else:
            porcentagem = 0

        porcentagem = min(porcentagem, 100)

        metas_formatadas.append({
            "id": meta["id"],
            "nome": meta["nome"],
            "valor_meta": meta["valor_meta"],
            "valor_atual": meta["valor_atual"],
            "data_limite": meta["data_limite"],
            "porcentagem": porcentagem
        })

    conexao.close()

    return render_template(
        "metas.html",
        metas=metas_formatadas
    )
    
@app.route("/metas/<int:meta_id>/adicionar", methods=["POST"])
def adicionar_valor_meta(meta_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    valor = float(request.form["valor"])

    conexao = criar_conexao()
    cursor = conexao.cursor()

    meta = cursor.execute(
        """
        SELECT *
        FROM metas
        WHERE id = ?
        AND usuario_id = ?
        """,
        (
            meta_id,
            usuario_id
        )
    ).fetchone()

    if meta:

        novo_valor = meta["valor_atual"] + valor

        if novo_valor > meta["valor_meta"]:
            novo_valor = meta["valor_meta"]

        cursor.execute(
            """
            UPDATE metas
            SET valor_atual = ?
            WHERE id = ?
            AND usuario_id = ?
            """,
            (
                novo_valor,
                meta_id,
                usuario_id
            )
        )

        conexao.commit()

    conexao.close()

    return redirect(url_for("metas"))


@app.route("/relatorios")
def relatorios():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    mes = request.args.get("mes")

    if not mes:
        mes = datetime.now().strftime("%Y-%m")

    conexao = criar_conexao()
    cursor = conexao.cursor()


    # RECEITAS DO MÊS
    resultado_receitas = cursor.execute(
        """
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM receitas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?
        """,
        (usuario_id, mes)
    ).fetchone()

    total_receitas = resultado_receitas["total"]


    # DESPESAS DO MÊS
    resultado_despesas = cursor.execute(
        """
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM despesas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?
        """,
        (usuario_id, mes)
    ).fetchone()

    total_despesas = resultado_despesas["total"]


    # SALDO
    saldo = total_receitas - total_despesas


    # QUANTIDADE DE MOVIMENTAÇÕES
    quantidade_receitas = cursor.execute(
        """
        SELECT COUNT(*) AS quantidade
        FROM receitas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?
        """,
        (usuario_id, mes)
    ).fetchone()["quantidade"]

    quantidade_despesas = cursor.execute(
        """
        SELECT COUNT(*) AS quantidade
        FROM despesas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?
        """,
        (usuario_id, mes)
    ).fetchone()["quantidade"]

    quantidade_movimentacoes = (
        quantidade_receitas +
        quantidade_despesas
    )


    # GASTOS POR CATEGORIA
    categorias = cursor.execute(
        """
        SELECT
            categoria,
            SUM(valor) AS total
        FROM despesas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?
        GROUP BY categoria
        ORDER BY total DESC
        """,
        (usuario_id, mes)
    ).fetchall()


    # MAIOR CATEGORIA DE GASTO
    maior_categoria = None

    if categorias:
        maior_categoria = categorias[0]


    # MOVIMENTAÇÕES DO MÊS
    movimentacoes = cursor.execute(
        """
        SELECT
            descricao,
            valor,
            categoria,
            data,
            'receita' AS tipo
        FROM receitas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?

        UNION ALL

        SELECT
            descricao,
            valor,
            categoria,
            data,
            'despesa' AS tipo
        FROM despesas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?

        ORDER BY data DESC
        """,
        (
            usuario_id,
            mes,
            usuario_id,
            mes
        )
    ).fetchall()


    conexao.close()


    return render_template(
        "relatorios.html",
        mes=mes,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        saldo=saldo,
        quantidade_movimentacoes=quantidade_movimentacoes,
        categorias=categorias,
        maior_categoria=maior_categoria,
        movimentacoes=movimentacoes
    )
    
@app.route("/configuracoes", methods=["GET", "POST"])
def configuracoes():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()

    usuario = cursor.execute(
        """
        SELECT *
        FROM usuarios
        WHERE id = ?
        """,
        (usuario_id,)
    ).fetchone()

    if request.method == "POST":

        acao = request.form.get("acao")

        # EDITAR PERFIL
        if acao == "perfil":

            nome = request.form["nome"]
            email = request.form["email"]

            email_existente = cursor.execute(
                """
                SELECT *
                FROM usuarios
                WHERE email = ?
                AND id != ?
                """,
                (email, usuario_id)
            ).fetchone()

            if email_existente:

                flash("Este e-mail já está sendo utilizado.")

            else:

                cursor.execute(
                    """
                    UPDATE usuarios
                    SET nome = ?, email = ?
                    WHERE id = ?
                    """,
                    (
                        nome,
                        email,
                        usuario_id
                    )
                )

                conexao.commit()

                session["usuario_nome"] = nome

                flash("Perfil atualizado com sucesso.")

        # ALTERAR SENHA
        elif acao == "senha":

            senha_atual = request.form["senha_atual"]
            nova_senha = request.form["nova_senha"]

            if bcrypt.check_password_hash(
                usuario["senha"],
                senha_atual
            ):

                nova_senha_hash = bcrypt.generate_password_hash(
                    nova_senha
                ).decode("utf-8")

                cursor.execute(
                    """
                    UPDATE usuarios
                    SET senha = ?
                    WHERE id = ?
                    """,
                    (
                        nova_senha_hash,
                        usuario_id
                    )
                )

                conexao.commit()

                flash("Senha alterada com sucesso.")

            else:

                flash("Senha atual incorreta.")

        conexao.close()

        return redirect(url_for("configuracoes"))

    conexao.close()

    return render_template(
        "configuracoes.html",
        usuario=usuario
    )
# =========================
# INICIAR SISTEMA
# =========================

if __name__ == "__main__":

    app.run(debug=True)