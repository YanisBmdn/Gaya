from dataclasses import dataclass
from pydantic import BaseModel
from typing import Dict
from enum import Enum
import pandas as pd

@dataclass
class VisualizationNeed(BaseModel):
    need_visualization: int
    topic_of_interest: str

@dataclass
class PersonaSelection(BaseModel):
    persona_id: int

@dataclass
class APISelection(BaseModel):
    url: str

@dataclass
class VisualizationType(BaseModel):
    json_definition: str

@dataclass
class ProcessedData:
    """
    A generic container for preprocessed dataframes.
    
    Attributes:
        main_data (pd.DataFrame): The base dataframe with non-nested columns
        nested_dataframes (Dict[str, pd.DataFrame]): Dictionary of expanded nested dataframes
    """
    main_data: pd.DataFrame
    nested_dataframes: Dict[str, pd.DataFrame]

    @staticmethod
    def generate_description(dataframes_dict: Dict[str, pd.DataFrame]) -> str:
        """
        Generate a formatted description of multiple dataframes
        Args:
            dataframes_dict: Dictionary of dataframe name and corresponding dataframe
        Returns:
            Formatted string describing each dataframe
        """
        if not dataframes_dict:
            return ""
            
        descriptions = []
        for name, df in dataframes_dict.items():
            descriptions.append(
                f"Dataset: {name}\n"
                f"Preview:\n{df.head()}\n"
                f"Shape: {df.shape}"
            )
            
        return "\n\n".join(descriptions)

class OutputType(Enum):
    VISUALIZATION = "visualization"
    TEXT = "text"