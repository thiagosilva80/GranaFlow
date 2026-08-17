from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt

from database.conexao import criar_conexao


app = Flask(__name__)
app.secret_key = "granaflow-chave-secreta"

bcrypt = Bcrypt(app)


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        senha = request.form["senha"]

        conexao = criar_conexao()
        cursor = conexao.cursor()

        usuario = cursor.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (email,)
        ).fetchone()

        conexao.close()

        if usuario and bcrypt.check_password_hash(usuario["senha"], senha):

            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]

            return redirect(url_for("dashboard"))

        flash("E-mail ou senha incorretos.")

    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        senha_hash = bcrypt.generate_password_hash(senha).decode("utf-8")

        conexao = criar_conexao()
        cursor = conexao.cursor()

        usuario_existente = cursor.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (email,)
        ).fetchone()

        if usuario_existente:
            conexao.close()

            flash("Este e-mail já está cadastrado.")

            return redirect(url_for("cadastro"))

        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha)
            VALUES (?, ?, ?)
            """,
            (nome, email, senha_hash)
        )

        conexao.commit()
        conexao.close()

        flash("Conta criada com sucesso!")

        return redirect(url_for("login"))

    return render_template("cadastro.html")


@app.route("/dashboard")
def dashboard():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()

    resultado_receitas = cursor.execute(
        """
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM receitas
        WHERE usuario_id = ?
        """,
        (usuario_id,)
    ).fetchone()

    total_receitas = resultado_receitas["total"]

    # Ainda não temos despesas, então por enquanto fica zero
    resultado_despesas = cursor.execute(
    """
    SELECT COALESCE(SUM(valor), 0) AS total
    FROM despesas
    WHERE usuario_id = ?
    """,
    (usuario_id,)
).fetchone()

    total_despesas = resultado_despesas["total"]

    saldo = total_receitas - total_despesas

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
    (usuario_id, usuario_id)
).fetchall()
    
    
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
         porcentagem = (total_categoria / total_despesas) * 100
        else:
            porcentagem = 0

    categorias_dashboard.append({
        "categoria": item["categoria"],
        "total": total_categoria,
        "porcentagem": porcentagem
    })

    conexao.close()

    return render_template(
        "dashboard.html",
        nome=session["usuario_nome"],
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        saldo=saldo,
        movimentacoes=movimentacoes,
        categorias_dashboard=categorias_dashboard
    )
    
    

@app.route("/receitas", methods=["GET", "POST"])
def receitas():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()

    if request.method == "POST":

        descricao = request.form["descricao"]
        valor = float(request.form["valor"])
        categoria = request.form["categoria"]
        data = request.form["data"]

        cursor.execute(
            """
            INSERT INTO receitas
            (usuario_id, descricao, valor, categoria, data)
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

        return redirect(url_for("receitas"))

    receitas_usuario = cursor.execute(
        """
        SELECT * FROM receitas
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
    
@app.route("/despesas", methods=["GET", "POST"])
def despesas():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = criar_conexao()
    cursor = conexao.cursor()

    if request.method == "POST":

        descricao = request.form["descricao"]
        valor = float(request.form["valor"])
        categoria = request.form["categoria"]
        data = request.form["data"]

        cursor.execute(
            """
            INSERT INTO despesas
            (usuario_id, descricao, valor, categoria, data)
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

        return redirect(url_for("despesas"))

    despesas_usuario = cursor.execute(
        """
        SELECT * FROM despesas
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
    
    
if __name__ == "__main__":
    app.run(debug=True)