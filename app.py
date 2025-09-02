# Importe o SQLAlchemy
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os, re
# Configuração para o caminho do banco de dados
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
# Configuração do banco de dados SQLite
# A URL do banco de dados de produção será pega da variável de ambiente DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Altera o dialeto para PostgreSQL
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///' + os.path.join(basedir, 'arena.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Opcional: desativa warnings

# Inicializa o banco de dados
db = SQLAlchemy(app)

# --- NOSSOS MODELOS (TABELAS) ---

# Comando customizado para criar as tabelas do banco de dados
@app.cli.command("create-db")
def create_db():
    """Cria as tabelas do banco de dados."""
    db.create_all()
    print("Tabelas do banco de dados criadas com sucesso!")

# ROTA SECRETA E TEMPORÁRIA PARA CRIAR O BANCO DE DADOS EM PRODUÇÃO
@app.route('/setup-database-9a7b3c')
def setup_database():
    try:
        db.create_all()
        return "<h1>Banco de dados e tabelas criados com sucesso!</h1>"
    except Exception as e:
        return f"<h1>Ocorreu um erro ao criar o banco:</h1><p>{e}</p>"

class Quadra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), default='Futebol Society', nullable=False)
    preco_por_hora = db.Column(db.Float, nullable=False)

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Novos campos para o cliente
    nome_cliente = db.Column(db.String(100), nullable=False)
    telefone_cliente = db.Column(db.String(20), nullable=False)
    
    data_hora_inicio = db.Column(db.DateTime, nullable=False)
    data_hora_fim = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='Confirmado', nullable=False)
    
    # Chave Estrangeira (ainda precisamos saber qual quadra foi agendada)
    quadra_id = db.Column(db.Integer, db.ForeignKey('quadra.id'), nullable=False)

# --- FIM DOS MODELOS ---

@app.route('/')
def home():
    # A função render_template vai procurar por 'index.html' na pasta 'templates'
    return render_template('index.html')

# Rota temporária para adicionar uma quadra (depois vamos remover)
@app.route('/add_quadra')
def add_quadra():
    # Verifica se a quadra já existe para não criar duplicatas
    quadra_existente = Quadra.query.first()
    if quadra_existente:
        return "<h1>A quadra principal já existe no banco de dados!</h1>"

    # Cria uma nova quadra com um preço provisório
    nova_quadra = Quadra(nome='Quadra Principal', preco_por_hora=70.00)
    
    # Adiciona a nova quadra à sessão do banco de dados
    db.session.add(nova_quadra)
    # Efetiva a gravação no banco de dados
    db.session.commit()
    
    return "<h1>Quadra 'Quadra Principal' adicionada com sucesso!</h1>"

# API para retornar a lista de quadras em formato JSON
@app.route('/api/quadras')
def get_quadras():
    quadras = Quadra.query.all()
    # Transforma a lista de objetos 'quadra' em uma lista de dicionários
    lista_de_quadras = []
    for quadra in quadras:
        lista_de_quadras.append({
            'id': quadra.id,
            'nome': quadra.nome,
            'preco_por_hora': quadra.preco_por_hora
        })
    return jsonify(lista_de_quadras)

@app.route('/api/horarios')
def get_horarios():
    # Pega os parâmetros da URL, por ex: /api/horarios?quadra_id=1&data=2025-09-02
    quadra_id = request.args.get('quadra_id')
    data_str = request.args.get('data')

    if not quadra_id or not data_str:
        return jsonify({'erro': 'Parâmetros quadra_id e data são obrigatórios'}), 400

    # Converte a string da data para um objeto de data do Python
    data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()

    # Busca no banco de dados
    agendamentos = Agendamento.query.filter(
        Agendamento.quadra_id == quadra_id,
        db.func.date(Agendamento.data_hora_inicio) == data_selecionada
    ).all()

    # Extrai apenas as horas de início dos agendamentos
    horarios_ocupados = [ag.data_hora_inicio.hour for ag in agendamentos]

    return jsonify(horarios_ocupados)

