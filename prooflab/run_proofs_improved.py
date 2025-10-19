#!/usr/bin/env python3
"""
Improved proof runner using the full fbprooflab package capabilities.
This version uses the Config class and ReportGenerator for better functionality.
"""

from __future__ import annotations
import sys
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List

from fbprooflab import Config, load_claims_from_yaml, run_claim, ReportGenerator, ClaimResult


def run_claims_parallel(claims, max_workers: int) -> List[ClaimResult]:
    """Run claims in parallel using ProcessPoolExecutor."""
    results = []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all claims
        future_to_claim = {executor.submit(run_claim, claim): claim for claim in claims}
        
        # Collect results as they complete
        for future in as_completed(future_to_claim):
            claim = future_to_claim[future]
            try:
                result = future.get()
                results.append(result)
                logging.info(f"Completed claim {claim.id}: {result.status}")
            except Exception as e:
                logging.error(f"Error processing claim {claim.id}: {e}")
                # Create a failed result
                results.append(ClaimResult(
                    id=claim.id,
                    type=claim.type,
                    status="inconclusive",
                    details={"error": str(e)}
                ))
    
    # Sort results by claim ID to maintain consistent ordering
    results.sort(key=lambda r: r.id)
    return results


def run_claims_sequential(claims) -> List[ClaimResult]:
    """Run claims sequentially."""
    results = []
    
    for claim in claims:
        try:
            result = run_claim(claim)
            results.append(result)
            logging.info(f"Completed claim {claim.id}: {result.status}")
        except Exception as e:
            logging.error(f"Error processing claim {claim.id}: {e}")
            results.append(ClaimResult(
                id=claim.id,
                type=claim.type,
                status="inconclusive",
                details={"error": str(e)}
            ))
    
    return results


def main():
    """Main entry point."""
    try:
        # Parse configuration
        config = Config.from_args()
        
        # Setup logging
        config.setup_logging()
        
        # Validate configuration
        config.validate()
        
        logging.info(f"Starting proof runner with {config.claims_file}")
        
        # Load claims
        claims = load_claims_from_yaml(config.claims_file)
        logging.info(f"Loaded {len(claims)} claims")
        
        if not claims:
            logging.warning("No claims found in file")
            return 0
        
        # Run proofs
        if config.parallel:
            logging.info(f"Running proofs in parallel with {config.max_workers or 'default'} workers")
            results = run_claims_parallel(claims, config.max_workers)
        else:
            logging.info("Running proofs sequentially")
            results = run_claims_sequential(claims)
        
        # Generate reports
        logging.info("Generating reports...")
        generator = ReportGenerator(results)
        
        # Write JSON report
        generator.write_json_report(config.out_json)
        
        # Write Markdown report
        generator.write_markdown_report(config.out_md)
        
        # Print summary
        generator.print_summary()
        
        logging.info(f"Reports written to {config.out_json} and {config.out_md}")
        
        # Return appropriate exit code
        failed_count = sum(1 for r in results if r.status != "proved")
        if failed_count > 0:
            logging.warning(f"{failed_count} claims were not proved")
            return 1
        else:
            logging.info("All claims proved successfully!")
            return 0
            
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        return 130
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
