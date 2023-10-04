from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flow_camp:ghRta9wBEkr2@mysql28.unoeuro.com:3306/flow_camp_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress a warning

# Initialize the database
db = SQLAlchemy(app)

# Add these lines for the Dilemma and Option models
class Dilemma(db.Model):
    __tablename__ = 'Dilemmas'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500))

    # Relationship to the Options table
    options = db.relationship('Option', back_populates='dilemma')

class Option(db.Model):
    __tablename__ = 'Options'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500))
    pros = db.Column(db.String(500))
    cons = db.Column(db.String(500))
    DilemmaID = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'))

    # Relationship to the Dilemmas table
    dilemma = db.relationship('Dilemma', back_populates='options')

@app.route('/add_dilemma', methods=['POST'])
def add_dilemma():
    data = request.get_json()
    new_dilemma = Dilemma(question=data['question'])
    db.session.add(new_dilemma)
    db.session.commit()
    return jsonify({'message': 'New dilemma added'}), 201

@app.route('/get_dilemmas', methods=['GET'])
def get_dilemmas():
    all_dilemmas = Dilemma.query.all()
    output = []

    for dilemma in all_dilemmas:
        dilemma_data = {}
        dilemma_data['id'] = dilemma.id
        dilemma_data['question'] = dilemma.question
        output.append(dilemma_data)

    return jsonify({'dilemmas': output})

@app.route('/add_option/<DilemmaID>', methods=['POST'])
def add_option(DilemmaID):
    data = request.get_json()
    new_option = Option(
        text=data['text'], 
        pros=data['pros'], 
        cons=data['cons'], 
        DilemmaID=DilemmaID
    )
    db.session.add(new_option)
    db.session.commit()
    return jsonify({'message': 'New option added'}), 201

@app.route('/get_options/<DilemmaID>', methods=['GET'])
def get_options(DilemmaID):
    options = Option.query.filter_by(DilemmaID=DilemmaID).all()
    output = []

    for option in options:
        option_data = {}
        option_data['id'] = option.id
        option_data['text'] = option.text
        option_data['pros'] = option.pros
        option_data['cons'] = option.cons
        output.append(option_data)

    return jsonify({'options': output})

@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()