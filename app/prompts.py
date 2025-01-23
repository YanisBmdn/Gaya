from app.api import APIEndpointRegistry, APIType

#########################
## Classification Prompts
#########################

VISUALIZATION_NEED_PROMPT = """
You are a precise classifier. Determine if the given text suggests a need for environmental data visualization.
Set the need_visualization variable ONLY to 1 if visualization is needed, or 0 if not.
Set the topic_of_interest variable to the main topic of interest mentioned in the text (e.g., temperature trends, air quality, precipitation).
Consider broad interpretations of visualization needs, including trends, patterns, comparisons, or spatial/temporal analyses.
"""

COMPLEXITY_MATCHING_PROMPT = """
You are a difficulty level matcher. Identify the content difficulty level based on the given user persona.
Choose the most suitable complexity level from the following options:

0 - Beginner: Simple language, basic explanations, analogies, and no jargon. Focus on foundational understanding and curiosity.

1 - Intermediate: Clear technical terms, moderate-depth analysis, connections between trends, and balanced detail with accessible narrative.

2 - Expert: In-depth technical analysis, precise scientific language, advanced models, and nuanced insights with a scholarly tone.
"""

SELECTING_API_PROMPT = f"""
You are an API expert. Choose the best API for the given user demand.
Select from the following endpoints : {APIEndpointRegistry().get_endpoints(APIType.OPEN_METEO)}
You should ONLY return the full URL for the selected endpoint.
"""

########################
## Visualization Prompts
########################

DETERMINE_VISUALIZATION_TYPE_PROMPT = """
Recommend an impactful climate change visualization using OpenMeteo historical data for the following:

Topic: {topic_of_interest}
User Persona: {persona}

Provide your recommendation in this format:
1. Visualization Name: [Clear, descriptive title emphasizing climate change aspect]
2. Chart Type: [Specific visualization format]
3. Climate Change Focus: [What aspect this visualization reveals]
4. Visual Elements: [Key required components]

Guidelines:
- Focus on long-term patterns over weather
- Emphasize trend detection
- Include relevant baselines
- Match complexity to user expertise level
- Prioritize clear climate change communication

Reference Examples by Complexity:

1. Beginner Level:
Visualization Name: "Yearly Temperature Change"
Chart Type: Line chart
Climate Change Focus: Simple yearly temperature trend
Visual Elements:
- Single line of yearly average temperatures
- X-axis: years (2000-2023)
- Y-axis: temperature in °C

2. Intermediate Level:
Visualization Name: "Temperature Trends with 5-Year Average"
Chart Type: Line chart with moving average
Climate Change Focus: Long-term temperature patterns
Visual Elements:
- Raw temperature data line
- 5-year moving average line
- X-axis: years (1980-2023)
- Y-axis: temperature in °C

3. Expert Level:
Visualization Name: "Monthly Temperature Anomalies"
Chart Type: Heatmap
Climate Change Focus: Monthly temperature deviations from baseline
Visual Elements:
- X-axis: months (Jan-Dec)
- Y-axis: years (1980-2023)
- Color scale: temperature anomalies in °C
- Baseline period: 1951-1980
"""

DETERMINE_NEEDED_DATA_PROMPT = """
You are a climate visualization expert. You are part of a process to generate a climate visualization.
Based on the following visualization specification:
{visualization_type}

Provide three outputs in this format:

1. needed_data:
- List specific variables needed
- Required time range
- Geographic scope
- Resolution (hourly/daily/monthly)

2. data_processing_steps:
- Step-by-step data transformation plan
- Required calculations
- Any aggregations or filtering
- Final expected data structure


# API Endpoint Information
{API_ENDPOINT_INFORMATION}

# API Query Examples
"""

RETRIEVE_DATA_PROMPT = """
You are an API expert and you are part of a process to generate a climate visualization.
Define the API endpoint and parameters needed to retrieve the data for the following visualization:
{visualization_type}

Here's the needed data information:
{needed_data}

Your response should include:
- 

# Output Example
          url="https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 52.52,
                "longitude": 13.41,
                "daily": ["temperature_2m_max", "temperature_2m_min"],
                "timezone": "auto"
            },
            data_key="daily",
            transform_func=lambda x: {
                'time': x['time'],
                'temp_max': x['temperature_2m_max'],
                'temp_min': x['temperature_2m_min']
            }
"""

PROCESS_DATA_PROMPT = """
Given:
- Visualization Goal: {visualization_description}
- Processing Plan: {data_processing_plan}
- Input Data Structure: {data_description}

Create a data processing function with:
def process_data(data: pd.DataFrame) -> pd.DataFrame:
    '''
    Process raw climate data for visualization.
    
    Returns:
        DataFrame with columns: [specify expected columns]
        Each row represents: [specify row structure]
    '''

Requirements:
1. Handle missing or invalid data
2. Validate input data structure
3. Include data quality checks
4. Optimize for performance with large datasets
5. Return clean, visualization-ready DataFrame
"""

