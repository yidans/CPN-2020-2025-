import pandas as pd
from collections import Counter
import warnings

warnings.filterwarnings("ignore")

CANONICAL_FIRMS = {
    'Baidu', 'Alibaba', 'Tencent', 'ByteDance', 'Google', 'Meta', 'Apple',
    'Amazon', 'Microsoft', 'OpenAI', 'Anthropic', 'Hugging Face', 'Cohere',
    'Nvidia', 'Tesla', 'Uber', 'Waymo', 'IBM', 'Intel', 'Qualcomm',
    'Adobe', 'Oracle'
}

def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    return df

def most_common_firm(series: pd.Series) -> str | None:
    counts = Counter(x for x in series if x in CANONICAL_FIRMS)
    if len(counts) == 1:
        return counts.most_common(1)[0][0]
    if counts:
        firm, freq = counts.most_common(1)[0]
        if freq > 0.7 * sum(counts.values()):
            return firm
    return None

def normalize_unified_assignees(df: pd.DataFrame) -> pd.DataFrame:
    needs_fix = ~df["unified_assignee"].isin(CANONICAL_FIRMS)

    for idx in df.index[needs_fix]:
        window = df.loc[max(0, idx - 10): idx + 10, "unified_assignee"]
        inferred = most_common_firm(window)
        if inferred:
            df.at[idx, "unified_assignee"] = inferred

    # Manual corrections
    manual_map = {
        "ALIBABA INNOVATION PRIVATE LIMITED": "Alibaba"
    }
    df["unified_assignee"] = df["unified_assignee"].replace(manual_map)
    return df

def main():
    filepath = "PATH"
    df = load_data(filepath)
    print(f"Original shape: {df.shape}")
    df = normalize_unified_assignees(df)

    unmapped = df.loc[
        ~df["unified_assignee"].isin(CANONICAL_FIRMS), "unified_assignee"
    ].unique()
    print("Remaining unmapped assignees (up to 15):", unmapped[:15])


if __name__ == "__main__":
    main()
