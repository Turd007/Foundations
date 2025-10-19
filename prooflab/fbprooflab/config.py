"""Configuration management for proof runner."""

from __future__ import annotations
import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Configuration class for proof runner."""
    
    claims_file: str
    out_json: str
    out_md: str
    verbose: bool = False
    parallel: bool = False
    max_workers: Optional[int] = None
    log_level: str = "INFO"
    
    @classmethod
    def from_args(cls, args: Optional[list[str]] = None) -> Config:
        """Create configuration from command line arguments."""
        parser = cls._create_parser()
        parsed_args = parser.parse_args(args)
        
        return cls(
            claims_file=parsed_args.claims,
            out_json=parsed_args.out_json,
            out_md=parsed_args.out_md,
            verbose=parsed_args.verbose,
            parallel=parsed_args.parallel,
            max_workers=parsed_args.max_workers,
            log_level=parsed_args.log_level.upper()
        )
    
    @staticmethod
    def _create_parser() -> argparse.ArgumentParser:
        """Create and configure argument parser."""
        parser = argparse.ArgumentParser(
            description="Run mathematical proofs from YAML claim specifications",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s --claims claims.yaml
  %(prog)s --claims claims.yaml --verbose --parallel
  %(prog)s --claims claims.yaml --out_json results.json --out_md report.md
            """
        )
        
        # Required arguments
        parser.add_argument(
            "--claims",
            required=True,
            help="Path to YAML file containing claim specifications"
        )
        
        # Output options
        parser.add_argument(
            "--out_json",
            default="reports/proof_report.json",
            help="Output path for JSON report (default: %(default)s)"
        )
        parser.add_argument(
            "--out_md",
            default="reports/proof_report.md",
            help="Output path for Markdown report (default: %(default)s)"
        )
        
        # Processing options
        parser.add_argument(
            "--parallel",
            action="store_true",
            help="Process claims in parallel for better performance"
        )
        parser.add_argument(
            "--max-workers",
            type=int,
            help="Maximum number of parallel workers (default: CPU count)"
        )
        
        # Logging options
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Set logging level (default: %(default)s)"
        )
        
        return parser
    
    def setup_logging(self) -> None:
        """Configure logging based on configuration."""
        level = getattr(logging, self.log_level)
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        if self.verbose:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        
        logging.basicConfig(
            level=level,
            format=format_str,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        claims_path = Path(self.claims_file)
        if not claims_path.exists():
            raise FileNotFoundError(f"Claims file not found: {self.claims_file}")
        
        if not claims_path.suffix.lower() in ['.yaml', '.yml']:
            raise ValueError(f"Claims file must be YAML format: {self.claims_file}")
        
        if self.max_workers is not None and self.max_workers < 1:
            raise ValueError("max_workers must be positive")
