# This is the main file that contains the functions that your Assistant would use to interact with external systems or databases.
# You can define all the functions that your Assistant would need to interact with external systems or databases here.
# This file would be imported in the main Assistant file (assistant.py) and the functions would be called from there.

# Importing required libraries
import os
import sys
import json
import requests
import datetime
import time
import random

# Importing the required libraries for the Assistant
from flask import Flask, request, jsonify
from flask_cors import CORS

# Importing the functions defined in the assistant_functions.py file
from assistant_functions import getCurrentProjectStatus, getStakeholderFeedback

# assistant_functions.py
def getCurrentProjectStatus(location):
    # This function would interact with your database or external systems
    # to get the current project status for the given location
    return "Project status for {} is ...".format(location)

def getStakeholderFeedback(location):
    # This function could fetch feedback from stakeholders for the project in the given location
    return "Stakeholder feedback for {} is ...".format(location)

# Additional functions that your Assistant might need to call can be defined here.

class EthiQuestGame:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key
        self.assistant_id = None  # Set your assistant ID after creation
        self.thread_id = None  # This will hold the ID of the conversation thread

    def start_new_thread(self):
        """
        Start a new conversation thread with OpenAI Assistant to maintain context throughout the game.
        """
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are assisting in generating engaging project dilemmas."}
            ]
        )
        self.thread_id = response['data']['id']

    def get_project_dilemma(self, project_details):
        """
        Generate a project dilemma based on the provided project details using the established thread.
        """
        if not self.thread_id:
            self.start_new_thread()

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": f"Generate a project dilemma that involves a critical project decision, providing 2-3 options with implications for the stakeholders based on: {project_details}"}
            ],
            thread_id=self.thread_id
        )
        dilemma = response.choices[0].message['content']
        return dilemma
            
    def get_project_narrative(self, project_details):
        """
        Generate the initial project narrative based on provided details using the established thread.
        """
        if not self.thread_id:
            self.start_new_thread()

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": f"Generate a project narrative based on: {project_details}"}
            ],
            thread_id=self.thread_id
        )
        narrative = response.choices[0].message['content']
        return narrative

    def update_stakeholders(self, stakeholder_update_info):
        """
        Update stakeholder information based on the latest game developments using the established thread.
        """
        if not self.thread_id:
            self.start_new_thread()

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": f"Update stakeholders based on: {stakeholder_update_info}"}
            ],
            thread_id=self.thread_id
        )
        updated_info = response.choices[0].message['content']
        return updated_info