@app.route('/api/agendar', methods=['POST'])
def agendar():
    dados = request.get_json()

    quadra_id = dados.get('quadra_id')
    lista_de_horarios_str = dados.get('horarios')
    nome_cliente = dados.get('nome_cliente')
    telefone_cliente = dados.get('telefone_cliente')

    # --- VALIDAÇÃO NO BACKEND ---
    if not all([quadra_id, lista_de_horarios_str, nome_cliente, telefone_cliente]):
        return jsonify({'erro': 'Dados incompletos.'}), 400
    
    # Valida o nome
    if len(nome_cliente.strip()) < 3:
        return jsonify({'erro': 'O nome deve ter pelo menos 3 caracteres.'}), 400

    # Valida o telefone
    telefone_numeros = re.sub(r'\D', '', telefone_cliente) # Remove não-dígitos
    if len(telefone_numeros) < 10:
        return jsonify({'erro': 'O número de telefone parece inválido.'}), 400
    # --- FIM DA VALIDAÇÃO ---

    for data_hora_str in lista_de_horarios_str:
        data_hora_inicio = datetime.fromisoformat(data_hora_str)
        data_hora_fim = data_hora_inicio + timedelta(hours=1)
        
        novo_agendamento = Agendamento(
            quadra_id=quadra_id,
            nome_cliente=nome_cliente,
            telefone_cliente=telefone_cliente,
            data_hora_inicio=data_hora_inicio,
            data_hora_fim=data_hora_fim,
            status='Confirmado'
        )
        db.session.add(novo_agendamento)

    db.session.commit()
    return jsonify({'sucesso': True, 'mensagem': 'Horários agendados com sucesso!'})
    dados = request.get_json()

    quadra_id = dados.get('quadra_id')
    lista_de_horarios_str = dados.get('horarios') # MUDANÇA: Agora esperamos uma lista chamada 'horarios'
    nome_cliente = dados.get('nome_cliente')
    telefone_cliente = dados.get('telefone_cliente')

    # MUDANÇA: A validação agora usa a lista
    if not all([quadra_id, lista_de_horarios_str, nome_cliente, telefone_cliente]):
        return jsonify({'erro': 'Dados incompletos.'}), 400
    
    # MUDANÇA: Loop para criar um agendamento para cada horário na lista
    for data_hora_str in lista_de_horarios_str:
        data_hora_inicio = datetime.fromisoformat(data_hora_str)
        data_hora_fim = data_hora_inicio + timedelta(hours=1)
        
        novo_agendamento = Agendamento(
            quadra_id=quadra_id,
            nome_cliente=nome_cliente,
            telefone_cliente=telefone_cliente,
            data_hora_inicio=data_hora_inicio,
            data_hora_fim=data_hora_fim,
            status='Confirmado'
        )
        db.session.add(novo_agendamento)

    # Faz o commit no banco apenas uma vez, após adicionar todos
    db.session.commit()

    return jsonify({'sucesso': True, 'mensagem': 'Horários agendados com sucesso!'})
    dados = request.get_json()

    # --- INÍCIO DA MUDANÇA ---
    quadra_id = dados.get('quadra_id')
    data_hora_str = dados.get('data_hora_inicio')
    # Novos campos que virão do frontend
    nome_cliente = dados.get('nome_cliente')
    telefone_cliente = dados.get('telefone_cliente')

    # Validação para os novos campos
    if not all([quadra_id, data_hora_str, nome_cliente, telefone_cliente]):
        return jsonify({'erro': 'Todos os campos são obrigatórios: quadra, data/hora, nome e telefone.'}), 400
    
    data_hora_inicio = datetime.fromisoformat(data_hora_str)
    data_hora_fim = data_hora_inicio + timedelta(hours=1)
    
    # Criando o novo agendamento com os dados do cliente
    novo_agendamento = Agendamento(
        quadra_id=quadra_id,
        nome_cliente=nome_cliente,
        telefone_cliente=telefone_cliente,
        data_hora_inicio=data_hora_inicio,
        data_hora_fim=data_hora_fim,
        status='Confirmado'
    )
    # --- FIM DA MUDANÇA ---

    db.session.add(novo_agendamento)
    db.session.commit()

    return jsonify({'sucesso': True, 'mensagem': 'Horário agendado com sucesso!'})

if __name__ == '__main__':
    app.run(debug=True)