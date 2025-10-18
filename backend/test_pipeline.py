#!/usr/bin/env python3
"""Test script for pipeline components."""

import asyncio
from dotenv import load_dotenv
from loguru import logger

from src.utils.config import get_settings
from src.processors.claim_extractor import ClaimExtractor
from src.processors.web_fact_checker import WebFactChecker
from src.models.claim_models import Claim

# Load environment variables
load_dotenv()


async def test_claim_extraction():
    """Test the ClaimExtractor component."""
    print("\n" + "="*60)
    print("Testing ClaimExtractor with PydanticAI")
    print("="*60)

    settings = get_settings()
    extractor = ClaimExtractor(settings.GROQ_API_KEY)

    test_sentences = [
        "Python 3.12 removed the distutils package.",
        "The Earth is flat and the moon is made of cheese.",
        "What is the weather like today?",
        "I think this is a great idea!",
        "The GDP of the US in 2023 was $27.36 trillion.",
    ]

    for sentence in test_sentences:
        print(f"\nSentence: {sentence}")
        claims = await extractor.extract(sentence)

        if claims:
            print(f"  Found {len(claims)} claim(s):")
            for claim in claims:
                print(f"    - {claim.text} (type: {claim.claim_type})")
        else:
            print("  No factual claims found")


async def test_fact_checking():
    """Test the WebFactChecker component."""
    print("\n" + "="*60)
    print("Testing WebFactChecker with PydanticAI")
    print("="*60)

    settings = get_settings()

    if not settings.EXA_API_KEY:
        print("EXA_API_KEY not found - skipping fact-checking test")
        return

    fact_checker = WebFactChecker(
        groq_api_key=settings.GROQ_API_KEY,
        exa_api_key=settings.EXA_API_KEY,
        allowed_domains=settings.allowed_domains_list
    )

    test_claims = [
        Claim(text="Python 3.12 removed distutils", claim_type="version"),
        Claim(text="The Earth is flat", claim_type="definition"),
    ]

    for claim in test_claims:
        print(f"\nClaim: {claim.text}")
        verdict = await fact_checker.verify(claim)

        print(f"  Status: {verdict.status}")
        print(f"  Confidence: {verdict.confidence:.2f}")
        print(f"  Rationale: {verdict.rationale}")
        if verdict.evidence_url:
            print(f"  Evidence: {verdict.evidence_url}")


async def test_full_pipeline():
    """Test the full pipeline from sentence to verdict."""
    print("\n" + "="*60)
    print("Testing Full PydanticAI Pipeline: Sentence -> Claims -> Verdicts")
    print("="*60)

    settings = get_settings()

    if not settings.exa_api_key:
        print("EXA_API_KEY not found - skipping full pipeline test")
        return

    # Initialize components
    extractor = ClaimExtractorV2(settings.groq_api_key)
    fact_checker = WebFactCheckerV2(
        groq_api_key=settings.groq_api_key,
        exa_api_key=settings.exa_api_key,
        allowed_domains=settings.allowed_domains_list
    )

    test_sentence = "Python 3.12 removed distutils and the Earth is flat."
    print(f"\nProcessing: {test_sentence}")

    # Extract claims
    print("\n1. Extracting claims...")
    claims = await extractor.extract(test_sentence)
    print(f"   Found {len(claims)} claim(s)")

    # Fact-check each claim
    if claims:
        print("\n2. Fact-checking claims...")
        for i, claim in enumerate(claims, 1):
            print(f"\n   Claim {i}: {claim.text}")
            verdict = await fact_checker.verify(claim)
            print(f"   -> {verdict.status} (confidence: {verdict.confidence:.2f})")
            print(f"      {verdict.rationale}")


async def main():
    """Run all tests."""
    try:
        # Test individual components
        await test_claim_extraction()
        await test_fact_checking()

        # Test full pipeline
        await test_full_pipeline()

        print("\n" + "="*60)
        print("All tests completed successfully!")
        print("="*60)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())