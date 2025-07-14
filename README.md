# Co-inventor Patent Network (CPN) Dataset 2020-2025

This repository contains the complete dataset and code for constructing co-inventor networks from patents filed by major technology organizations between 2020 and 2025. 
The dataset includes patent records and derived co-inventor networks for **19 major technology organizations**, covering patents filed and granted between **2020-01-01** and **2025-04-30**.

### Key Statistics
- **49,681** patents
- **53,603** unique inventors  
- **220,836** inventor-patent pairs
- **245,548** collaboration edges
- **19** major technology organizations

### Organizations Included
**Big Tech**: Google/Alphabet, Meta/Facebook, Apple, Amazon, Microsoft  
**AI Labs**: OpenAI, Anthropic, Hugging Face, Cohere  
**Hardware**: Nvidia, Intel, Qualcomm, AMD  
**Autonomous Vehicles**: Tesla, Uber, Waymo  
**Enterprise**: IBM, Oracle, Adobe  
**Chinese Tech**: Baidu, Alibaba, Tencent, ByteDance

## Dataset Structure

The released dataset consists of 5 CSV files:

### 1. `patents.csv` (49,681 records)
Patent-level metadata including:
- `patent_number`: Unique patent identifier
- `patent_title`: Title of the patent
- `patent_date`: Patent grant date
- `app_date`: Application filing date
- `assignee_organization`: Standardized organization name
- `num_inventors`: Number of inventors on the patent
- `citedby_count`: Number of forward citations

### 2. `inventors.csv` (53,603 records)
Inventor-level profiles with career metrics:
- `inventor_id`: Unique disambiguated inventor identifier
- `first_name`, `last_name`, `full_name`: Inventor name variants
- `total_patents`: Total patents filed by inventor
- `career_start_date`, `career_end_date`: Career span boundaries
- `avg_team_size`: Average number of co-inventors per patent
- `org_transitions`: Number of organizational changes
- `primary_affiliation`: Most frequent organizational affiliation
- `affiliation_history`: Chronological sequence of affiliations

### 3. `inventor_patents.csv` (220,836 records)
Inventor-patent mapping with temporal affiliations:
- `inventor_id`: Inventor identifier
- `patent_number`: Patent identifier  
- `app_date`, `patent_date`: Filing and grant dates
- `affiliation_at_filing`: Organization at time of filing
- `app_year`, `patent_year`: Filing and grant years

### 4. `edges.csv` (245,548 records)
Co-inventor collaboration network:
- `inventor1_id`, `inventor2_id`: Collaborating inventor pair
- `edge_weight`: Number of shared patents
- `first_collaboration_date`, `last_collaboration_date`: Collaboration span
- `first_year`, `last_year`: Collaboration year boundaries
- `edge_2020`, `edge_2021`, ..., `edge_2025`: Annual collaboration indicators

### 5. `assignee_aliases.csv` 
Organization name standardization mapping:
- `observed_name`: Original assignee name variant
- `canonical_form`: Standardized organization name
- `relationship_type`: Type of name relationship (legal_entity, subsidiary, etc.)

## Environment Setup

### Requirements
```
python>=3.8
pandas>=1.3.0
numpy>=1.21.0
networkx>=2.6
requests>=2.25.0
```

### Installation
```bash
# Clone the repository
git clone https://github.com/yidans/CPN-2020-2025-.git
cd CPN-2020-2025-

# Install dependencies
pip install -r requirements.txt

# Or using conda
conda env create -f environment.yml
conda activate coinventor-network
```

## Quick Start

### Loading the Dataset
```python
import pandas as pd
import networkx as nx

# Load the dataset
patents = pd.read_csv('data/patents.csv')
inventors = pd.read_csv('data/inventors.csv')
inventor_patents = pd.read_csv('data/inventor_patents.csv')
edges = pd.read_csv('data/edges.csv')
aliases = pd.read_csv('data/assignee_aliases.csv')

print(f"Dataset loaded: {len(patents)} patents, {len(inventors)} inventors")
```

### Constructing the Network
```python
# Create NetworkX graph from edges
G = nx.from_pandas_edgelist(
    edges, 
    source='inventor1_id', 
    target='inventor2_id',
    edge_attr=True
)

print(f"Network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
print(f"Network density: {nx.density(G):.6f}")
```

### Basic Analysis Examples
```python
# Top inventors by patent count
top_inventors = inventors.nlargest(10, 'total_patents')[['full_name', 'total_patents', 'primary_affiliation']]
print("Top 10 most prolific inventors:")
print(top_inventors)

# Organization patent counts
org_patents = patents['assignee_organization'].value_counts()
print("\nPatents by organization:")
print(org_patents.head(10))

# Collaboration patterns by year
yearly_collabs = edges[['edge_2020', 'edge_2021', 'edge_2022', 'edge_2023', 'edge_2024', 'edge_2025']].sum()
print("\nCollaborations by year:")
print(yearly_collabs)
```

## Reproducibility Scripts

### Scripts
- `scripts/01_data_collection.py`: PatentsView API data retrieval
- `scripts/02_data_cleaning.py`: Standardization and filtering pipeline  
- `scripts/03_network_construction.py`: Co-inventor network building
- `scripts/04_dataset_generation.py`: Final CSV export and validation

### Usage
```bash
# Full pipeline (requires PatentsView API key)
python scripts/01_data_collection.py --api_key YOUR_API_KEY
python scripts/02_data_cleaning.py
python scripts/03_network_construction.py  
python scripts/04_dataset_generation.py

# Or run the complete pipeline
bash scripts/run_full_pipeline.sh
```

## Acknowledgments

- **PatentsView**: USPTO's patent data platform and API
- **U.S. Patent and Trademark Office**: Source of all patent records


**Last Updated**: June 2025  
**Version**: 1.0  
**DOI**: [To be assigned upon publication]