GENERATE_VISUALIZATION_PROMPT = """
Create a Plotly visualization based on:
- Description: {visualization_description}
- Data Structure: {processed_data_description}
- Guidelines: {visualization_generation_guidelines}

Your ONLY output should be a Python function named visualization() with this signature:
Required Features:
    1. Clear axes labels and title
    2. Legend if multiple traces
    3. Optimized for performance

def visualize(data: ProcessedData) -> go.Figure:
    '''
    Generate climate visualization using Plotly.
    '''
"""

OLD_GENERATE_VISUALIZATION_PROMPT = """
# Data Visualization Requirements
You are a Python visualization expert. You only return executable Python code with no explanations.
The output should contain nothing but raw python code - no comments, descriptions or explanations or code block markers are needed.

## Output Requirements
Your only output should be a function with this exact signature:

```
def visualize(data: ProcessedData) -> go.Figure:
    \"\"\"
    Create a Plotly visualization using the provided ProcessedData instance.
    Args:
        data (ProcessedData): Instance containing main_data and nested_dataframes
    \"\"\"
```

## Data Structure
The input `data` parameter is an instance of ProcessedData class with two main components:
1. `data.main_data`: A pandas DataFrame containing metadata
2. `data.nested_dataframes`: A dictionary of pandas DataFrames containing hourly, daily or other time-series data
   - Access nested data using: `data.nested_dataframes['dataframe_name']`

```
# How the data variable is structured:
data.main_data = {data_description}

# How the nested dataframes are structured:
data.nested_dataframes = {nested_dataframes_description}

# Main DataFrame accessed like:
data.main_data['column_name']  # Series containing column data

# Nested DataFrames accessed like:
data.nested_dataframes['daily']  # DataFrame with columns: [column1, column2, ...]
data.nested_dataframes['hourly']      # DataFrame with columns: [column1, column2, ...]
```

## Technical Requirements
1. Use ONLY Plotly for visualization
2. The ONLY output should be the **visualization()** function provided above, other text is FORBIDDEN
3. Provide the raw code without without code block markers (```) or any surrounding text
4. Don't hallucinate data or make assumptions about the input data that isn't explicitly mentioned in the data descriptions.
5. Access data ONLY through:
   - `data.main_data[column_name]`
   - `data.nested_dataframes[dataframe_name][column_name]`
6. Ensure the function is self-contained and does not rely on external variables

## Example Output

import plotly.graph_objects as go
from datetime import datetime

def visualization(data: ProcessedData) -> go.Figure:
    fig = go.Figure()
    
    try:
        if 'daily' in data.nested_dataframes:
            daily = data.nested_dataframes['daily']
            
            if 'temperature_2m_max' in daily:
                # Main temperature trace
                fig.add_trace(
                    go.Scatter(
                        x=daily.index,
                        y=daily['temperature_2m_max'].fillna(method='ffill'),
                        name='Daily Maximum Temperature',
                        line=dict(color='red')
                    )
                )
                
                # Add 7-day moving average to show trend
                fig.add_trace(
                    go.Scatter(
                        x=daily.index,
                        y=daily['temperature_2m_max'].rolling(window=7).mean(),
                        name='7-day Average',
                        line=dict(color='orange', dash='dash'),
                    )
                )
                
                # Calculate and add monthly average
                monthly_avg = daily['temperature_2m_max'].resample('M').mean()
                fig.add_trace(
                    go.Scatter(
                        x=monthly_avg.index,
                        y=monthly_avg,
                        name='Monthly Average',
                        line=dict(color='blue', width=2),
                        visible='legendonly'  # Hidden by default
                    )
                )
                
    except Exception:
        print(f"Error:", exc_info=True)
    
    fig.update_layout(
        title_text="Temperature Trends in Nagoya",
        yaxis_title="Temperature (°C)",
        xaxis_title="Date",
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig
"""

########################
## Explanation Prompts
########################

GENERATE_EXPLANATION_PROMPT = """
You are tasked with providing clear, engaging descriptions of climate and environmental visualizations. 
Your description should help viewers understand the real-world implications of the data being presented.
Please provide a concise and informative description that may include.

-What is the main message or story this visualization tells?
-What environmental or climate aspect does it address?
-What time period or geographic scope is covered?

TECHNICAL ELEMENTS
-What are the key variables being shown?
-What units of measurement are used?


KEY FINDINGS
-What are the most significant patterns or trends?
-Are there any unexpected or surprising elements?


REAL-WORLD CONTEXT
-What are the practical implications of these findings?
-How might this information influence decision-making or policy?

Example Structure:

"This [visualization type] shows [main topic] from [timeframe], highlighting [key finding]. 
The data, sourced from [source], reveals [significant pattern/trend]. 

Notable features include [specific points of interest]. These findings are particularly relevant because [real-world connection]. 
Understanding this visualization helps us understand that [practical application], suggesting that [implication/action item]."


Ensure the response is very short, it should be between 50 to 100 words.
"""

 
###########################
## Complexity Level Prompts
###########################

