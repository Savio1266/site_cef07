import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'


import sqlite3
from werkzeug.security import generate_password_hash

# Função para conectar ao banco de dados SQLite
def conectar_bd():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para criar tabelas se elas não existirem
def inicializar_bd():
    conn = conectar_bd()
    cursor = conn.cursor()

    # Criação das tabelas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            status TEXT DEFAULT 'pendente'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS turmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            turno TEXT NOT NULL  -- Adiciona o campo turno
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            turma_id INTEGER,
            FOREIGN KEY (turma_id) REFERENCES turmas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            turma_id INTEGER,
            data TEXT,
            tipo_ocorrencia TEXT,
            motivo TEXT,
            professor TEXT,
            chamar_responsavel TEXT,
            data_reuniao TEXT,
            hora_reuniao TEXT,
            total_dias INTEGER DEFAULT 0,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id),
            FOREIGN KEY (turma_id) REFERENCES turmas(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responsaveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            aluno_id INTEGER,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id)
        )
    ''')

    # Verificar se o moderador "SAVIO" já existe, caso contrário, adicioná-lo
    cursor.execute("SELECT * FROM professores WHERE login = ?", ('SAVIO',))
    if not cursor.fetchone():
        senha_hash = generate_password_hash('Ws396525$')
        cursor.execute("INSERT INTO professores (login, senha, status) VALUES (?, ?, 'aprovado')",
                       ('SAVIO', senha_hash))
        conn.commit()

    cursor.close()
    conn.close()

# Função para atualizar o banco de dados, adicionando colunas se necessário
def atualizar_bd():
    conn = conectar_bd()
    cursor = conn.cursor()

    # Adiciona coluna 'turno' na tabela turmas, se não existir
    try:
        cursor.execute("ALTER TABLE turmas ADD COLUMN turno TEXT NOT NULL DEFAULT 'Matutino'")
        conn.commit()
    except sqlite3.OperationalError:
        print("A coluna 'turno' já existe.")

    # Adiciona coluna 'total_dias' se não existir
    try:
        cursor.execute("ALTER TABLE ocorrencias ADD COLUMN total_dias INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        print("A coluna 'total_dias' já existe.")

    # Adiciona coluna 'status' na tabela professores, se não existir
    try:
        cursor.execute("ALTER TABLE professores ADD COLUMN status TEXT DEFAULT 'pendente'")
        conn.commit()
    except sqlite3.OperationalError:
        print("A coluna 'status' já existe.")

    cursor.close()
    conn.close()

# Chamada para criar e atualizar o banco de dados
inicializar_bd()
atualizar_bd()



# Página inicial
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT senha, status FROM professores WHERE login = ?", (usuario,))
        data = cursor.fetchone()
        conn.close()

        if data and check_password_hash(data[0], senha):
            if usuario == 'SAVIO':
                session['usuario'] = usuario
                return redirect(url_for('aprovar_professores'))
            elif data[1] == 'aprovado':
                session['usuario'] = usuario
                return redirect(url_for('area_professor'))
            else:
                session['mensagem'] = "Seu cadastro ainda está pendente de aprovação pelo moderador."
                return redirect(url_for('login'))
        else:
            return "Login ou senha inválidos."

    mensagem = session.pop('mensagem', None)
    return render_template('login_professor.html', mensagem=mensagem)


@app.route('/cadastro_professor_login', methods=['GET', 'POST'])
def cadastro_professor_login():
    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']
        senha_hash = generate_password_hash(senha)

        conn = conectar_bd()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM professores WHERE login = ?", (login,))
        professor_existente = cursor.fetchone()

        if professor_existente:
            session['mensagem'] = "Este login já está em uso. Por favor, escolha outro."
            cursor.close()
            conn.close()
            return redirect(url_for('cadastro_professor_login'))

        cursor.execute(
            "INSERT INTO professores (login, senha, status) VALUES (?, ?, 'pendente')",
            (login, senha_hash)
        )
        conn.commit()
        cursor.close()
        conn.close()

        session['mensagem'] = "Seu cadastro foi realizado e está pendente de aprovação pelo moderador."
        return redirect(url_for('login'))

    return render_template('cadastro_professor_login.html')


@app.route('/area_professor')
def area_professor():
    if 'usuario' in session:
        return render_template('area_professor.html')
    return redirect(url_for('login'))

# Cadastro de professor
@app.route('/cadastrar_professor', methods=['GET', 'POST'])
def cadastrar_professor():
    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']
        senha_hash = generate_password_hash(senha)

        conn = conectar_bd()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO professores (login, senha, status) VALUES (?, ?, 'pendente')",
                       (login, senha_hash))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('area_professor'))

    return render_template('cadastro_professor.html')


@app.route('/aprovar_professores', methods=['GET', 'POST'])
def aprovar_professores():
    # Verificar se o usuário logado é o moderador "SAVIO"
    if 'usuario' not in session or session['usuario'] != 'SAVIO':
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute("SELECT id, login FROM professores WHERE status = 'pendente'")
    professores_pendentes = cursor.fetchall()

    if request.method == 'POST':
        action = request.form['action']
        professor_id = int(action.split('_')[1])  # Extrair o ID do professor da ação

        if 'aprovar' in action:
            cursor.execute("UPDATE professores SET status = 'aprovado' WHERE id = ?", (professor_id,))
        elif 'rejeitar' in action:
            cursor.execute("DELETE FROM professores WHERE id = ?", (professor_id,))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('aprovar_professores'))

    cursor.close()
    conn.close()
    return render_template('aprovar_professores.html', professores=professores_pendentes)


# Rota para o moderador limpar o banco de dados
@app.route('/limpar_banco_dados', methods=['POST'])
def limpar_banco_dados():
    if 'usuario' not in session or session['usuario'] != 'SAVIO':
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM ocorrencias")
        cursor.execute("DELETE FROM responsaveis")
        cursor.execute("DELETE FROM alunos")
        cursor.execute("DELETE FROM turmas")
        cursor.execute("DELETE FROM professores WHERE login != 'SAVIO'")
        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"Erro ao limpar o banco de dados: {e}"
    finally:
        cursor.close()
        conn.close()

    return "Banco de dados limpo com sucesso!"


# Login do responsável
@app.route('/login_responsavel', methods=['GET', 'POST'])
def login_responsavel():
    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT senha, aluno_id FROM responsaveis WHERE login = ?", (login,))
        data = cursor.fetchone()
        conn.close()

        if data and check_password_hash(data[0], senha):
            session['responsavel'] = login
            session['aluno_id'] = data[1]
            return redirect(url_for('area_responsavel'))
        else:
            return "Login ou senha inválidos."

    return render_template('login_responsavel.html')


# Página principal do responsável, mostrando as ocorrências do aluno
@app.route('/area_responsavel')
def area_responsavel():
    if 'responsavel' not in session:
        return redirect(url_for('login_responsavel'))

    aluno_id = session.get('aluno_id')

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT alunos.nome, turmas.nome, ocorrencias.data, ocorrencias.tipo_ocorrencia, ocorrencias.motivo, 
               ocorrencias.total_dias, ocorrencias.chamar_responsavel, 
               COALESCE(ocorrencias.data_reuniao, 'N/A'), 
               COALESCE(ocorrencias.hora_reuniao, 'N/A')
        FROM alunos
        JOIN turmas ON alunos.turma_id = turmas.id
        LEFT JOIN ocorrencias ON alunos.id = ocorrencias.aluno_id
        WHERE alunos.id = ?
        ORDER BY ocorrencias.data DESC
    ''', (aluno_id,))
    ocorrencias = cursor.fetchall()
    conn.close()

    aluno_nome = ocorrencias[0][0] if ocorrencias else None

    return render_template('area_responsavel.html', aluno_nome=aluno_nome, ocorrencias=ocorrencias)


