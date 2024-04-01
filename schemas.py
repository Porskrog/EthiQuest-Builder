from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Define the schemas for the Stakeholder, Project, and Dilemma classes
# These classes will be used to validate the data received from the client and to serialize the data sent back to the client
# The BaseModel class from Pydantic is used as the base class for the schemas. It provides the necessary functionality for data validation and serialization
# The fields of the schemas are defined as class attributes with type annotations

class Stakeholder(BaseModel):
    name: str
    satisfaction_level: int  # Range from 1-100

class Project(BaseModel):
    name: str
    deadline: datetime
    budget: float
    stakeholders: List[Stakeholder]

class Dilemma(BaseModel):
    description: str
    options: List[str]
    impact_on_stakeholders: Optional[List[str]] = None
