import requests
import json
import logging

import plotly.graph_objects as go
import pandas as pd

from typing import List

from .constants import USER, USER
from .utils import handle_exceptions
from .api import OpenMeteoAPI
from .prompts import (
    DETERMINE_VISUALIZATION_TYPE_PROMPT,
    DETERMINE_NEEDED_DATA_PROMPT,
    RETRIEVE_DATA_PROMPT,
    PROCESS_DATA_PROMPT,
    BUILD_VISUALIZATION_PROMPT
)
from .models import (
    VisualizationType,
    DataProcessingType,
    APIEndpoint,
    APIEndpointResponse,
    NormalizedOpenMeteoData,
    ProcessedData,
)
from .ai import anthropic_client




@handle_exceptions()
def determine_visualization_type(
    prompt: str,
    topic_of_interest: str,
    persona: str,
    complexity_level: str,
) -> VisualizationType:
    """
    Determine the visualization type, complexity, and details

    Args:
        prompt (str): User's visualization request
        topic_of_interest (str): Specific climate topic
        persona (str): User persona
        complexity_level (ComplexityLevel): Visualization complexity

    Returns:
        VisualizationType: Detailed visualization specification
    """
    system_prompt = str.format(
        DETERMINE_VISUALIZATION_TYPE_PROMPT,
        topic_of_interest=topic_of_interest,
        persona=persona,
        complexity_level=complexity_level,
    )

    response = anthropic_client.structured_completion(
        messages=[
            {"role": USER, "content": system_prompt},
            {"role": USER, "content": prompt},
        ],
        response_format=VisualizationType,
        max_tokens=1000,
        temperature=.5
    )
    return response


@handle_exceptions()
def determine_needed_data(
    prompt: str, visualization_type: VisualizationType
) -> DataProcessingType:
    """
    Determine data requirements for the visualization

    Args:
        prompt (str): User's visualization request
        visualization (VisualizationType): Visualization details

    Returns:
        DataProcessingType: Data processing and API endpoint specifications
    """

    system_prompt = DETERMINE_NEEDED_DATA_PROMPT.format(
        visualization_type=visualization_type,
        API_ENDPOINT_INFORMATION=OpenMeteoAPI.__str__(),
    )

    response = anthropic_client.structured_completion(
        messages=[
            {"role": USER, "content": system_prompt},
            {"role": USER, "content": prompt},
        ],
        response_format=DataProcessingType,
        max_tokens=1000,
    )
    return response


def build_data_retrieval(
    visualization_type: VisualizationType, needed_data: str
) -> list[APIEndpoint]:
    """
    Build data retrieval queries for the specified visualization and data requirements

    Args:
        visualization (VisualizationType): Visualization details
        needed_data (str): Data requirements

    Returns:
        list[APIEndpoint]: List of API endpoints to query
    """
    system_prompt = str.format(RETRIEVE_DATA_PROMPT, visualization_type=visualization_type, needed_data=needed_data, API_ENDPOINT_INFORMATION=OpenMeteoAPI.__str__())

    response = anthropic_client.structured_completion(
        messages=[
            {"role": USER, "content": system_prompt},
        ],
        response_format=APIEndpointResponse,
        max_tokens=800,
        temperature=.3
    )

    return response


