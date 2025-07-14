import os
import time
import argparse
import logging
import requests
import pandas as pd
from datetime import datetime
from collections import Counter 

class PatentsViewAPI:
    """
    Retrieves and processes patents from the PatentsView API for a list of tech companies,
    checkpointing results to disk per company to avoid data loss on errors.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://search.patentsview.org/api/v1/patent/"
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Exact legal name variants for phrase-matching
        self.company_mappings = {
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

        
        self.assignee_to_canonical = {}
        for company, variants in self.company_mappings.items():
            for v in variants:
                self.assignee_to_canonical[v] = company


    def search_patents_by_company(self, company_name: str,
                                start_date: str, end_date: str):
        all_raw   = []
        variants  = self.company_mappings.get(company_name, [])
        page_size = 1000

        for term in variants:
            after_cursor = None
            logging.info(f"Querying variant '{term}' for {company_name}")
            earliest_global = "9999-12-31"

            while True:
                options = {"size": page_size}
                if after_cursor:
                    options["after"] = after_cursor          

                payload = {
                    "q": {
                        "_and": [
                            {"_text_phrase": {"assignees.assignee_organization": term}},
                            {"_gte": {"application.filing_date": start_date}},
                            {"_lte": {"application.filing_date": end_date}},
                            {"_gte": {"patent_date": start_date}},
                            {"_lte": {"patent_date": end_date}}
                        ]
                    },
                    "f": [
                        "patent_id", "patent_title", "patent_date",
                        "application.filing_date",
                        "assignees.assignee_organization",
                        "inventors.inventor_id",
                        "inventors.inventor_name_first",
                        "inventors.inventor_name_last",
                        "patent_num_times_cited_by_us_patents"
                    ],
                    
                    "s": [{"patent_id": "asc"}],
                    "o": options
                }

                resp = requests.post(self.base_url, headers=self.headers,
                                    json=payload, timeout=60)
                resp.raise_for_status()
                batch = resp.json().get("patents", [])
                if not batch:
                    break

                all_raw.extend(batch)

           
                page_dates = [
                    app["filing_date"]
                    for pat in batch
                    for app in (pat.get("application") or [{}])
                    if app.get("filing_date")
                ]
                batch_min = min(page_dates) if page_dates else "—"
                batch_max = max(page_dates) if page_dates else "—"
                if page_dates:
                    earliest_global = min(batch_min, earliest_global)
                logging.info(
                    f"[{datetime.now():%H:%M:%S}] "
                    f"Retrieved {len(batch):4d} | total so far: {len(all_raw):,} | "
                    f"batch dates {batch_min} → {batch_max} | "
                    f"oldest filing so far: {earliest_global}"
                )
                # ─────────────────────

                if len(batch) < page_size:
                    break                                 

                after_cursor = batch[-1]["patent_id"]

                time.sleep(1)                           
            time.sleep(2)                                

        patents = {p["patent_id"]: p for p in all_raw}.values()
        logging.info(f"{company_name}: {len(patents)} unique patents")
        return list(patents)



    def process_patent_data(self, patents):

        rows = []
        for p in patents:
            raw_org = (p.get("assignees") or [{}])[0].get("assignee_organization", "")
            canon = self.assignee_to_canonical.get(raw_org, raw_org)
            base = {
                "patent_number": p.get("patent_id"),
                "patent_title": p.get("patent_title"),
                "patent_date": p.get("patent_date"),
                "app_date": (p.get("application") or [{}])[0].get("filing_date"),
                "unified_assignee": canon,
                "original_assignee_organization": raw_org,
                "citedby_count": p.get("patent_num_times_cited_by_us_patents", 0)
            }
            for inv in p.get("inventors", []):
                row = base.copy()
                row.update({
                    "inventor_id": inv.get("inventor_id"),
                    "first_name": inv.get("inventor_name_first"),
                    "last_name": inv.get("inventor_name_last")
                })
                rows.append(row)

        return pd.DataFrame(rows)

    def run_complete_analysis(self, start_date: str, end_date: str, output_file: str):

        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

        processed = set()
        if os.path.exists(output_file):
            try:
                df_exist = pd.read_csv(output_file, usecols=["unified_assignee"])
                processed = set(df_exist["unified_assignee"].unique())
                logging.info(f"Resuming; already processed: {processed}")
            except Exception:
                processed = set()

        for company in self.company_mappings:
            if company in processed:
                logging.info(f"Skipping {company} (already done)")
                continue

            try:
                patents = self.search_patents_by_company(company, start_date, end_date)
                df = self.process_patent_data(patents)
                if df.empty:
                    logging.warning(f"No data for {company}; writing empty placeholder")
                
                df.to_csv(
                    output_file,
                    mode="a",
                    header=not os.path.exists(output_file),
                    index=False
                )
                logging.info(f" Saved {len(df)} rows for {company}")
            except Exception as e:
                logging.error(f" Error with {company}: {e}", exc_info=True)

        logging.info(f"All done. Combined results in '{output_file}'")

def parse_args():
    p = argparse.ArgumentParser(description="Retrieve tech-company patents from PatentsView API")
    p.add_argument("--api-key", required=True, help="Your PatentsView API key")
    p.add_argument("--start-date", default="2010-01-01", help="Earliest filing/grant date (YYYY-MM-DD)")
    p.add_argument("--end-date", default=datetime.now().strftime("%Y-%m-%d"),
                   help="Latest filing/grant date (YYYY-MM-DD)")
    p.add_argument("--output-file", default="tech_company_patents.csv",
                   help="CSV path to append results")
    return p.parse_args()

def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    api = PatentsViewAPI(args.api_key)
    api.run_complete_analysis(args.start_date, args.end_date, args.output_file)

if __name__ == "__main__":
    main()
