import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
import logging

def prepare_detailed_data(before_df, after_df, comparison_df):
    """Prepare detailed data for the report by merging and processing dataframes."""
    # Merge before and after data
    merged_before = before_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']]
    merged_after = after_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']]
    
    # Get unique solution directories
    solution_dirs = sorted(set(before_df['solution dir']).union(after_df['solution dir']))
    
    # Prepare data for each solution dir
    detailed_data = {}
    for dir in solution_dirs:
        before_details = merged_before[merged_before['solution dir'] == dir].to_dict(orient='records')
        after_details = merged_after[merged_after['solution dir'] == dir].to_dict(orient='records')
        detailed_data[dir] = {
            'before': before_details,
            'after': after_details
        }
    
    return solution_dirs, detailed_data

def create_energy_graphs(before_df, after_df):
    """Create energy consumption graphs for before and after refinement."""
    # Group by 'solution dir' and calculate sum
    before_file_type = before_df.groupby('solution dir')['Energy Consumed (Wh)'].sum().reset_index()
    after_file_type = after_df.groupby('solution dir')['Energy Consumed (Wh)'].sum().reset_index()
    
    # Sort data
    before_file_type_sorted = before_file_type.sort_values('Energy Consumed (Wh)', ascending=False)
    after_file_type_sorted = after_file_type.sort_values('Energy Consumed (Wh)', ascending=False)
    
    # Create color mapping
    unique_solution_dirs = sorted(set(before_file_type_sorted['solution dir']).union(after_file_type_sorted['solution dir']))
    color_palette = px.colors.qualitative.Plotly
    color_mapping = {dir: color_palette[i % len(color_palette)] for i, dir in enumerate(unique_solution_dirs)}
    
    # Create before graph
    bar_graph_before = create_bar_graph(
        before_file_type_sorted,
        'Energy Consumed (Wh)',
        'Solution Based(Wh) Before',
        color_mapping
    )
    
    # Create after graph
    bar_graph_after = create_bar_graph(
        after_file_type_sorted,
        'Energy Consumed (Wh)',
        'Solution Based (Wh) After',
        color_mapping
    )
    
    return (
        pio.to_html(bar_graph_before, include_plotlyjs=False, full_html=False),
        pio.to_html(bar_graph_after, include_plotlyjs=False, full_html=False)
    )

def create_emissions_graphs(before_df, after_df):
    """Create emissions graphs for before and after refinement."""
    # Group by 'solution dir' and sum emissions
    before_gco2eq = before_df.groupby('solution dir')['Emissions (gCO2eq)'].sum().reset_index()
    after_gco2eq = after_df.groupby('solution dir')['Emissions (gCO2eq)'].sum().reset_index()
    
    # Sort data
    before_gco2eq_sorted = before_gco2eq.sort_values('Emissions (gCO2eq)', ascending=False)
    after_gco2eq_sorted = after_gco2eq.sort_values('Emissions (gCO2eq)', ascending=False)
    
    # Create color mapping
    unique_solution_dirs = sorted(set(before_gco2eq_sorted['solution dir']).union(after_gco2eq_sorted['solution dir']))
    color_palette = px.colors.qualitative.Plotly
    color_mapping = {dir: color_palette[i % len(color_palette)] for i, dir in enumerate(unique_solution_dirs)}
    
    # Create graphs
    bar_graph_before = create_bar_graph(
        before_gco2eq_sorted,
        'Emissions (gCO2eq)',
        'Emissions by Solution Directory Before Refinement (gCO2eq)',
        color_mapping
    )
    
    bar_graph_after = create_bar_graph(
        after_gco2eq_sorted,
        'Emissions (gCO2eq)',
        'Emissions by Solution Directory After Refinement (gCO2eq)',
        color_mapping
    )
    
    return (
        pio.to_html(bar_graph_before, include_plotlyjs=False, full_html=False),
        pio.to_html(bar_graph_after, include_plotlyjs=False, full_html=False)
    )

