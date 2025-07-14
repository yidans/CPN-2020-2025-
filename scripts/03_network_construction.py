import pandas as pd
import networkx as nx
from collections import Counter

def build_coauthor_network(df: pd.DataFrame) -> nx.Graph:
    patent_inventors = df.groupby('patent_number')['inventor_id'].apply(list).reset_index()

    G = nx.Graph()
    coauthor_pairs = []
    patent_collaborations = {}

    print("Processing collaborations...")
    for _, row in patent_inventors.iterrows():
        inventors = row['inventor_id']
        patent_num = row['patent_number']

        if len(inventors) > 1:
            for i in range(len(inventors)):
                for j in range(i + 1, len(inventors)):
                    pair = tuple(sorted([inventors[i], inventors[j]]))
                    coauthor_pairs.append(pair)
                    if pair not in patent_collaborations:
                        patent_collaborations[pair] = []
                    patent_collaborations[pair].append(patent_num)

    collaboration_counts = Counter(coauthor_pairs)

    print("Building network graph...")
    for (inv1, inv2), weight in collaboration_counts.items():
        G.add_edge(inv1, inv2,
                   weight=weight,
                   shared_patents=len(patent_collaborations[(inv1, inv2)]))

    print(f"Network created with {G.number_of_nodes():,} nodes and {G.number_of_edges():,} edges")
    return G

def attach_inventor_attributes(G: nx.Graph, df: pd.DataFrame) -> None:
    inventor_stats = df.groupby('inventor_id').agg({
        'inventor_full_name': 'first',
        'patent_number': 'nunique',
        'unified_assignee': lambda x: list(set(x.dropna())),
        'patent_year': ['min', 'max']
    }).reset_index()

    inventor_stats.columns = ['inventor_id', 'full_name', 'patent_count',
                              'organizations', 'first_year', 'last_year']
    inventor_stats['career_span'] = (
        inventor_stats['last_year'] - inventor_stats['first_year'] + 1
    )

    for _, row in inventor_stats.iterrows():
        if row['inventor_id'] in G.nodes:
            G.nodes[row['inventor_id']].update({
                'full_name': row['full_name'],
                'patent_count': row['patent_count'],
                'organizations': row['organizations'],
                'first_year': row['first_year'],
                'last_year': row['last_year'],
                'career_span': row['career_span']
            })

def main():
   
    df_path = "PATH"
    df = pd.read_csv(df_path)

    G = build_coauthor_network(df)
    attach_inventor_attributes(G, df)
    # nx.write_gpickle(G, "outputs/coauthor_network.gpickle")

if __name__ == "__main__":
    main()