@app.route('/cadastrar_aluno', methods=['GET', 'POST'])
def cadastrar_aluno():
    if request.method == 'POST':
        nomes_alunos = request.form.getlist('nome_aluno[]')
        turma_id = request.form['turma_id']

        conn = conectar_bd()
        cursor = conn.cursor()

        for nome_aluno in nomes_alunos:
            cursor.execute("INSERT INTO alunos (nome, turma_id) VALUES (?, ?)", (nome_aluno, turma_id))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('cadastrar_aluno'))

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, turno FROM turmas")  # Certifique-se de que o turno está sendo selecionado
    turmas = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('cadastro_aluno.html', turmas=turmas)



@app.route('/cadastrar_turma', methods=['GET', 'POST'])
def cadastrar_turma():
    if request.method == 'POST':
        # Lógica para cadastrar turma
        nome_turma = request.form['nome_turma']
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO turmas (nome) VALUES (?)", (nome_turma,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('area_professor'))

    # Renderize o template de cadastro de turma
    return render_template('cadastro_turma.html')



# Cadastro do responsável
@app.route('/cadastrar_responsavel', methods=['GET', 'POST'])
def cadastrar_responsavel():
    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']
        turma_id = request.form['turma_id']
        aluno_id = request.form['aluno_id']

        conn = conectar_bd()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM responsaveis WHERE aluno_id = ?", (aluno_id,))
        num_responsaveis = cursor.fetchone()[0]

        if num_responsaveis >= 2:
            cursor.close()
            conn.close()
            return "Este aluno já possui dois responsáveis cadastrados."

        senha_hash = generate_password_hash(senha)
        cursor.execute("INSERT INTO responsaveis (login, senha, aluno_id) VALUES (?, ?, ?)",
                       (login, senha_hash, aluno_id))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('login_responsavel'))

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('cadastrar_responsavel.html', turmas=turmas)


# Registro de ocorrências
@app.route('/registrar_ocorrencia', methods=['GET', 'POST'])
def registrar_ocorrencia():
    if request.method == 'POST':
        turma_id = request.form['turma_id']
        aluno_id = request.form['aluno_id']
        data_ocorrencia = request.form['data_ocorrencia']
        tipo_ocorrencia = request.form['tipo_ocorrencia']
        motivo = request.form['motivo']
        professor = request.form['professor']
        chamar_responsavel = request.form.get('chamar_responsavel', 'nao')
        data_reuniao = request.form.get('data_reuniao')
        hora_reuniao = request.form.get('hora_reuniao')
        total_dias = request.form.get('total_dias', 0) if tipo_ocorrencia == 'SUSPENSAO' else 0

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ocorrencias (aluno_id, turma_id, data, tipo_ocorrencia, motivo, professor, 
                                     chamar_responsavel, data_reuniao, hora_reuniao, total_dias)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (aluno_id, turma_id, data_ocorrencia, tipo_ocorrencia, motivo, professor,
              chamar_responsavel, data_reuniao, hora_reuniao, total_dias))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('area_professor'))

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()
    cursor.execute("SELECT id, nome FROM alunos")
    alunos = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('registro_ocorrencia.html', turmas=turmas, alunos=alunos)

# Visualizar ocorrências por turma
@app.route('/visualizar_ocorrencias', methods=['GET'])
def visualizar_ocorrencias():
    conn = conectar_bd()
    cursor = conn.cursor()

    # Obter todas as turmas para a seleção no formulário
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()

    # Obter o id da turma selecionada
    turma_id = request.args.get('turma_id')
    ocorrencias = []

    # Verificar se uma turma foi selecionada para filtrar as ocorrências
    if turma_id:
        cursor.execute('''
            SELECT ocorrencias.id, alunos.nome AS aluno_nome, turmas.nome AS turma_nome, ocorrencias.data, 
                   ocorrencias.tipo_ocorrencia, ocorrencias.motivo, ocorrencias.total_dias, 
                   ocorrencias.chamar_responsavel, COALESCE(ocorrencias.data_reuniao, 'N/A') AS data_reuniao, 
                   COALESCE(ocorrencias.hora_reuniao, 'N/A') AS hora_reuniao
            FROM ocorrencias
            JOIN alunos ON ocorrencias.aluno_id = alunos.id
            JOIN turmas ON alunos.turma_id = turmas.id
            WHERE turmas.id = ?
            ORDER BY ocorrencias.data DESC
        ''', (turma_id,))
        ocorrencias = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('visualizar_ocorrencias.html', ocorrencias=ocorrencias, turmas=turmas, turma_selecionada=turma_id)



# Excluir professor
@app.route('/excluir_professor', methods=['GET', 'POST'])
def excluir_professor():
    if request.method == 'POST':
        professor_id = request.form['professor_id']
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM professores WHERE id = ?", (professor_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('area_professor'))

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, login FROM professores")
    professores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('excluir_professor.html', professores=professores)


# Excluir turma
@app.route('/excluir_turma', methods=['GET', 'POST'])
def excluir_turma():
    if request.method == 'POST':
        turma_id = request.form['turma_id']

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM alunos WHERE turma_id = ?", (turma_id,))
        num_alunos = cursor.fetchone()[0]

        if num_alunos > 0:
            cursor.close()
            conn.close()
            return "Não é possível excluir a turma, pois há alunos associados a ela."

        cursor.execute("DELETE FROM turmas WHERE id = ?", (turma_id,))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('area_professor'))

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('excluir_turma.html', turmas=turmas)


@app.route('/excluir_aluno/turmas')
def excluir_aluno_turmas():
    """Exibe todas as turmas para escolher uma ao excluir um aluno."""
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('excluir_aluno_turmas.html', turmas=turmas)


