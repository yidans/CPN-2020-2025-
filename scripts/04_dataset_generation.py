import os
import pandas as pd
import numpy as np
import networkx as nx
from collections import defaultdict, Counter


OUTPUT_DIR = "PATH"
START_DATE = '2020-01-01'
END_DATE = '2025-04-30'

def filter_dataset(df):
    return df[
        (df['app_date'] >= START_DATE) & 
        (df['app_date'] <= END_DATE)
    ].copy()

def create_patents_csv(df):
    patents = df.groupby('patent_number').agg({
        'patent_title': 'first',
        'patent_date': 'first',
        'app_date': 'first',
        'unified_assignee': 'first',
        'citedby_count': 'first',
        'inventor_id': 'count',
        'patent_year': 'first',
        'app_year': 'first'
    }).reset_index()
    patents = patents.rename(columns={
        'inventor_id': 'num_inventors',
        'unified_assignee': 'assignee_organization'
    })
    return patents

def create_inventors_csv(df):
    basic_info = df.groupby('inventor_id').agg({
        'first_name': 'first',
        'last_name': 'first',
        'inventor_full_name': 'first'
    }).reset_index()

    career_metrics = df.groupby('inventor_id').agg({
        'app_date': ['min', 'max', 'count'],
        'patent_number': 'nunique',
        'unified_assignee': ['first', lambda x: len(x.unique()), list]
    }).reset_index()
    career_metrics.columns = [
        'inventor_id', 'career_start_date', 'career_end_date', 'total_records',
        'total_patents', 'primary_affiliation', 'unique_organizations', 'all_affiliations'
    ]
    career_metrics['career_span_days'] = (
        pd.to_datetime(career_metrics['career_end_date']) - 
        pd.to_datetime(career_metrics['career_start_date'])
    ).dt.days

    # Average team size
    team_sizes = df.groupby('patent_number')['inventor_id'].count().rename('team_size')
    avg_team_size = df.merge(team_sizes, on='patent_number')\
                      .groupby('inventor_id')['team_size']\
                      .mean().round(2).reset_index().rename(columns={'team_size': 'avg_team_size'})

    # Transitions
    def count_transitions(affils):
        transitions = sum(a != b for a, b in zip(affils, affils[1:]))
        return transitions

    transitions = df.sort_values(['inventor_id', 'app_date'])\
        .groupby('inventor_id')['unified_assignee']\
        .apply(lambda x: count_transitions(x.tolist()))\
        .reset_index(name='org_transitions')

    histories = df.sort_values(['inventor_id', 'app_date'])\
        .groupby('inventor_id')['unified_assignee']\
        .apply(lambda x: ' -> '.join(dict.fromkeys(x.tolist())))\
        .reset_index(name='affiliation_history')

    inventors = basic_info\
        .merge(career_metrics, on='inventor_id')\
        .merge(avg_team_size, on='inventor_id')\
        .merge(transitions, on='inventor_id')\
        .merge(histories, on='inventor_id')\
        .drop(columns=['all_affiliations'])

    return inventors

def create_inventor_patents_csv(df):
    return df[[
        'inventor_id', 'patent_number', 'app_date', 'patent_date',
        'unified_assignee', 'app_year', 'patent_year'
    ]].rename(columns={'unified_assignee': 'affiliation_at_filing'})

def create_collaboration_network_from_G(G):
    edge_list = []
    for u, v, attr in G.edges(data=True):
        record = {
            'inventor1_id': u,
            'inventor2_id': v,
            'edge_weight': attr.get('weight', 1),
            'shared_patents': attr.get('shared_patents', None)
        }
        for year in range(2020, 2026):
            record[f'edge_{year}'] = attr.get(f'edge_{year}', 0)
        edge_list.append(record)
    return pd.DataFrame(edge_list)

