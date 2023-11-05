from extensions import db
from datetime import datetime

##################################################################################
# Database tables for the Dilemmas, Options, ContextCharacteristics, DilemmaContextCharacteristics, Users, UserChoices, ViewedDilemmas  #
##################################################################################

# Projects table
class Project(db.Model):
    __tablename__ = 'Projects'
    id = db.Column(Integer, primary_key=True)
    Name = db.Column(String(255), nullable=False)
    Budget = db.Column(BIGINT)
    Currency = db.Column(String(3), nullable=False, default="USD")
    Timeline = db.Column(String(100))
    PlannedStart = db.Column(Date, nullable=False)
    ActualStart = db.Column(Date, nullable=False)
    PlannedEnd = db.Column(Date, nullable=False)
    EstimatedCompletion = db.Column(Date, nullable=False)
    Scope = db.Column(Text)
    TeamSize = db.Column(Integer)
    Description = db.Column(Text)
    QualitativeBenefits = db.Column(Text)
    ExpectedROI = db.Column(DECIMAL(10,2))
    CostSavings = db.Column(BIGINT)
    EfficiencyGain = db.Column(DECIMAL(10,2))
    SpentToDate = db.Column(Integer, nullable=False)
    ProjectedCostAtCompletion = db.Column(Integer, nullable=False)
    CurrentCostOverrun = db.Column(Integer, nullable=False)
    ContingencyReserve = db.Column(Integer, nullable=False)
    
    # User Project Relations
    user_project_relations = db.relationship('UserProjectRelation', backref='project', lazy=True)

    # Project Stakeholder Relations
    project_stakeholder_relations = db.relationship('ProjectStakeholder', backref='project', lazy=True)

    # Project Risk Relations
    project_risk_relations = db.relationship('Risks', backref='project', lazy=True)


# ProjectStakeholders table
class ProjectStakeholder(db.Model):
    __tablename__ = 'ProjectStakeholders'
    ProjectID = db.Column(Integer, primary_key=True, db.ForeignKey('Projects.id'))
    StakeholderID = db.Column(Integer, primary_key=True, db.ForeignKey('Stakeholders.id'))
    RoleID = db.Column(Integer, primary_key=True, db.ForeignKey('StakeholderRoles.id'))

# Stakeholders table
class Stakeholder(db.Model):
    __tablename__ = "Stakeholders"
    id = db.Column(Integer, primary_key=True)
    Name = db.Column(String(255), nullable=False)
    Notes = db.Column(Text)

# Roles table
class Role(db.Model):
    __tablename__ = "StakeholderRoles"
    id = db.Column(Integer, primary_key=True)
    Name = db.Column(String(255), nullable=False)
    Notes = db.Column(Text)


# ProjectRisks table
class Risks(db.Model):
    __tablename__ = 'Risks'
    id = db.Column(db.Integer, primary_key=True)
    ProjectID = db.Column(db.Integer, db.ForeignKey('Projects.id'))
    IdentifiedBy = db.Column(db.Integer, db.ForeignKey('Stakeholders.id'))
    CurrentConcern = db.Column(Text)
    PotentialEvent = db.Column(Text)
    PotentialImpact = db.Column(Text)
    Likelihood = db.Column(Enum('Low', 'Medium', 'High'))
    MitigationStrategies = db.Column(Text)
    Status = db.Column(Enum('Open', 'In Progress', 'Closed', 'Realized'), default='Open')
    Acknowledged = db.Column(TINYINT(1), default=0)
    ActionTaken = db.Column(TINYINT(1), default=0)
    DateIdentified = db.Column(Date)
    DateAcknowledged = db.Column(Date)
    DateActionTaken = db.Column(Date)
    DateResolved = db.Column(Date)

    # Project Risk relations - backreference to foreign key from Projects table
    project_risk_relations = db.relationship('ProjectRisk', backref='risk', lazy=True)

# ProjectUserRelations table
class UserProjectRelation(db.Model):
    __tablename__ = 'UserProjectRelations'
    UserProjectRelationID = db.Column(Integer, primary_key=True)
    ProjectID = db.Column(Integer, db.ForeignKey('Projects.id'))
    UserID = db.Column(Integer, db.ForeignKey('Users.id'))


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

class Category(db.Model):
    __tablename__ = 'Category'
    CategoryID = db.Column(db.Integer, primary_key=True)
    CategoryName = db.Column(db.String(50))
    CategoryTypeID = db.Column(db.Integer, db.ForeignKey('CategoryType.CategoryTypeID'))
    Weight = db.Column(db.Integer)

class CategoryType(db.Model):
    __tablename__ = 'CategoryType'
    CategoryTypeID = db.Column(db.Integer, primary_key=True)
    TypeName = db.Column(db.String(50))

    # Relationship to Category
    categories = db.relationship('Category', backref='type', lazy=True)
    
# Association table for the many-to-many relationship between Dilemmas and Category
class DilemmaCategory(db.Model):
    __tablename__ = 'DilemmaCategory'
    DilemmaID = db.Column(db.Integer, db.ForeignKey('Dilemmas.id'), primary_key=True)
    CategoryID = db.Column(db.Integer, db.ForeignKey('Category.CategoryID'), primary_key=True)

# Combined User table
class User(db.Model):
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Auto-incrementing ID
    UserID = db.Column(db.String(50), unique=True)  # For registered users
    cookie_id = db.Column(db.String(100), unique=True, nullable=True)  # For anonymous users
    LastVisit = db.Column(db.DateTime, default=datetime.utcnow)
    user_type = db.Column(db.String(50), nullable=False, default='Free')  # default is 'Free'
    Random = db.Column(db.String(5), default=True)
    Consequential = db.Column(db.String(5), default=False)

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