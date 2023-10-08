from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from random import choice 
from datetime import datetime

# Initialize your Flask app here
app = Flask(__name__)
CORS(app)

# Database configurationm  -- new comment
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flow_camp:ghRta9wBEkr2@mysql28.unoeuro.com:3306/flow_camp_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress a warning

# Initialize the database
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Database tables for the Dilemma, Option, Users, UerChoices
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

# Combined User table
class User(db.Model):
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Auto-incrementing ID
    UserID = db.Column(db.String(50), unique=True)  # For registered users
    cookie_id = db.Column(db.String(100), unique=True, nullable=True)  # For anonymous users
    LastVisit = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to UserChoices
    choices = db.relationship('UserChoice', back_populates='user')
    # Relationship to ViewedDilemma
    viewed_dilemmas = db.relationship('ViewedDilemma', back_populates='user')

# UserChoices table
class UserChoice(db.Model):
    __tablename__ = 'UserChoices'
    ChoiceID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.id'))
    DilemmaID = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'))
    OptionID = db.Column(db.Integer, db.ForeignKey('Options.id'))
    Timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='choices')
    option = db.relationship('Option') 

# Veiwed Dilemmas table 
class ViewedDilemma(db.Model):
    __tablename__ = 'ViewedDilemmas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'))
    dilemma_id = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'))
    Timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='viewed_dilemmas')
    dilemma = db.relationship('Dilemma')


# End of Database tables


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

        options = Option.query.filter_by(DilemmaID=dilemma.id).all()
        options_list = []

        for option in options:
            option_data = {}
            option_data['id'] = option.id
            option_data['text'] = option.text
            option_data['pros'] = option.pros
            option_data['cons'] = option.cons
            options_list.append(option_data)

        dilemma_data['options'] = options_list
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

@app.route('/get_random_dilemma', methods=['GET'])
def get_random_dilemma():
    all_dilemmas = Dilemma.query.all()
    
    if not all_dilemmas:
        return jsonify({'message': 'No dilemmas available'}), 404
    
    selected_dilemma = choice(all_dilemmas)
    options = Option.query.filter_by(DilemmaID=selected_dilemma.id).all()

    dilemma_data = {
        'id': selected_dilemma.id,
        'question': selected_dilemma.question,
        'options': [
            {
                'id': option.id,
                'text': option.text,
                'pros': option.pros,
                'cons': option.cons
            } for option in options
        ]
    }

    return jsonify({'dilemma': dilemma_data})

@app.route('/get_option_details/<OptionID>', methods=['GET'])
def get_option_details(OptionID):
    option = Option.query.filter_by(id=OptionID).first()
    if not option:
        return jsonify({'message': 'Option not found'}), 404

    option_data = {
        'id': option.id,
        'text': option.text,
        'pros': option.pros,
        'cons': option.cons
    }

    return jsonify({'option': option_data})

# Store user's choice
@app.route('/store_user_choice', methods=['POST'])
def store_user_choice():
    data = request.get_json()
    cookie_id = data['cookie_id']
    option_id = data['option_id']

    # Check if user exists
    user = User.query.filter_by(cookie_id=cookie_id).first()
    
    # If user doesn't exist, create a new user
    if not user:
        new_user = User(cookie_id=cookie_id)
        db.session.add(new_user)
        db.session.commit()
        user = new_user

    # Store the user's choice
    new_choice = UserChoice(option_id=option_id, user_id=user.id)
    db.session.add(new_choice)
    db.session.commit()

    return jsonify({'message': 'User choice stored successfully'}), 200


@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()