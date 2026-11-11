"""Validate the deploy file against Render's current public schema and Free policy."""
import json
import urllib.request
from pathlib import Path

import jsonschema
import yaml


def main():
    root = Path(__file__).resolve().parent.parent
    blueprint = yaml.safe_load((root / "render.yaml").read_text(encoding="utf-8"))
    with urllib.request.urlopen("https://render.com/schema/render.yaml.json", timeout=30) as response:
        schema = json.load(response)
    jsonschema.validate(blueprint, schema)
    resources = blueprint.get("services", []) + blueprint.get("databases", [])
    if any(resource.get("plan") != "free" for resource in resources):
        raise ValueError("Only Free plans are authorized for this deployment.")
    if len({resource["region"] for resource in resources}) != 1:
        raise ValueError("The app and database must share a region.")
    print("PASS: current Render schema; all resources use Free in the same region.")


if __name__ == "__main__":
    main()