def create_assignee_aliases_csv():
    company_mappings = {
        "Baidu": [
            "Baidu, Inc.",
            "BEIJING BAIDU NETCOM SCIENCE TECHNOLOGY CO., LTD.", 
            "BAIDU ONLINE NETWORK TECHNOLOGY (BEIJING) CO., LTD."
        ],
        "Alibaba": [
            "Alibaba Group Holding Limited",
            "ALIBABA (CHINA) CO., LTD.",
            "Alibaba Damo (Hangzhou) Technology Co., Ltd.",
            "Alibaba Cloud Computing Co., Ltd.",
            "Alibaba Singapore Holding Private Limited",
            "ALIBABA TECHNOLOGY (ISRAEL) LTD.",
            "Alibaba Innovation Private Limited"
        ],
        "Tencent": [
            "Tencent Holdings Ltd.",
            "TENCENT AMERICA LLC",
            "TENCENT TECHNOLOGIES (SHENZHEN) COMPANY LIMITED",
            "TENCENT CLOUD COMPUTING (BEIJING) CO., LTD.",
            "Tencent Music Entertainment Technology (Shenzhen) Co., Ltd."
        ],
        "ByteDance": [
            "ByteDance Ltd.",
            "BEIJING BYTEDANCE NETWORK TECHNOLOGY CO., LTD.",
            "TIANJIN BYTEDANCE TECHNOLOGY CO., LTD.",
            "Beijing Zitiao Network Technology Co., Ltd.",
            "BYTEDANCE INC."
        ],
        "Google": [
            "Google LLC",
            "Google Inc.",
            "GOOGLE TECHNOLOGY HOLDINGS LLC",
            "Alphabet Communications, Inc.",
            "Alphabet Inc."
        ],
        "Meta": [
            "Meta Platforms, Inc.",
            "Facebook, Inc.",
            "Meta Platforms Technologies, LLC",
            "Facebook Technologies, LLC"
        ],
        "Apple": ["Apple Inc."],
        "Amazon": [
            "Amazon.com, Inc.",
            "Amazon Technologies, Inc.",
            "Amazon Technology, Inc."
        ],
        "Microsoft": [
            "Microsoft Corporation",
            "MICROSOFT TECHNOLOGY LICENSING, LLC",
            "Microsoft Licensing Technology, LLC"
        ],
        "OpenAI": ["OpenAI, Inc.", "OpenAi OPCo, LLC."],
        "Anthropic": ["Anthropic PBC"],
        "Hugging Face": ["Hugging Face, Inc."],
        "Cohere": ["Cohere Technologies, Inc."],
        "Nvidia": [
            "NVIDIA CORPORATION",
            "NVIDIA Technologies, Inc.",
            "Nvidia Denmark ApS", 
            "Nvidia Technology UK Limited"
        ],
        "Tesla": [
            "Tesla, Inc.",
            "Tesla Motors, Inc.",
            "Tesla Motors Canada ULC",
            "TESLA GROHMANN AUTOMATION GMBH"
        ],
        "Uber": [
            "Uber Technologies, Inc.",
            "Uber Technology, Inc.", 
            "UBER HOLDINGS LIMITED"
        ],
        "Waymo": ["Waymo LLC"],
        "IBM": [
            "IBM Corporation",
            "IBM INTERNATIONAL GROUP BV"
        ],
        "Intel": [
            "Intel Corporation",
            "Intel NDTM US LLC",
            "Intel IP Corporation",
            "Intel Germany GmbH & Co. KG"
        ],
        "Qualcomm": [
            "QUALCOMM Incorporated",
            "QUALCOMM Technologies, Inc."
        ],
        "Adobe": ["Adobe Inc."],
        "Oracle": [
            "Oracle Corporation",
            "Oracle International Corporation",
            "ORACLE SYSTEMS CORPORATION",
            "Oracle Financial Services Software Limited"
        ]
    }
    

    
    records = []
    for canonical, variants in company_mappings.items():
        for v in variants:
            records.append({
                'observed_name': v,
                'canonical_form': canonical,
                'relationship_type': 'legal_entity'
            })
    return pd.DataFrame(records)

def main(df_clean, G):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_filtered = filter_dataset(df_clean)

    patents_df = create_patents_csv(df_filtered)
    patents_df.to_csv(f"{OUTPUT_DIR}/patents.csv", index=False)

    inventors_df = create_inventors_csv(df_filtered)
    inventors_df.to_csv(f"{OUTPUT_DIR}/inventors.csv", index=False)

    inventor_patents_df = create_inventor_patents_csv(df_filtered)
    inventor_patents_df.to_csv(f"{OUTPUT_DIR}/inventor_patents.csv", index=False)

    edges_df = create_collaboration_network_from_G(G)
    edges_df.to_csv(f"{OUTPUT_DIR}/edges.csv", index=False)

    aliases_df = create_assignee_aliases_csv()
    aliases_df.to_csv(f"{OUTPUT_DIR}/assignee_aliases.csv", index=False)