def create_bar_graph(data_frame, value_column, title, color_mapping):
    """Create a horizontal bar graph with consistent styling."""
    fig = go.Figure()
    
    for _, row in data_frame.iterrows():
        fig.add_trace(go.Bar(
            x=[row[value_column]],
            y=[row['solution dir']],
            orientation='h',
            name=row['solution dir'],
            marker=dict(color=color_mapping.get(row['solution dir'], 'blue'))
        ))
    
    fig.update_layout(
        barmode='stack',
        title=title,
        xaxis_title=value_column,
        yaxis_title='Solution Directory',
        xaxis=dict(
            range=[0, data_frame[value_column].max() * 1.1],
            tickformat=".6f"
        ),
        margin=dict(l=150, r=50, t=50, b=50),
        showlegend=False
    )
    
    return fig

def create_embedded_code_graphs(before_df, after_df):
    """Create graphs comparing embedded and non-embedded code emissions."""
    # Define file types
    embedded_types = ['.html', '.css', '.xml', '.php', '.ts']
    non_embedded_types = ['.py', '.java', '.cpp', '.rb']
    
    # Filter data
    before_embedded = before_df[before_df['File Type'].isin(embedded_types)]
    before_non_embedded = before_df[before_df['File Type'].isin(non_embedded_types)]
    after_embedded = after_df[after_df['File Type'].isin(embedded_types)]
    after_non_embedded = after_df[after_df['File Type'].isin(non_embedded_types)]
    
    # Calculate totals
    total_embedded_before = before_embedded['Emissions (gCO2eq)'].astype(float).sum()
    total_embedded_after = after_embedded['Emissions (gCO2eq)'].astype(float).sum()
    total_non_embedded_before = before_non_embedded['Emissions (gCO2eq)'].astype(float).sum()
    total_non_embedded_after = after_non_embedded['Emissions (gCO2eq)'].astype(float).sum()
    
    # Create graphs
    embedded_graph = create_code_type_graph(
        total_embedded_before,
        total_embedded_after,
        'Embedded Code',
        'Emissions for Embedded Code (gCO2eq)'
    )
    
    non_embedded_graph = create_code_type_graph(
        total_non_embedded_before,
        total_non_embedded_after,
        'Non-Embedded Code',
        'Emissions for Non-Embedded Code (gCO2eq)'
    )
    
    return (
        pio.to_html(embedded_graph, include_plotlyjs=False, full_html=False),
        pio.to_html(non_embedded_graph, include_plotlyjs=False, full_html=False)
    )

def create_code_type_graph(before_value, after_value, code_type, title):
    """Create a comparison graph for code types."""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=[before_value],
        y=[code_type],
        orientation='h',
        name='Before',
        marker=dict(color='red')
    ))
    
    fig.add_trace(go.Bar(
        x=[after_value],
        y=[code_type],
        orientation='h',
        name='After',
        marker=dict(color='green')
    ))
    
    fig.update_layout(
        barmode='group',
        title=title,
        xaxis_title='Emissions (gCO2eq)',
        yaxis_title='Code Type',
        xaxis=dict(
            range=[0, max(before_value, after_value) * 1.1],
            tickformat=".6f"
        ),
        margin=dict(l=150, r=50, t=50, b=50),
        showlegend=True
    )
    
    return fig

def create_top_five_tables(df):
    """Create HTML tables for top five energy and emissions consumers."""
    # Top five energy consumers
    top_five_energy = df.sort_values('Energy Consumed (Wh)', ascending=False).head(5)[
        ['Application name', 'Timestamp', 'Energy Consumed (Wh)']
    ]
    top_five_energy.rename(columns={
        'Application name': 'File Name',
        'Timestamp': 'Timestamp',
        'Energy Consumed (Wh)': 'Energy Consumed (Wh)'
    }, inplace=True)
    
    # Top five emissions producers
    top_five_emissions = df.sort_values('Emissions (gCO2eq)', ascending=False).head(5)[
        ['Application name', 'Timestamp', 'Emissions (gCO2eq)']
    ]
    top_five_emissions.rename(columns={
        'Application name': 'File Name',
        'Timestamp': 'Timestamp',
        'Emissions (gCO2eq)': 'Emissions (gCO2eq)'
    }, inplace=True)
    
    return (
        top_five_energy.to_html(index=False, classes='table', border=0, float_format=lambda x: f"{x:.6f}"),
        top_five_emissions.to_html(index=False, classes='table', border=0, float_format=lambda x: f"{x:.6f}")
    )
