"""Run manually or from a scheduler: python download_data.py."""
import json
from src.data_sources import download_inputs

if __name__ == "__main__":
    print(json.dumps(download_inputs(), indent=2))