def retrieve_data(api_endpoints: APIEndpointResponse) -> List[NormalizedOpenMeteoData]:
    """
    Retrieve data from multiple API OpenMeteo endpoints
    
    Args:
        api_endpoints (APIEndpointResponse): Object containing list of API endpoints to query
        
    Returns:
        List[NormalizedOpenMeteoData]: List of normalized data objects
    """
    consolidated_data: List[NormalizedOpenMeteoData] = []
    
    for endpoint in api_endpoints.endpoints:
        try:
            response = requests.get(endpoint.url)
            
            if not response.status_code == 200:
                raise ValueError(f"Invalid response status code {response.status_code} from {endpoint.url}")
                
            json_data = response.json()
            if json_data is None:
                raise ValueError(f"Null JSON response from {endpoint.url}")
                
            metadata_df = pd.DataFrame()
            hourly_df = pd.DataFrame()
            daily_df = pd.DataFrame()
            
            if 'hourly' in json_data:
                hourly_df = pd.DataFrame(json_data.pop('hourly'))
                
            # Handle daily data if present
            if 'daily' in json_data:
                daily_df = pd.DataFrame(json_data.pop('daily'))
            
            # Create metadata DataFrame from remaining scalar values
            # Convert to a single-row DataFrame with an explicit index

            metadata_df = pd.DataFrame([json_data])
            
            # Create normalized data object with all fields initialized
            normalized_data = NormalizedOpenMeteoData(
                metadata=metadata_df,
                hourly_data=hourly_df,
                daily_data=daily_df
            )
            
            consolidated_data.append(normalized_data)
            
        except requests.RequestException as e:
            print(f"API Request Error for {endpoint.url}: {str(e)}")
            continue
        except ValueError as e:
            print(f"Data Validation Error for {endpoint.url}: {str(e)}")
            continue
        except Exception as e:
            print(f"Unexpected Error for {endpoint.url}: {str(e)}")
            continue
            
    return consolidated_data


@handle_exceptions()
def process_data(
    visualization_type: VisualizationType, processing_steps: str, data: list[NormalizedOpenMeteoData]
) -> ProcessedData:
    """
    Process data for visualization with dynamic approach

    Args:
        visualization_type (VisualizationType): Visualization specifications
        data (pd.DataFrame): Input data

    Returns:
        ProcessedData: Processed data ready for visualization
    """

    data_description = [entry.__str__() for entry in data]

    system_prompt = str.format(
        PROCESS_DATA_PROMPT, 
        visualization_type=visualization_type, 
        processing_steps=processing_steps, 
        data_description=data_description,
    )

    # Use LLM to dynamically generate data processing code
    response = anthropic_client.completion(
        messages=[
            {"role": USER, "content": system_prompt},
        ],
        max_tokens=700,
        temperature=.8
    )

    try:
        exec(response)
        processed_data: ProcessedData = locals().get("process_raw_data")(data)
        return processed_data

    except Exception as e:
        print(f"Data processing error: {e}")
        return data



@handle_exceptions()
def process_and_viz(data: List[NormalizedOpenMeteoData], visualization_type, complexity_level, processing_steps) -> go.Figure:
    prompt = BUILD_VISUALIZATION_PROMPT.format(
        visualization_type=visualization_type,
        complexity_level=complexity_level,
        processing_steps=processing_steps,
        data_preview=data.__str__()
    )

    response = anthropic_client.completion(
        messages=[
            {"role": USER, "content": prompt},
        ],
        max_tokens=2000,
    )

    exec(response)
    fig = locals().get("visualize")(data)



    return fig

@handle_exceptions(default_return=(None, None))
def visualization_generation_pipeline(
    prompt: str,
    persona: str,
    topic_of_interest: str,
    complexity_level: str,
) -> tuple[go.Figure, pd.DataFrame]:
    """
    Comprehensive visualization generation pipeline

    Args:
        prompt (str): User's visualization request
        persona (str): User persona
        complexity_level (ComplexityLevel): Visualization complexity

    Returns:
        tuple: Generated figure and processed data
    """
    visualization_details: VisualizationType = determine_visualization_type(
        prompt, topic_of_interest, persona, complexity_level
    )
    logging.info(f"Visualization details: {visualization_details}")
    data_requirements: DataProcessingType = determine_needed_data(prompt, visualization_details)

    logging.info(f"Data requirements: {data_requirements}")
    # Retrieve data from specified endpoints
    api_endpoints = build_data_retrieval(
        visualization_details, data_requirements.needed_data
    )

    logging.info(f"Raw data: {api_endpoints}")
    normalized_data = retrieve_data(api_endpoints)

    # Execute visualization generation
    fig = process_and_viz(normalized_data, visualization_details, complexity_level, data_requirements.data_processing_steps)

    return fig, normalized_data
