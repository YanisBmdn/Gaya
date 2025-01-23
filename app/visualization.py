import string
import requests
from io import StringIO
from typing import Any, Dict, Optional

from dataclasses import dataclass

import plotly.graph_objects as go
import pandas as pd

from .constants import DEVELOPER, USER
from .utils import handle_exceptions
from .main import openai_client
from .prompts import DETERMINE_VISUALIZATION_TYPE_PROMPT, DETERMINE_NEEDED_DATA_PROMPT, RETRIEVE_DATA_PROMPT, PROCESS_DATA_PROMPT, GENERATE_VISUALIZATION_PROMPT

client = openai_client

@dataclass
class VisualizationType():
    visualization: str
    chart_type: str
    focus: str
    visual_elements: str

    def __str__(self):
        return """
        Visualization: {self.visualization}
        Chart Type: {self.chart_type}
        Focus: {self.focus}
        Visual Elements: {self.visual_elements}
        """.format(self=self)

@dataclass
class APIEndpoint:
    url: str
    params: Dict[str, Any]
    data_key: str  # The key to extract from response
    transform_func: Optional[callable] = None  # Optional function to transform the data

@dataclass
class DataProcessingType():
    needed_data: str
    api_endpoints: list[str]
    data_processing_steps: str

    def __str__(self):
        return """
        Data Needed: {self.data_needed}
        API Endpoints: {self.api_endpoints}
        """.format(self=self)

###
# Visualization generation pipeline
###

@handle_exceptions()
def determine_visualization_type(prompt: str, topic_of_interest: str, persona: str) -> str:
    """
    First step of the visualization generation pipeline
    Determine the visualization type that will be generated and the details of the visualization

    Args:
        prompt (str) : The user prompt
        persona (str) : The persona of the user
    Returns:
        VisualizationType : The details of the visualization
    """
    system_prompt = str.format(DETERMINE_VISUALIZATION_TYPE_PROMPT, prompt, topic_of_interest, persona)

    response = client.structured_completion(messages=[
            {"role": DEVELOPER, "content": system_prompt},
            {"role": USER,"content": prompt},
        ],
        response_format=VisualizationType)
    return response


@handle_exceptions()
def determine_needed_data(prompt: str, visualization: VisualizationType) -> DataProcessingType:
    """
    Second step of the visualization generation pipeline
    Determine the data needed for the proposed visualization based on what is available in the known apis and the api endpoints to query
    
    Args:
        prompt (str) : The user prompt
        visualization (VisualizationType) : The visualization details
    Returns:
        str : The data needed for the visualization and the api endpoints to query
    """

    system_prompt = str.format(DETERMINE_NEEDED_DATA_PROMPT, visualization)

    response = client.structured_completion(messages=[
            {"role": DEVELOPER, "content": system_prompt},
            {"role": USER,"content": prompt},
        ],
        response_format=DataProcessingType)
    return response


@handle_exceptions()
def process_data(visualization_type: VisualizationType, data:pd.DataFrame) -> str:
    """
    Fourth step of the visualization generation pipeline
    Provides a function to process the retrieved data to be used in the visualization
    
    Args:
        visualization_type : VisualizationType
        data : pd.DataFrame

    Returns
        str : code to process the data
    """
    response = client.completuion(messages=[
            {"role": DEVELOPER, "content": PROCESS_DATA_PROMPT},
        ])
    return response


@handle_exceptions()
def generate_visualization(prompt: str, persona: str, visualization_details:VisualizationType, visualization_data:dict) -> str:
    """
    Generate Visualization with the processed data
    """
    response = client.completion(messages=[
            {"role": DEVELOPER, "content": GENERATE_VISUALIZATION_PROMPT},
            {"role": USER,"content": prompt},
        ])
    return response


def visualization_generation_pipeline(prompt:str , persona: str) -> tuple[go.Figure, pd.DataFrame]:
    visualization_details = determine_visualization_type(prompt, persona)
    visualization_type = visualization_details.visualization_type

    required_data = determine_needed_data(prompt, visualization_type)

    retrieved_data = []
    for queries in required_data.api_endpoints:
        data = requests.get(queries).json()
        
    data_processing_code = process_data(visualization_type, data)
    exec(data_processing_code)
    processed_data = locals().get('process_data')(data)

    vis_code = generate_visualization(prompt, persona, processed_data)
    exec(vis_code)
    fig = locals().get('visualize')(processed_data)

    return fig, processed_data
    

## def define_visualization_explanation(persona: str, visualization_type: str) -> str:
## def explain_visualization(persona: str, visualization_type: str) -> str: