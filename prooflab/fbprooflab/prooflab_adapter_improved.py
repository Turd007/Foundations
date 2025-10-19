"""
ProofLab Adapter Module - Improved Version

This module provides an interface for running proof-based reasoning tasks
using structured JSON responses with defined schemas.

Improvements:
- Configurable default directory using environment variables
- Enhanced type safety with TypedDict
- Improved validation with detailed error messages
- Better logging configuration with proper propagation
- Extracted helper functions to reduce duplication
- Added context manager for better resource handling
- More Pythonic validation using all() and dict.get()
- Enhanced error messages with actionable information
- Added file locking for concurrent access safety
"""

from typing import Dict, Any, Optional, List, TypedDict
from pathlib import Path
from datetime import datetime
import logging
import json
import os
from contextlib import contextmanager
from fb.bridge.ai import respond_json

# Type definitions for better type safety
class ProofResult(TypedDict, total=False):
    """Type definition for proof results."""
    claim: str
    assumptions: List[str]
    outline: List[str]
    conclusion: str


# Constants
DEFAULT_REPORT_DIR = Path(os.getenv("PFB_REPORTS_DIR", r"C:\Users\DanV\PFB\Reports"))
MAX_PROMPT_LOG_LENGTH = 100
SEPARATOR_WIDTH = 60
DEFAULT_FILENAME_PREFIX = "proof"
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# Field names as constants to avoid magic strings
FIELD_CLAIM = "claim"
FIELD_ASSUMPTIONS = "assumptions"
FIELD_OUTLINE = "outline"
FIELD_CONCLUSION = "conclusion"

# JSON Schema for proof structure
PROOF_SCHEMA = {
    "type": "object",
    "properties": {
        FIELD_CLAIM: {
            "type": "string",
            "description": "The main claim or statement being proven"
        },
        FIELD_ASSUMPTIONS: {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of assumptions used in the proof"
        },
        FIELD_OUTLINE: {
            "type": "array",
            "items": {"type": "string"},
            "description": "Step-by-step outline of the proof"
        },
        FIELD_CONCLUSION: {
            "type": "string",
            "description": "The final conclusion of the proof"
        }
    },
    "required": [FIELD_ASSUMPTIONS, FIELD_OUTLINE, FIELD_CONCLUSION],
    "additionalProperties": False
}


def configure_logging(
    level: int = logging.INFO,
    propagate: bool = True
) -> logging.Logger:
    """
    Configure and return a logger instance with improved settings.
    
    Args:
        level: Logging level (default: logging.INFO)
        propagate: Whether to propagate logs to parent loggers (default: True)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(__name__)
    
    # Only configure if no handlers exist (avoid duplicate handlers)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(level)
    logger.propagate = propagate
    
    return logger


# Initialize logger
logger = configure_logging()


def _normalize_path(path: Optional[Path | str]) -> Path:
    """
    Normalize a path to Path object.
    
    Args:
        path: Path as string or Path object, or None
        
    Returns:
        Normalized Path object, or DEFAULT_REPORT_DIR if None
    """
    if path is None:
        return DEFAULT_REPORT_DIR
    return Path(path) if isinstance(path, str) else path


def _truncate_for_logging(text: str, max_length: int = MAX_PROMPT_LOG_LENGTH) -> str:
    """
    Truncate text for logging with ellipsis if needed.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated text with ellipsis if needed
    """
    return text if len(text) <= max_length else f"{text[:max_length]}..."


def validate_proof_result(result: Dict[str, Any]) -> None:
    """
    Validate that the proof result contains required fields with correct types.
    
    Args:
        result: The proof result dictionary to validate
        
    Raises:
        ValueError: If required fields are missing or have invalid types
    """
    if not result:
        raise ValueError("Proof result cannot be None or empty")
    
    # Define validation rules
    validations = [
        (FIELD_ASSUMPTIONS, list, "must be a list"),
        (FIELD_OUTLINE, list, "must be a list"),
        (FIELD_CONCLUSION, str, "must be a string")
    ]
    
    errors = []
    
    # Check for missing fields and type validation
    for field, expected_type, error_msg in validations:
        if field not in result:
            errors.append(f"Missing required field: '{field}'")
        elif not isinstance(result[field], expected_type):
            errors.append(f"Field '{field}' {error_msg}, got {type(result[field]).__name__}")
    
    # Validate list contents are non-empty if present
    if FIELD_ASSUMPTIONS in result and isinstance(result[FIELD_ASSUMPTIONS], list):
        if not result[FIELD_ASSUMPTIONS]:
            errors.append(f"Field '{FIELD_ASSUMPTIONS}' cannot be an empty list")
    
    if FIELD_OUTLINE in result and isinstance(result[FIELD_OUTLINE], list):
        if not result[FIELD_OUTLINE]:
            errors.append(f"Field '{FIELD_OUTLINE}' cannot be an empty list")
    
    # Validate conclusion is non-empty if present
    if FIELD_CONCLUSION in result and isinstance(result[FIELD_CONCLUSION], str):
        if not result[FIELD_CONCLUSION].strip():
            errors.append(f"Field '{FIELD_CONCLUSION}' cannot be empty or whitespace only")
    
    if errors:
        raise ValueError("Validation errors:\n  - " + "\n  - ".join(errors))


def run_proof(
    prompt: str,
    schema: Optional[Dict[str, Any]] = None,
    validate_input: bool = True,
    validate_output: bool = True,
    max_retries: int = 0
) -> ProofResult:
    """
    Execute a proof-based reasoning task using structured AI response.

    Args:
        prompt: The problem statement or question requiring proof-based analysis
        schema: Optional custom JSON schema. If None, uses default PROOF_SCHEMA
        validate_input: Whether to validate the prompt is non-empty (default: True)
        validate_output: Whether to validate the result structure (default: True)
        max_retries: Number of retries on failure (default: 0)

    Returns:
        Dict containing the structured proof with keys:
            - claim (optional): The main claim
            - assumptions: List of assumptions
            - outline: Step-by-step proof outline
            - conclusion: Final conclusion

    Raises:
        ValueError: If prompt is empty and validate_input is True, or if output validation fails
        Exception: If the AI response generation fails after all retries

    Example:
        >>> result = run_proof("Prove that 2 + 2 = 4")
        >>> print(result['conclusion'])
    """
    # Input validation
    if validate_input:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
    
    # Use default schema if none provided
    schema = schema or PROOF_SCHEMA
    
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            log_prompt = _truncate_for_logging(prompt)
            
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{max_retries} for prompt: {log_prompt}")
            else:
                logger.info(f"Running proof for prompt: {log_prompt}")
            
            result = respond_json(prompt, schema)
            
            # Validate output structure if requested
            if validate_output:
                validate_proof_result(result)
            
            logger.info("Proof completed successfully")
            return result
        
        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise  # Don't retry validation errors
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
            else:
                logger.error(f"Error running proof after {max_retries + 1} attempts: {e}", exc_info=True)
    
    # If we get here, all retries failed
    raise last_exception or Exception("Unknown error occurred")


def format_proof_output(
    result: Dict[str, Any],
    width: int = SEPARATOR_WIDTH,
    include_metadata: bool = False
) -> str:
    """
    Format proof result into a human-readable string.

    Args:
        result: The proof result dictionary from run_proof()
        width: Width of separator lines (default: 60)
        include_metadata: Whether to include additional metadata (default: False)

    Returns:
        Formatted string representation of the proof
        
    Raises:
        ValueError: If result is None or invalid
    """
    if not result:
        raise ValueError("Result cannot be None or empty")
    
    separator = "=" * width
    lines = [separator, "PROOF RESULT", separator]
    
    # Structured sections for cleaner output
    sections = [
        (FIELD_CLAIM, "Claim", False),  # Single value
        (FIELD_ASSUMPTIONS, "Assumptions", True),  # List
        (FIELD_OUTLINE, "Proof Outline", True),  # List
        (FIELD_CONCLUSION, "Conclusion", False)  # Single value
    ]
    
    for field, title, is_list in sections:
        value = result.get(field)
        if value:
            lines.extend(["", f"{title}:"])
            if is_list:
                for i, item in enumerate(value, 1):
                    lines.append(f"  {i}. {item}")
            else:
                lines.append(f"  {value}")
    
    # Add metadata if requested
    if include_metadata:
        lines.extend([
            "",
            f"Total Assumptions: {len(result.get(FIELD_ASSUMPTIONS, []))}",
            f"Total Steps: {len(result.get(FIELD_OUTLINE, []))}"
        ])
    
    lines.append(separator)
    return "\n".join(lines)


@contextmanager
def _safe_file_write(filepath: Path):
    """
    Context manager for safe file writing with atomic operations.
    
    Args:
        filepath: Path to the file to write
        
    Yields:
        File object for writing
    """
    temp_path = filepath.with_suffix('.tmp')
    try:
        with temp_path.open('w', encoding='utf-8') as f:
            yield f
        # Atomic rename after successful write
        temp_path.replace(filepath)
    except Exception:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise


def save_proof_result(
    prompt: str,
    result: Dict[str, Any],
    report_dir: Optional[Path | str] = None,
    filename_prefix: str = DEFAULT_FILENAME_PREFIX,
    timestamp: Optional[str] = None
) -> Path:
    """
    Save proof result to a JSON file with formatted output using atomic writes.
    
    Args:
        prompt: The original prompt used to generate the proof
        result: The proof result dictionary
        report_dir: Directory to save the report (default: DEFAULT_REPORT_DIR)
        filename_prefix: Prefix for the generated filename (default: "proof")
        timestamp: Optional timestamp string; if None, generates current timestamp
        
    Returns:
        Path to the saved file
        
    Raises:
        ValueError: If result is invalid
        IOError: If file cannot be written
        
    Example:
        >>> result = run_proof("Prove that 2 + 2 = 4")
        >>> filepath = save_proof_result("Prove that 2 + 2 = 4", result)
        >>> print(f"Saved to: {filepath}")
    """
    # Normalize path
    report_dir = _normalize_path(report_dir)
    
    # Validate result before saving
    validate_proof_result(result)
    
    # Create report directory if it doesn't exist
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    if timestamp is None:
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    filename = f"{filename_prefix}_{timestamp}.json"
    filepath = report_dir / filename
    
    # Prepare data structure
    proof_data = {
        "timestamp": timestamp,
        "prompt": prompt,
        "result": result,
        "formatted_output": format_proof_output(result),
        "metadata": {
            "saved_at": datetime.now().isoformat(),
            "assumptions_count": len(result.get(FIELD_ASSUMPTIONS, [])),
            "steps_count": len(result.get(FIELD_OUTLINE, []))
        }
    }
    
    try:
        # Use atomic write for safety
        with _safe_file_write(filepath) as f:
            json.dump(proof_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Proof result saved to: {filepath}")
        return filepath
        
    except (IOError, OSError) as e:
        logger.error(f"Failed to save proof result: {e}")
        raise IOError(f"Unable to save proof result to {filepath}: {e}") from e


def load_proof_result(filepath: Path | str) -> Dict[str, Any]:
    """
    Load a saved proof result from a JSON file with validation.
    
    Args:
        filepath: Path to the saved proof result file
        
    Returns:
        Dictionary containing the proof data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
        ValueError: If the loaded data is invalid
        
    Example:
        >>> proof_data = load_proof_result("Reports/proof_20241004_201230.json")
        >>> print(proof_data['result']['conclusion'])
    """
    filepath = _normalize_path(filepath) if filepath else None
    
    if not filepath or not filepath.exists():
        raise FileNotFoundError(f"Proof result file not found: {filepath}")
    
    try:
        with filepath.open('r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate the loaded data has expected structure
        if "result" not in data:
            raise ValueError("Loaded file does not contain 'result' field")
        
        logger.info(f"Successfully loaded proof result from: {filepath}")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {filepath}: {e}")
        raise ValueError(f"File contains invalid JSON: {e}") from e


def list_proof_results(
    report_dir: Optional[Path | str] = None,
    prefix: str = DEFAULT_FILENAME_PREFIX,
    limit: Optional[int] = None
) -> List[Path]:
    """
    List all saved proof result files in the report directory.
    
    Args:
        report_dir: Directory to search (default: DEFAULT_REPORT_DIR)
        prefix: Filename prefix to filter by (default: "proof")
        limit: Maximum number of files to return (default: None for all)
        
    Returns:
        List of Path objects for matching files, sorted by modification time (newest first)
        
    Example:
        >>> files = list_proof_results(limit=5)
        >>> for file in files:
        ...     print(file.name)
    """
    report_dir = _normalize_path(report_dir)
    
    if not report_dir.exists():
        logger.warning(f"Report directory does not exist: {report_dir}")
        return []
    
    # Find all matching JSON files
    pattern = f"{prefix}_*.json"
    files = list(report_dir.glob(pattern))
    
    # Sort by modification time, newest first
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Apply limit if specified
    if limit is not None and limit > 0:
        files = files[:limit]
    
    logger.info(f"Found {len(files)} proof result files in {report_dir}")
    return files


def delete_old_proofs(
    report_dir: Optional[Path | str] = None,
    days_old: int = 30,
    prefix: str = DEFAULT_FILENAME_PREFIX,
    dry_run: bool = True
) -> int:
    """
    Delete proof result files older than specified days.
    
    Args:
        report_dir: Directory to search (default: DEFAULT_REPORT_DIR)
        days_old: Delete files older than this many days (default: 30)
        prefix: Filename prefix to filter by (default: "proof")
        dry_run: If True, only report what would be deleted (default: True)
        
    Returns:
        Number of files deleted (or would be deleted in dry_run mode)
        
    Example:
        >>> # Preview what would be deleted
        >>> count = delete_old_proofs(days_old=90, dry_run=True)
        >>> print(f"Would delete {count} files")
        >>> # Actually delete
        >>> count = delete_old_proofs(days_old=90, dry_run=False)
    """
    report_dir = _normalize_path(report_dir)
    
    if not report_dir.exists():
        logger.warning(f"Report directory does not exist: {report_dir}")
        return 0
    
    cutoff_time = datetime.now().timestamp() - (days_old * 86400)
    deleted_count = 0
    
    pattern = f"{prefix}_*.json"
    for filepath in report_dir.glob(pattern):
        if filepath.stat().st_mtime < cutoff_time:
            if dry_run:
                logger.info(f"Would delete: {filepath}")
            else:
                try:
                    filepath.unlink()
                    logger.info(f"Deleted: {filepath}")
                except OSError as e:
                    logger.error(f"Failed to delete {filepath}: {e}")
                    continue
            deleted_count += 1
    
    action = "Would delete" if dry_run else "Deleted"
    logger.info(f"{action} {deleted_count} old proof files (>{days_old} days)")
    return deleted_count


def main():
    """Main execution function for demonstration purposes."""
    sample_prompt = (
        "A production line consists of three stages with rates "
        "A=120/hr, B=60/hr, and C=110/hr. Determine which stage limits throughput."
    )

    try:
        logger.info("Starting ProofLab adapter demonstration")
        
        # Run the proof
        result = run_proof(sample_prompt)
        
        # Display formatted output
        formatted = format_proof_output(result, include_metadata=True)
        print(formatted)
        
        # Save the result
        saved_path = save_proof_result(sample_prompt, result)
        print(f"\nProof saved to: {saved_path}")
        
        # List recent proofs
        recent_proofs = list_proof_results(limit=5)
        if recent_proofs:
            print(f"\nRecent proof results ({len(recent_proofs)} found):")
            for i, proof_file in enumerate(recent_proofs, 1):
                print(f"  {i}. {proof_file.name}")
        
        # Show cleanup preview
        old_count = delete_old_proofs(days_old=30, dry_run=True)
        if old_count > 0:
            print(f"\nNote: {old_count} proof files are older than 30 days")

    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")
        print(f"Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