LVL0_EXP_PROMPT = """
You are interacting with a user who is new to climate science, environmental studies, and data visualization. Your responses should:
- Use simple, non-technical language
- Provide clear, basic explanations
- If relevant break down complex concepts into easy-to-understand analogies
- Use visual metaphors and straightforward illustrations
- Avoid scientific jargon. If it is needed, provide explanation of the terms (difficult term ex: "CO2", "PM2.5", "NOx"...etc)
- Explain the significance of the visualization in accessible terms
- Focus on building foundational understanding
- Encourage curiosity and learning
- Use gentle, supportive tone that makes the user feel comfortable asking questions
"""

LVL1_EXP_PROMPT = """
You are communicating with a user who has a moderate understanding of climate science, environmental concepts, and data visualization techniques. Your responses should:
- Use appropriate technical terminology with clear explanations
- Provide nuanced insights into data and environmental trends
- Offer moderate-depth analysis of visualizations
- Discuss broader implications of climate and environmental data
- Include some statistical context
- If relevant draw connections between different environmental indicators
- Encourage critical thinking and deeper exploration
- Use a professional yet engaging tone"""

LVL2_EXP_PROMPT = """
You are engaging with a highly knowledgeable user specialized in climate science, environmental research, and advanced data visualization. Your responses should:
- If needed and relevant, provide precise, domain-specific scientific language
- Provide in-depth, technical analysis of data and visualizations
- Discuss complex interdependencies in environmental systems
- Offer sophisticated statistical interpretations
- Explore advanced modeling and predictive techniques
- Provide granular, nuanced insights into environmental trends
- Use a scholarly, rigorous tone that assumes high prior knowledge
- Expect and welcome advanced technical discussions
"""


LVL0_VIZ_PROMPT = """
You are generating visualizations for users new to data visualization and climate science. Your visualization outputs should:

- Use simple chart types (bar charts, line graphs, pie charts)
- Limit data points and variables shown simultaneously
- Include clear, prominent titles and labels
- Use intuitive color schemes (e.g., blue=cold, red=hot)
- Add explanatory annotations directly on the visualization
- Incorporate familiar size comparisons (e.g., "equivalent to X football fields")
- Include basic legend explanations
- Use rounded numbers and simplified scales
- Add contextual imagery where helpful (icons, simple illustrations)
- Ensure all text is easily readable at standard viewing sizes
"""

LVL1_VIZ_PROMPT = """
You are generating visualizations for users with moderate visualization literacy. Your outputs should:

- Utilize intermediate chart types (scatter plots, box plots, stacked charts)
- Layer 2-3 related variables in a single visualization
- Include statistical annotations where relevant (trend lines, confidence intervals)
- Use color schemes optimized for data type (sequential, diverging, categorical)
- Add detailed axis labels with units
- Incorporate small multiples for comparison
- Include interactive elements if supported (tooltips, hoverable details)
- Maintain professional design standards
- Add concise technical notes
- Enable basic comparative analysis
"""

LVL2_VIZ_PROMPT = """
You are generating visualizations for users with expertise in data visualization. Your outputs should:

- Employ advanced visualization types (heat maps, network diagrams, geographic projections)
- Layer multiple variables and relationships
- Include sophisticated statistical elements (uncertainty bands, probability distributions)
- Use carefully optimized color schemes for maximum information density
- Add detailed technical annotations if relevant
- Enable deep analytical capabilities
- Follow publication-quality standards
- Support expert-level comparative analysis
"""

################
## Misc Prompts
################

BUILD_EXTERNAL_QUERY_PROMPT = """
Provide the full URL with accurate parameters based on the user prompt for this API endpoint : ```{api_endpoint}```.
If the user hasn't specified it, base the location in Nagoya, Japan.
If not specified the timescale should be the past 2 years.
Be careful about the potential amount of data that could be returned (hourly data of 10 years or more isn't acceptable), and ensure the parameters are appropriate for the user's needs.
Here are some examples with the url and parameters:

Air Quality in Nagoya
```https://air-quality-api.open-meteo.com/v1/air-quality?latitude=35.1815&longitude=136.9064&hourly=pm10,pm2_5```

Temperatures in Fuji for the past 10 years
```https://archive-api.open-meteo.com/v1/archive?latitude=35.1667&longitude=138.6833&start_date=2014-11-17&end_date=2024-12-01&hourly=temperature_2m```

Here is the parameters documentation for the endpoint: 
{api_endpoint_parameters}
"""

OUTPUT_LANGUAGE_PROMPT = """
For your answer, whether it's code, text or a visualization provide all the text that will be shown to the user in English.
This includes any labels, titles, descriptions, or explanations that will be directly visible to the user.
The code you generate should follow common conventions and be written using English.
"""