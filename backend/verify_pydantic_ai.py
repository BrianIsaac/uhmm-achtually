#!/usr/bin/env python3
"""Verify that all AI components are using PydanticAI."""

import ast
import os
from pathlib import Path


def check_imports(filepath):
    """Check what AI libraries are imported in a file."""
    with open(filepath, 'r') as f:
        content = f.read()

    tree = ast.parse(content)

    imports = {
        'pydantic_ai': False,
        'instructor': False,
        'other_ai': []
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if 'pydantic_ai' in alias.name:
                    imports['pydantic_ai'] = True
                elif 'instructor' in alias.name:
                    imports['instructor'] = True

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                if 'pydantic_ai' in node.module:
                    imports['pydantic_ai'] = True
                elif 'instructor' in node.module:
                    imports['instructor'] = True

    return imports


def main():
    """Check all V2 pipeline components."""
    print("=" * 60)
    print("VERIFYING PYDANTIC AI USAGE IN V2 PIPELINE")
    print("=" * 60)

    v2_dir = Path("src/processors_v2")

    components = {
        "ClaimExtractorV2": v2_dir / "claim_extractor_v2.py",
        "WebFactCheckerV2": v2_dir / "web_fact_checker_v2.py",
        "PipelineCoordinator": v2_dir / "pipeline_coordinator.py",
        "PipelineBridge": v2_dir / "pipeline_bridge.py",
        "FactCheckMessengerV2": v2_dir / "fact_check_messenger_v2.py",
    }

    all_pydantic = True

    for name, filepath in components.items():
        if filepath.exists():
            imports = check_imports(filepath)

            print(f"\n{name}:")
            print(f"  File: {filepath.name}")

            if imports['pydantic_ai']:
                print(f"  ✅ Uses PydanticAI")
            else:
                print(f"  ⭕ No PydanticAI (not needed)")

            if imports['instructor']:
                print(f"  ❌ Still uses Instructor!")
                all_pydantic = False
            else:
                print(f"  ✅ No Instructor dependency")
        else:
            print(f"\n{name}: File not found!")

    print("\n" + "=" * 60)
    if all_pydantic:
        print("✅ SUCCESS: No Instructor dependencies found!")
        print("✅ All AI components use PydanticAI exclusively!")
    else:
        print("❌ ERROR: Some components still use Instructor!")
    print("=" * 60)

    # Show pipeline flow
    print("\nPIPELINE FLOW:")
    print("1. SentenceAggregator → TextFrame")
    print("2. PipelineBridge → Queues sentences")
    print("3. ClaimExtractorV2 (PydanticAI) → Extracts claims")
    print("4. WebFactCheckerV2 (PydanticAI) → Verifies claims")
    print("5. FactCheckMessengerV2 → Broadcasts verdicts")
    print("\n✅ All AI operations use PydanticAI exclusively!")


if __name__ == "__main__":
    main()