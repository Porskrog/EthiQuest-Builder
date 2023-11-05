from flask import jsonify
from extensions import db
from app import cache
from models import Project, UserProjectRelation, Stakeholder, Role, ProjectStakeholder, Risks 
from sqlalchemy import func, desc, Integer, String, Text, Date, BIGINT, DECIMAL
from random import choice
from datetime import datetime
import logging

HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_CREATED = 201

logging.basicConfig(level=logging.INFO)

######################################################################################################
# Utility Functions - getting and storing project data for users                                     #
######################################################################################################

# Get all projects from the database
def get_all_projects():
    projects = Project.query.all()
    return projects

# Get all projects chosen by a user
def get_user_projects(user_id):
    user_projects = Project.query.join(UserProjectRelation).filter(UserProjectRelation.UserID == user_id).all()
    return user_projects

# Get all stakeholders for a project including their roles
def get_project_stakeholders_with_roles(project_id):
    project_stakeholders = Stakeholder.query.join(ProjectStakeholder).join(Role).filter(ProjectStakeholder.ProjectID == project_id).all()
    return project_stakeholders



