from typing import Dict 
import requests
import logging
import json
import random

import pandas as pd
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Type
import plotly.graph_objects as go

from .prompts import *
from .models import VisualizationNeed, PersonaSelection, APISelection, ProcessedData, OutputType
from .utils import figure_to_base64, enhance_plotly_figure, handle_exceptions
from .visualization import visualization_generation_pipeline
from .constants import DEVELOPER, USER, DEVELOPER
from .api import APIEndpointRegistry, APIType
from .ai import OpenAIClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s \n\n')

load_dotenv()

openai_client = OpenAIClient()

@handle_exceptions()
def classify_text(text: str, classification_prompt: str, response_format: Type[BaseModel], max_tokens: int = 20) -> BaseModel:
    """
    Classify the given text based on the provided prompt.

    Args:
        text (str): Input text to analyze
        classification_prompt (str): The prompt to use for classification
        response_format (BaseModel): The Pydantic model to use for the response format
        max_tokens (int): The maximum number of tokens to generate
    Returns:
        BaseModel: The classified result parsed into the specified response format
    """
    response = openai_client.structured_completion(
        messages=[
            {"role": DEVELOPER, "content": classification_prompt},
            {
                "role": USER,
                "content": f"Classify this text:\n\n{text}",
            },
        ],
        response_format=response_format,
        max_tokens=max_tokens,
        temperature=0,
    )

    return response

handle_exceptions()
def build_api_query(api_endpoint: str, prompt: str) -> dict:
    """
    Build the query to request the chosen external external API.

    Args:
        api_endpoint (str): The API endpoint to query

    Returns:
        dict: A dictionary of parameters for the API query
    """
    DEVELOPER_prompt = str.format(BUILD_EXTERNAL_QUERY_PROMPT, api_endpoint=api_endpoint, api_endpoint_parameters=APIEndpointRegistry()._get_endpoint_parameters(api_endpoint))

    response = openai_client.structured_completion(
        messages=[
            {"role": DEVELOPER, "content": DEVELOPER_prompt},
            {
                "role": USER,
                "content": prompt,
            },
        ],
        temperature=0,
        response_format=APISelection
        
    )

    result = response.url
    return result



def data_preprocessing(data: pd.DataFrame) -> ProcessedData:
    """
    Preprocess the data by separating nested and non-nested columns into separate dataframes.
    
    Args:
        data (pd.DataFrame): The input dataframe containing potential nested columns
        
    Returns:
        ProcessedData: A container with the main dataframe and dictionary of nested dataframes
    """
    main_data = data.copy()
    nested_dataframes = {}
    
    for column in main_data.columns:
        if (
            len(main_data[column]) > 0 
            and isinstance(main_data[column].iloc[0], (list, dict))
        ):
            nested_df = pd.DataFrame(main_data[column].tolist())
            nested_dataframes[column] = nested_df
            main_data.drop(columns=[column], inplace=True)
    
    return ProcessedData(main_data=main_data, nested_dataframes=nested_dataframes)

handle_exceptions()
def generate_visualization(data: ProcessedData, complexity_level: str, prompt: str) -> dict:
    """
    Generate a visualization based on the given data and complexity level.

    Args:
        data (pd.DataFrame): The dataframe to visualize
        complexity_level (str): The complexity level of the user
        prompt (str): The user's prompt
        additional_data (Dict[str, pd.DataFrame]): Dictionary of additional nested dataframes
    """
    additional_data_description = ProcessedData.generate_description(data.nested_dataframes)

    visualization_prompt = str.format(OLD_GENERATE_VISUALIZATION_PROMPT, data_description=data.main_data.head(), nested_dataframes_description=additional_data_description)
    
    response = openai_client.completion(
        messages=[
            {"role": DEVELOPER, "content": visualization_prompt},
            {"role": DEVELOPER, "content": f"Here is the complexity_level for the user you are going to answer. The visualization should fit {complexity_level}"},
            {
                "role": USER,
                "content": f"{prompt}",
            },
        ],
        max_tokens=5000,
        temperature=1,
    )
    
    return response


