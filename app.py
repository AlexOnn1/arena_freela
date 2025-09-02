# Importe o SQLAlchemy
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os, re

# Configuração para o caminho do banco de dados
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
# Configuração do banco de dados
database_url = os.environ.get('DATABASE_URL')
if database_url:
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///' + os.path.join(basedir, 'arena.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- COMANDO PARA CRIAR O BANCO DE DADOS ---
@app.cli.command("create-db")
def create_db():
    """Cria as tabelas do banco de dados."""
    db.create_all()
    print("Tabelas do banco de dados criadas com sucesso!")

# --- NOSSOS MODELOS (TABELAS) ---
class Quadra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), default='Futebol Society', nullable=False)
    preco_por_hora = db.Column(db.Float, nullable=False)

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(100), nullable=False)
    telefone_cliente = db.Column(db.String(20), nullable=False)
    data_hora_inicio = db.Column(db.DateTime, nullable=False)
    data_hora_fim = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='Confirmado', nullable=False)
    quadra_id = db.Column(db.Integer, db.ForeignKey('quadra.id'), nullable=False)

# --- ROTAS DA APLICAÇÃO ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add_quadra')
def add_quadra():
    if Quadra.query.first():
        return "<h1>A quadra principal já existe no banco de dados!</h1>"
    nova_quadra = Quadra(nome='Quadra Principal', preco_por_hora=70.00)
    db.session.add(nova_quadra)
    db.session.commit()
    return "<h1>Quadra 'Quadra Principal' adicionada com sucesso!</h1>"

# --- ROTAS DA API ---
@app.route('/api/quadras')
def get_quadras():
    quadras = Quadra.query.all()
    lista_de_quadras = [{'id': q.id, 'nome': q.nome, 'preco_por_hora': q.preco_por_hora} for q in quadras]
    return jsonify(lista_de_quadras)

@app.route('/api/horarios')
def get_horarios():
    quadra_id = request.args.get('quadra_id')
    data_str = request.args.get('data')

    if not quadra_id or not data_str:
        return jsonify({'erro': 'Parâmetros quadra_id e data são obrigatórios'}), 400

    data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
    agendamentos = Agendamento.query.filter(
        Agendamento.quadra_id == quadra_id,
        db.func.date(Agendamento.data_hora_inicio) == data_selecionada
    ).all()
    horarios_ocupados = [ag.data_hora_inicio.hour for ag in agendamentos]
    return jsonify(horarios_ocupados)

@app.route('/api/agendar', methods=['POST'])
def agendar():
    dados = request.get_json()
    quadra_id = dados.get('quadra_id')
    lista_de_horarios_str = dados.get('horarios')
    nome_cliente = dados.get('nome_cliente')
    telefone_cliente = dados.get('telefone_cliente')

    if not all([quadra_id, lista_de_horarios_str, nome_cliente, telefone_cliente]) or len(nome_cliente.strip()) < 3 or len(re.sub(r'\D', '', telefone_cliente)) < 10:
        return jsonify({'erro': 'Dados inválidos ou incompletos.'}), 400

    for data_hora_str in lista_de_horarios_str:
        data_hora_inicio = datetime.fromisoformat(data_hora_str)
        data_hora_fim = data_hora_inicio + timedelta(hours=1)
        novo_agendamento = Agendamento(
            quadra_id=quadra_id,
            nome_cliente=nome_cliente.strip(),
            telefone_cliente=telefone_cliente,
            data_hora_inicio=data_hora_inicio,
            data_hora_fim=data_hora_fim,
            status='Confirmado'
        )
        db.session.add(novo_agendamento)

    db.session.commit()
    return jsonify({'sucesso': True, 'mensagem': 'Horários agendados com sucesso!'})

if __name__ == '__main__':
    app.run(debug=True)

