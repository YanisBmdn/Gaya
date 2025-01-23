from enum import Enum
import json

from dataclasses import dataclass
from typing import Dict, List, Optional


class APIType(Enum):
    """
    Enum representing supported API types with their known endpoints.
    """
    OPEN_METEO = {
        'base_endpoints': [
            'archive',
            'air-quality',
        ],
        'base_url': 'https://{endpoint}-api.open-meteo.com/v1/{endpoint}'
    }

    def get_endpoints(self) -> List[str]:
        """
        Retrieve available endpoints for the API type.
        
        Returns:
            List[str]: List of available endpoints
        """
        return self.value['base_endpoints']

    def construct_url(self, endpoint: str) -> str:
        """
        Construct the full URL for a given endpoint.
        
        Args:
            endpoint (str): The specific endpoint
        
        Returns:
            str: Fully constructed URL
        
        Raises:
            ValueError: If the endpoint is not available for this API type
        """
        if endpoint not in self.get_endpoints():
            raise ValueError(f"Endpoint {endpoint} not available for {self.name}")
        
        return self.value['base_url'].format(endpoint=endpoint)

@dataclass
class APIEndpointInfo:
    """
    Dataclass to provide detailed information about API endpoints.
    """
    api_type: APIType
    endpoint: str
    full_url: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, str]] = None

class APIEndpointRegistry:
    """
    A registry to manage and provide information about API endpoints.
    """
    @classmethod
    def get_endpoints(cls, api_type: APIType) -> List[APIEndpointInfo]:
        """
        Retrieve detailed information about all endpoints for a given API type.
        
        Args:
            api_type (APIType): The API type to retrieve endpoints for
        
        Returns:
            List[APIEndpointInfo]: Detailed endpoint information
        """
        endpoints = []
        for endpoint in api_type.get_endpoints():
            endpoints.append(
                APIEndpointInfo(
                    api_type=api_type,
                    endpoint=endpoint,
                    full_url=api_type.construct_url(endpoint),
                    # You can add more details here as needed
                    description=cls._get_endpoint_description(api_type, endpoint)
                )
            )
        return endpoints

    @staticmethod
    def _get_endpoint_description(api_type: APIType, endpoint: str) -> Optional[str]:
        """
        Provide a description for a specific endpoint.
        This is a placeholder method that can be expanded with more detailed descriptions.
        
        Args:
            api_type (APIType): The API type
            endpoint (str): The specific endpoint
        
        Returns:
            Optional[str]: A description of the endpoint
        """
        # Example descriptions - these would ideally come from API documentation
        descriptions = {
            APIType.OPEN_METEO: {
                'forecast': 'Forecast weather data',
                'air-quality': 'Air quality measurements and forecasts',
                'flood': 'Flood monitoring and prediction',
                'geocoding': 'Geographic location and coordinate services',
                'marine': 'Marine and oceanic weather data'
            }
        }
        
        return descriptions.get(api_type, {}).get(endpoint, "No description available")
    
    @staticmethod
    def _get_endpoint_parameters(url: str) -> Optional[Dict[str, str]]:
        """
        Provide parameter information for a specific endpoint.
        """

        with open('known_apis.json', 'r') as file:
            parameters = json.load(file)

        return parameters[url]
    
    @staticmethod
    def construct_url(endpoint: str) -> str:
        """
        Construct the URL for a given endpoint by automatically determining its API type.
        
        Args:
            endpoint (str): The endpoint to construct the URL for
        
        Returns:
            str: The constructed URL
        
        Raises:
            ValueError: If the endpoint does not belong to any API type
        """
        for api_type in APIType:
            if endpoint in api_type.get_endpoints():
                return api_type.construct_url(endpoint)
        
        raise ValueError(f"Endpoint {endpoint} does not match any known API type")