handle_exceptions()
def set_complexity_level(persona: str, output_type: OutputType) -> str:
    """
    Set the complexity level based on the persona.

    Args:
        persona (str): The persona name

    Returns:
        str: The complexity level prompt
    """
    with open('personas.json', 'r') as file:
        personas = json.load(file)
    
    user_description = next((p['tuning'] for p in personas if p['name'] == persona), None)
    
    if not user_description:
        raise ValueError(f"Persona '{persona}' not found in personas.json")

    complexity_level = classify_text(user_description, COMPLEXITY_MATCHING_PROMPT, PersonaSelection).persona_id

    if complexity_level == 0:
        return LVL0_VIZ_PROMPT if output_type == OutputType.VISUALIZATION else LVL0_EXP_PROMPT
    elif complexity_level == 1:
        return LVL1_VIZ_PROMPT if output_type == OutputType.VISUALIZATION else LVL1_EXP_PROMPT
    elif complexity_level == 2:
        return LVL2_VIZ_PROMPT if output_type == OutputType.VISUALIZATION else LVL2_EXP_PROMPT
    else:
        raise ValueError("Invalid complexity level")


handle_exceptions()
def describe_visualization(data: ProcessedData, complexity_level: str,fig: go.Figure) -> str:

    """data_description = ""
    data_description += f"describe:{data.main_data.describe()}\n\n"
    for key, value in data.nested_dataframes.items():
        data_description += f"key:{key} \n describe:{value.describe()}\n\n"
"""
    base64_image = figure_to_base64(fig)
    nested_df_info = ProcessedData.generate_description(data.nested_dataframes)
    response = openai_client.completion(
        messages=[
            {"role": DEVELOPER, "content": GENERATE_EXPLANATION_PROMPT},
            {"role": DEVELOPER, "content": complexity_level},
            {"role": USER, "content": [
                {
                    "type": "text",
                    "text": f"Please explain this visualization. Here's a brief description of the data:\n\n{nested_df_info}",
                },
                {
                    "type": "image_url",
                    "image_url": { "url": f"data:image/png;base64,{base64_image}"},
                },
            ]},
        ],
        max_tokens=300,
        temperature=0.7,
    )
    del base64_image
    return response


def main() -> tuple[go.Figure, str]:
    with open('mock.json', 'r') as file:
        conversations = json.load(file)

    conversation = random.choice(conversations)

    for message in conversation['messages']:
        viz_need = classify_text(message['message'], VISUALIZATION_NEED_PROMPT, VisualizationNeed)

        if viz_need.need_visualization:
            logging.info(f"Needed viz : {message['message']}")
            logging.info(f"Topic of interest : {viz_need.topic_of_interest}")

            fig, data = visualization_generation_pipeline()
            fig = enhance_plotly_figure(fig)

            complexity_level = set_complexity_level(message['persona'], OutputType.TEXT)
            description = describe_visualization(data, complexity_level, fig)

            return fig, description




def old_main() -> tuple[callable, pd.DataFrame]:
    with open('mock.json', 'r') as file:
        conversations = json.load(file)

    # Select a random conversation
    # conversation = random.choice(conversations)

    conversation = conversations[0]

    for message in conversation['messages']:
        print(message)
        classified_prompt = classify_text(message['message'], VISUALIZATION_NEED_PROMPT, VisualizationNeed)
        if classified_prompt.need_visualization:
            logging.info(f"Visualization needed for message: {message['message']}")
            
            api_endpoint = classify_text(message['message'], SELECTING_API_PROMPT, APISelection, max_tokens=20).url

            known_endpoints = APIEndpointRegistry.get_endpoints(APIType.OPEN_METEO)
            for endpoint in known_endpoints:
                if api_endpoint == endpoint.full_url:
                    logging.info(f"Selected API endpoint: {api_endpoint}")
                    if api_endpoint:
                        query = build_api_query(api_endpoint, message['message'])
                        logging.info(f"Query {query}")
                    
                        response = requests.get(query)
                        if response.status_code == 200:
                            data = pd.read_json(json.dumps(response.json()))

                            data = data_preprocessing(data)

                            complexity_level = set_complexity_level(message['persona'], OutputType.VISUALIZATION)
                            visualization_code = generate_visualization(data, complexity_level, message['message'])
                            
                            try:
                                exec(visualization_code)
                                fig = locals().get('visualize')(data)
                                fig = enhance_plotly_figure(fig)
                            except Exception:
                                logging.error(f"Error executing visualization:", exc_info=True)
                                return

                            complexity_level = set_complexity_level(message['persona'], OutputType.TEXT)
                            description = describe_visualization(data, complexity_level, fig)

                            return fig, description
                        else:
                            logging.error(f"Error retrieving data: {response.text}")




