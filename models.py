from extensions import db
from datetime import datetime

##################################################################################
# Database tables for the Dilemmas, Options, ContextCharacteristics, DilemmaContextCharacteristics, Users, UserChoices, ViewedDilemmas  #
##################################################################################

# Dilemmas table
class Dilemma(db.Model):
    __tablename__ = 'Dilemmas'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500))

    # Relationship to the OptionDilemmaRelations table
    option_dilemma_relations = db.relationship('OptionDilemmaRelation', backref='dilemma', lazy=True)

# Options table
class Option(db.Model):
    __tablename__ = 'Options'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500))
    pros = db.Column(db.String(500))
    cons = db.Column(db.String(500))

    # Relationship to the OptionDilemmaRelations table
    option_dilemma_relations = db.relationship('OptionDilemmaRelation', backref='option', lazy=True)

# ContextCharacteristics table
class ContextCharacteristic(db.Model):
    __tablename__ = 'ContextCharacteristics'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

# DilemmasContextCharacteristics table
class DilemmasContextCharacteristic(db.Model):
    __tablename__ = 'DilemmasContextCharacteristics'
    DilemmaID = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'), primary_key=True)
    ContextCharacteristicID = db.Column(db.Integer, db.ForeignKey('ContextCharacteristics.id'), primary_key=True)

# OptionDilemmaRelations table
class OptionDilemmaRelation(db.Model):
    __tablename__ = 'OptionDilemmaRelations'
    id = db.Column(db.Integer, primary_key=True)
    OptionID = db.Column(db.Integer, db.ForeignKey('Options.id'))
    DilemmaID = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'))
    RelationType = db.Column(db.Enum('OptionFor', 'ConsequenceOf'))

# Combined User table
class User(db.Model):
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Auto-incrementing ID
    UserID = db.Column(db.String(50), unique=True)  # For registered users
    cookie_id = db.Column(db.String(100), unique=True, nullable=True)  # For anonymous users
    LastVisit = db.Column(db.DateTime, default=datetime.utcnow)
    user_type = db.Column(db.String(50), nullable=False, default='Free')  # default is 'Free'

    # Relationship to UserChoices
    choices = db.relationship('UserChoice', back_populates='user')
    # Relationship to ViewedDilemmas
    viewed_dilemmas = db.relationship('ViewedDilemma', back_populates='user')

# UserChoices table
class UserChoice(db.Model):
    __tablename__ = 'UserChoices'
    ChoiceID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.id'))
    DilemmaID = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'))
    OptionID = db.Column(db.Integer, db.ForeignKey('Options.id'))
    Timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Users
    user = db.relationship('User', back_populates='choices')
    # Relationship to Options
    option = db.relationship('Option') 

# Veiwed Dilemmas table 
class ViewedDilemma(db.Model):
    __tablename__ = 'ViewedDilemmas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'))
    dilemma_id = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'))
    Timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships to Users
    user = db.relationship('User', back_populates='viewed_dilemmas')
    # Relationship to Dilemmas
    dilemma = db.relationship('Dilemma')


# End of Database tables