@app.route('/excluir_aluno/turma/<int:turma_id>', methods=['GET', 'POST'])
def excluir_aluno_turma(turma_id):
    """Exclui um aluno específico de uma turma."""
    conn = conectar_bd()
    cursor = conn.cursor()

    if request.method == 'POST':
        aluno_id = request.form['aluno_id']

        # Verificar se o aluno possui ocorrências associadas
        cursor.execute("SELECT COUNT(*) FROM ocorrencias WHERE aluno_id = ?", (aluno_id,))
        num_ocorrencias = cursor.fetchone()[0]

        # Verificar se o aluno possui responsáveis associados
        cursor.execute("SELECT COUNT(*) FROM responsaveis WHERE aluno_id = ?", (aluno_id,))
        num_responsaveis = cursor.fetchone()[0]

        # Mensagem de erro se o aluno possuir ocorrências ou responsáveis
        if num_ocorrencias > 0 or num_responsaveis > 0:
            cursor.close()
            conn.close()
            mensagem = "Não é possível excluir o aluno porque ele possui "
            if num_ocorrencias > 0:
                mensagem += "ocorrências associadas. "
            if num_responsaveis > 0:
                mensagem += "responsáveis associados. "
            mensagem += "Exclua as ocorrências e/ou responsáveis antes de tentar novamente."
            return mensagem

        # Excluir o aluno se não houver ocorrências ou responsáveis associados
        cursor.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
        conn.commit()

        cursor.close()
        conn.close()
        # Redireciona para a rota de visualização de turmas para exclusão
        return redirect(url_for('excluir_aluno_turmas'))

    # Buscar todos os alunos da turma selecionada para exibição
    cursor.execute("SELECT id, nome FROM alunos WHERE turma_id = ?", (turma_id,))
    alunos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('excluir_aluno.html', turma=turma_id, alunos=alunos)



# Excluir ocorrência
@app.route('/excluir_ocorrencia', methods=['GET', 'POST'])
def excluir_ocorrencia():
    conn = conectar_bd()
    cursor = conn.cursor()

    if request.method == 'POST':
        ocorrencia_id = request.form['ocorrencia_id']
        cursor.execute("DELETE FROM ocorrencias WHERE id = ?", (ocorrencia_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('excluir_ocorrencia'))

    cursor.execute('''
        SELECT ocorrencias.id, alunos.nome, turmas.nome, ocorrencias.data, ocorrencias.tipo_ocorrencia, ocorrencias.motivo
        FROM ocorrencias
        JOIN alunos ON ocorrencias.aluno_id = alunos.id
        JOIN turmas ON ocorrencias.turma_id = turmas.id
        ORDER BY ocorrencias.data DESC
    ''')
    ocorrencias = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('excluir_ocorrencia.html', ocorrencias=ocorrencias)


# Visualizar turmas
@app.route('/visualizar_turmas')
def visualizar_turmas():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('visualizar_turmas.html', turmas=turmas)


# Visualizar professores
@app.route('/visualizar_professores')
def visualizar_professores():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, login FROM professores")
    professores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('visualizar_professores.html', professores=professores)


# Visualizar responsáveis
@app.route('/visualizar_responsaveis', methods=['GET'])
def visualizar_responsaveis():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()

    turma_id = request.args.get('turma_id')
    responsaveis = []
    if turma_id:
        cursor.execute('''
            SELECT responsaveis.login, alunos.nome, responsaveis.id
            FROM responsaveis
            JOIN alunos ON responsaveis.aluno_id = alunos.id
            WHERE alunos.turma_id = ?
        ''', (turma_id,))
        responsaveis = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('visualizar_responsaveis.html', turmas=turmas, responsaveis=responsaveis)


# Excluir responsável
@app.route('/excluir_responsavel', methods=['POST'])
def excluir_responsavel():
    responsavel_id = request.form['responsavel_id']

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM responsaveis WHERE id = ?", (responsavel_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('visualizar_responsaveis'))


# Visualizar alunos de uma turma
@app.route('/visualizar_turmas/<int:turma_id>')
def visualizar_alunos_turma(turma_id):
    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute("SELECT nome FROM turmas WHERE id = ?", (turma_id,))
    turma = cursor.fetchone()

    cursor.execute("SELECT id, nome FROM alunos WHERE turma_id = ?", (turma_id,))
    alunos = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('visualizar_alunos_turma.html', turma=turma, alunos=alunos)


# Obter alunos de uma turma em formato JSON
@app.route('/get_alunos/<int:turma_id>')
def get_alunos(turma_id):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM alunos WHERE turma_id = ?", (turma_id,))
    alunos = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([{'id': aluno[0], 'nome': aluno[1]} for aluno in alunos])


# Rota para obter alunos de uma turma em formato JSON
@app.route('/get_alunos_turma/<int:turma_id>')
def get_alunos_turma(turma_id):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM alunos WHERE turma_id = ?", (turma_id,))
    alunos = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([{'id': aluno['id'], 'nome': aluno['nome']} for aluno in alunos])


if __name__ == '__main__':
    app.run(debug=True)
