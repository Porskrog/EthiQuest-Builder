from flask import jsonify
from extensions import db
from app import cache
from models import Projects, Dilemma, Option, ContextCharacteristic, DilemmasContextCharacteristic, OptionDilemmaRelation, UserChoice, ViewedDilemma
from sqlalchemy import func, desc
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

# Get project data for a user
def get_project_data(user_id):
    project_data = get_project_data_from_db(user_id)
    # If the user has not been assigned a project, assign one
    if project_data is None:
        project_data = assign_project(user_id)
    # Return the project data
    return project_data

# Get project data for a user from the database
def get_project_data_from_db(user_id):
    # Get the project id for the user
    project_id = get_project_id_for_user(user_id)
    # If the user has not been assigned a project, return None
    if project_id is None:
        return None
    # Get the project data
    project_data = get_project_data_from_id(project_id)
    # Return the project data
    return project_data

