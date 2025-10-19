"""Cascade export interface and CLI.

This module provides functionality to export data in canonical format,
supporting both programmatic API and command-line interface usage.

Example:
    Basic usage:
        >>> from interface_improved import export_to_canon
        >>> data = {"key": "value", "count": 42}
        >>> success = export_to_canon("output.json", data)
        
    CLI usage:
        $ python interface_improved.py output.json --input data.json --verbose
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    """Configuration for export operations.
    
    Attributes:
        format_version: Version string for the canonical format
        pretty_print: Whether to format JSON with indentation
        include_metadata: Whether to include export metadata
        compression: Optional compression type ('gzip', 'bzip2', or None)
        encoding: Character encoding for text output
    """
    format_version: str = "1.0"
    pretty_print: bool = True
    include_metadata: bool = True
    compression: Optional[str] = None
    encoding: str = 'utf-8'


class ExportError(Exception):
    """Exception raised for export operation failures."""
    pass


def validate_output_path(
    output: Union[str, Path],
    overwrite: bool = False
) -> Path:
    """Validate and prepare output path.
    
    Args:
        output: Output file path (string or Path object)
        overwrite: Whether to allow overwriting existing files
        
    Returns:
        Validated Path object
        
    Raises:
        ValueError: If output path is empty or invalid
        FileExistsError: If file exists and overwrite is False
    """
    if not output:
        raise ValueError("Output path cannot be empty")
    
    output_path = Path(output)
    
    # Check if parent directory is valid
    if output_path.parent != Path('.') and not output_path.parent.exists():
        logger.debug(f"Creating parent directory: {output_path.parent}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check for existing file
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}. "
            "Use overwrite=True to replace it."
        )
    
    return output_path


def prepare_export_data(
    data: Dict[str, Any],
    config: ExportConfig
) -> Dict[str, Any]:
    """Prepare data for export with metadata.
    
    Args:
        data: Data dictionary to export
        config: Export configuration
        
    Returns:
        Data dictionary with optional metadata
    """
    if not config.include_metadata:
        return data
    
    # Wrap data with metadata
    export_data = {
        "metadata": {
            "format_version": config.format_version,
            "export_timestamp": datetime.utcnow().isoformat(),
            "encoding": config.encoding,
        },
        "data": data
    }
    
    return export_data


def export_to_canon(
    output: Union[str, Path],
    data: Optional[Dict[str, Any]] = None,
    config: Optional[ExportConfig] = None,
    overwrite: bool = False
) -> bool:
    """Export data to canonical JSON format.
    
    Exports the provided data dictionary to a file in canonical JSON format.
    Supports various configuration options including metadata inclusion,
    formatting, and validation.
    
    Args:
        output: Output file path (string or Path object)
        data: Dictionary of data to export (defaults to empty dict)
        config: Export configuration (uses defaults if None)
        overwrite: Whether to overwrite existing files
        
    Returns:
        True if export succeeded, False otherwise
        
    Raises:
        ValueError: If output path is invalid or data is not serializable
        FileExistsError: If output exists and overwrite is False
        ExportError: If export operation fails
        
    Example:
        >>> data = {"temperature": 25.5, "humidity": 60}
        >>> export_to_canon("sensor_data.json", data)
        True
    """
    # Set defaults
    data = data if data is not None else {}
    config = config or ExportConfig()
    
    try:
        # Validate output path
        output_path = validate_output_path(output, overwrite)
        
        logger.info(f"Exporting to canonical format: {output_path}")
        logger.debug(f"Export config: {asdict(config)}")
        
        # Prepare data with metadata
        export_data = prepare_export_data(data, config)
        
        # Validate data is JSON-serializable
        try:
            json.dumps(export_data)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Data is not JSON-serializable: {e}")
        
        # Write to file
        indent = 2 if config.pretty_print else None
        with open(output_path, 'w', encoding=config.encoding) as f:
            json.dump(export_data, f, indent=indent, ensure_ascii=False)
        
        logger.info(f"Successfully exported {len(data)} items to {output_path}")
        return True
        
    except (ValueError, FileExistsError) as e:
        logger.error(f"Export validation failed: {e}")
        raise
        
    except IOError as e:
        logger.error(f"Failed to write file: {e}")
        raise ExportError(f"File operation failed: {e}")
        
    except Exception as e:
        logger.exception(f"Unexpected error during export: {e}")
        raise ExportError(f"Export failed: {e}")


def load_input_data(input_path: Union[str, Path]) -> Dict[str, Any]:
    """Load data from input file.
    
    Args:
        input_path: Path to input JSON file
        
    Returns:
        Loaded data dictionary
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If input file is not valid JSON
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    logger.info(f"Loading input data from: {input_path}")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.debug(f"Loaded {len(data)} items from input")
        return data
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in input file: {e}")


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application.
    
    Args:
        verbose: Enable debug-level logging if True
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main() -> int:
    """CLI entry point for export operations.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="Export data to canonical JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export from input file to output file
  %(prog)s output.json --input data.json
  
  # Export with verbose logging
  %(prog)s output.json --input data.json --verbose
  
  # Export with custom format version
  %(prog)s output.json --input data.json --format-version "2.0"
  
  # Overwrite existing file
  %(prog)s output.json --input data.json --overwrite
        """
    )
    
    # Required arguments
    parser.add_argument(
        'output',
        type=str,
        help='Output file path for canonical export'
    )
    
    # Optional arguments
    parser.add_argument(
        '--input',
        type=str,
        help='Input JSON file path (optional, generates sample data if not provided)'
    )
    
    parser.add_argument(
        '--format-version',
        type=str,
        default='1.0',
        help='Format version string (default: 1.0)'
    )
    
    parser.add_argument(
        '--no-metadata',
        action='store_true',
        help='Exclude metadata from export'
    )
    
    parser.add_argument(
        '--no-pretty-print',
        action='store_true',
        help='Disable JSON pretty printing'
    )
    
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing output file'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose debug output'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    setup_logging(args.verbose)
    
    try:
        # Load or generate data
        if args.input:
            data = load_input_data(args.input)
        else:
            logger.warning("No input file provided, using sample data")
            data = {
                "sample": "data",
                "timestamp": datetime.utcnow().isoformat(),
                "count": 0
            }
        
        # Create export configuration
        config = ExportConfig(
            format_version=args.format_version,
            pretty_print=not args.no_pretty_print,
            include_metadata=not args.no_metadata
        )
        
        # Perform export
        success = export_to_canon(
            args.output,
            data,
            config,
            overwrite=args.overwrite
        )
        
        if success:
            logger.info("Export completed successfully")
            return 0
        else:
            logger.error("Export failed")
            return 1
            
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 2
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 3
        
    except FileExistsError as e:
        logger.error(f"File already exists: {e}")
        return 4
        
    except ExportError as e:
        logger.error(f"Export error: {e}")
        return 5
        
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 99


if __name__ == '__main__':
    sys.exit(main())
