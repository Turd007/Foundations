"""Improved report generation utilities for proof results.

This module provides enhanced report generation with better performance,
maintainability, and extensibility.
"""

from __future__ import annotations
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union
from io import StringIO

from .claims import ClaimResult


logger = logging.getLogger(__name__)


# Constants
DEFAULT_MAX_DETAIL_LENGTH = 200
DEFAULT_JSON_INDENT = 2
MARKDOWN_TABLE_SEPARATOR = "|------|-------|--------|----------|--------------|-------------|"
MARKDOWN_TABLE_HEADER = "| Type | Total | Proved | Rejected | Inconclusive | Success Rate |"


class ProofStatus(Enum):
    """Enumeration for proof statuses."""
    PROVED = "proved"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class ReportFormat(Enum):
    """Supported report formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    CONSOLE = "console"


@dataclass
class ReportConfig:
    """Configuration options for report generation."""
    max_detail_length: int = DEFAULT_MAX_DETAIL_LENGTH
    json_indent: int = DEFAULT_JSON_INDENT
    include_timestamps: bool = True
    include_detailed_results: bool = True
    include_summary_table: bool = True
    sort_results_by: str = "id"  # "id", "type", "status"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_detail_length < 1:
            raise ValueError("max_detail_length must be positive")
        if self.json_indent < 0:
            raise ValueError("json_indent must be non-negative")
        if self.sort_results_by not in {"id", "type", "status"}:
            raise ValueError("sort_results_by must be 'id', 'type', or 'status'")


@dataclass
class ProofStatistics:
    """Statistics calculated from proof results."""
    total: int
    proved: int
    rejected: int
    inconclusive: int
    success_rate: float
    by_type: Dict[str, Dict[str, Union[int, float]]]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def from_results(cls, results: List[ClaimResult]) -> ProofStatistics:
        """Create statistics from a list of results."""
        if not results:
            return cls(
                total=0, proved=0, rejected=0, inconclusive=0,
                success_rate=0.0, by_type={}
            )
        
        # Count statuses efficiently
        status_counts = Counter(result.status for result in results)
        total = len(results)
        proved = status_counts.get(ProofStatus.PROVED.value, 0)
        rejected = status_counts.get(ProofStatus.REJECTED.value, 0)
        inconclusive = status_counts.get(ProofStatus.INCONCLUSIVE.value, 0)
        
        # Group by type efficiently
        by_type = defaultdict(lambda: defaultdict(int))
        for result in results:
            by_type[result.type]["total"] += 1
            by_type[result.type][result.status] += 1
        
        # Calculate success rates for each type
        for type_name, type_stats in by_type.items():
            type_total = type_stats["total"]
            type_proved = type_stats.get(ProofStatus.PROVED.value, 0)
            type_stats["success_rate"] = round(
                type_proved / type_total * 100, 1
            ) if type_total > 0 else 0.0
        
        return cls(
            total=total,
            proved=proved,
            rejected=rejected,
            inconclusive=inconclusive,
            success_rate=round(proved / total * 100, 1) if total > 0 else 0.0,
            by_type=dict(by_type)
        )


class ReportGenerationError(Exception):
    """Base exception for report generation errors."""
    pass


class FileWriteError(ReportGenerationError):
    """Exception raised when file writing fails."""
    pass


class InvalidConfigError(ReportGenerationError):
    """Exception raised when configuration is invalid."""
    pass


class StatusFormatter:
    """Handles formatting of proof statuses."""
    
    _EMOJI_MAP = {
        ProofStatus.PROVED.value: "✅",
        ProofStatus.REJECTED.value: "❌",
        ProofStatus.INCONCLUSIVE.value: "❓"
    }
    
    _BOOLEAN_MAP = {
        True: "✅ Yes",
        False: "❌ No"
    }
    
    @classmethod
    def get_status_emoji(cls, status: str) -> str:
        """Get emoji representation for a status."""
        return cls._EMOJI_MAP.get(status, "❓")
    
    @classmethod
    def format_detail_value(cls, value: Any, max_length: int = DEFAULT_MAX_DETAIL_LENGTH) -> str:
        """Format detail values for display with proper escaping and truncation."""
        if isinstance(value, bool):
            return cls._BOOLEAN_MAP[value]
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # Escape markdown special characters and limit length
            escaped = cls._escape_markdown(value)
            return cls._truncate_string(escaped, max_length)
        elif isinstance(value, (list, dict)):
            # Convert to JSON string for complex types
            try:
                json_str = json.dumps(value, indent=None, ensure_ascii=False)
                return cls._truncate_string(json_str, max_length)
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize value to JSON: {e}")
                return cls._truncate_string(str(value), max_length)
        else:
            return cls._truncate_string(str(value), max_length)
    
    @staticmethod
    def _escape_markdown(text: str) -> str:
        """Escape markdown special characters."""
        return text.replace('|', '\\|').replace('\n', ' ').replace('*', '\\*')
    
    @staticmethod
    def _truncate_string(text: str, max_length: int) -> str:
        """Truncate string with ellipsis if too long."""
        return text[:max_length] + "..." if len(text) > max_length else text


class ReportGenerator:
    """Enhanced report generator with improved performance and maintainability."""
    
    def __init__(self, results: List[ClaimResult], config: Optional[ReportConfig] = None):
        """Initialize with proof results and optional configuration."""
        self.results = self._validate_and_sort_results(results, config)
        self.config = config or ReportConfig()
        self._stats: Optional[ProofStatistics] = None
        self._formatter = StatusFormatter()
    
    def _validate_and_sort_results(self, results: List[ClaimResult], config: Optional[ReportConfig]) -> List[ClaimResult]:
        """Validate and sort results based on configuration."""
        if not isinstance(results, list):
            raise InvalidConfigError("Results must be a list")
        
        if not results:
            return results
        
        # Validate that all items are ClaimResult instances
        for i, result in enumerate(results):
            if not hasattr(result, 'id') or not hasattr(result, 'status') or not hasattr(result, 'type'):
                raise InvalidConfigError(f"Invalid result at index {i}: missing required attributes")
        
        # Sort results if configuration specifies
        sort_key = (config.sort_results_by if config else "id")
        if sort_key == "id":
            return sorted(results, key=lambda r: r.id)
        elif sort_key == "type":
            return sorted(results, key=lambda r: (r.type, r.id))
        elif sort_key == "status":
            return sorted(results, key=lambda r: (r.status, r.id))
        
        return results
    
    @property
    def stats(self) -> ProofStatistics:
        """Get cached statistics, calculating if necessary."""
        if self._stats is None:
            self._stats = ProofStatistics.from_results(self.results)
        return self._stats
    
    def write_json_report(self, output_path: Union[str, Path]) -> None:
        """Write results to JSON file with metadata and error handling."""
        output_path = Path(output_path)
        logger.info(f"Writing JSON report to {output_path}")
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            report_data = self._build_json_report_data()
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    report_data, 
                    f, 
                    indent=self.config.json_indent, 
                    ensure_ascii=False
                )
            
            logger.info(f"Successfully wrote JSON report with {len(self.results)} results")
            
        except OSError as e:
            error_msg = f"Failed to write JSON report to {output_path}: {e}"
            logger.error(error_msg)
            raise FileWriteError(error_msg) from e
        except (TypeError, ValueError) as e:
            error_msg = f"Failed to serialize JSON data: {e}"
            logger.error(error_msg)
            raise ReportGenerationError(error_msg) from e
    
    def write_markdown_report(self, output_path: Union[str, Path]) -> None:
        """Write results to Markdown file with enhanced formatting."""
        output_path = Path(output_path)
        logger.info(f"Writing Markdown report to {output_path}")
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                self._write_markdown_content(f)
            
            logger.info(f"Successfully wrote Markdown report with {len(self.results)} results")
            
        except OSError as e:
            error_msg = f"Failed to write Markdown report to {output_path}: {e}"
            logger.error(error_msg)
            raise FileWriteError(error_msg) from e
    
    def get_markdown_content(self) -> str:
        """Generate markdown content as string."""
        buffer = StringIO()
        self._write_markdown_content(buffer)
        return buffer.getvalue()
    
    def _build_json_report_data(self) -> Dict[str, Any]:
        """Build the complete JSON report data structure."""
        metadata = {
            "total_claims": len(self.results),
            "statistics": self._stats_to_dict(self.stats)
        }
        
        if self.config.include_timestamps:
            metadata["generated_at"] = datetime.now().isoformat()
        
        return {
            "metadata": metadata,
            "results": [self._result_to_dict(r) for r in self.results]
        }
    
    def _write_markdown_content(self, file: TextIO) -> None:
        """Write the complete Markdown content to file."""
        # Header
        file.write("# Proof Report\n\n")
        
        if self.config.include_timestamps:
            timestamp = datetime.now().strftime('%Y-%m-%d at %H:%M:%S')
            file.write(f"*Generated on {timestamp}*\n\n")
        
        # Summary statistics
        self._write_summary_section(file)
        
        # Results by type (if enabled)
        if self.config.include_summary_table:
            self._write_results_by_type(file)
        
        # Detailed results (if enabled)
        if self.config.include_detailed_results:
            self._write_detailed_results(file)
    
    def _write_summary_section(self, file: TextIO) -> None:
        """Write summary statistics section."""
        file.write("## Summary\n\n")
        
        stats = self.stats
        file.write(f"- **Total Claims**: {stats.total}\n")
        file.write(f"- **Proved**: {stats.proved} ({stats.success_rate}%)\n")
        file.write(f"- **Rejected**: {stats.rejected}\n")
        file.write(f"- **Inconclusive**: {stats.inconclusive}\n\n")
        
        if stats.by_type:
            file.write("### Results by Type\n\n")
            file.write(f"{MARKDOWN_TABLE_HEADER}\n")
            file.write(f"{MARKDOWN_TABLE_SEPARATOR}\n")
            
            for claim_type, type_stats in stats.by_type.items():
                file.write(
                    f"| {claim_type} | {type_stats['total']} | "
                    f"{type_stats.get('proved', 0)} | {type_stats.get('rejected', 0)} | "
                    f"{type_stats.get('inconclusive', 0)} | {type_stats['success_rate']}% |\n"
                )
            file.write("\n")
    
    def _write_results_by_type(self, file: TextIO) -> None:
        """Write results grouped by type."""
        if not self.results:
            return
        
        # Group results by type efficiently
        by_type = defaultdict(list)
        for result in self.results:
            by_type[result.type].append(result)
        
        file.write("## Results by Type\n\n")
        
        for claim_type, results in by_type.items():
            file.write(f"### {claim_type.title()} Claims\n\n")
            
            for result in results:
                status_emoji = self._formatter.get_status_emoji(result.status)
                file.write(f"- **{result.id}** {status_emoji} {result.status.upper()}\n")
            
            file.write("\n")
    
    def _write_detailed_results(self, file: TextIO) -> None:
        """Write detailed results section."""
        file.write("## Detailed Results\n\n")
        
        for i, result in enumerate(self.results):
            if i > 0:
                file.write("---\n\n")
            
            status_emoji = self._formatter.get_status_emoji(result.status)
            file.write(f"### {result.id} — {result.type} — {status_emoji} **{result.status.upper()}**\n\n")
            
            if result.details:
                file.write("**Details:**\n\n")
                for key, value in result.details.items():
                    formatted_value = self._formatter.format_detail_value(
                        value, self.config.max_detail_length
                    )
                    file.write(f"- **{key}**: {formatted_value}\n")
                file.write("\n")
            else:
                file.write("*No additional details available.*\n\n")
    
    def _stats_to_dict(self, stats: ProofStatistics) -> Dict[str, Any]:
        """Convert ProofStatistics to dictionary."""
        result = {
            "total": stats.total,
            "proved": stats.proved,
            "rejected": stats.rejected,
            "inconclusive": stats.inconclusive,
            "success_rate": stats.success_rate,
            "by_type": stats.by_type
        }
        
        if self.config.include_timestamps:
            result["timestamp"] = stats.timestamp
        
        return result
    
    def _result_to_dict(self, result: ClaimResult) -> Dict[str, Any]:
        """Convert ClaimResult to dictionary for JSON serialization."""
        return {
            "id": result.id,
            "type": result.type,
            "status": result.status,
            "details": result.details
        }
    
    def print_summary(self) -> None:
        """Print a brief summary to console with improved formatting."""
        stats = self.stats
        
        print(f"\n📊 Proof Results Summary:")
        print(f"   Total: {stats.total} claims")
        print(f"   ✅ Proved: {stats.proved} ({stats.success_rate}%)")
        print(f"   ❌ Rejected: {stats.rejected}")
        print(f"   ❓ Inconclusive: {stats.inconclusive}")
        
        if stats.by_type:
            print(f"\n📋 By Type:")
            for claim_type, type_stats in stats.by_type.items():
                success_rate = type_stats.get('success_rate', 0)
                proved = type_stats.get('proved', 0)
                total = type_stats.get('total', 0)
                print(f"   {claim_type}: {proved}/{total} ({success_rate}%)")
    
    def generate_report(self, format_type: ReportFormat, output_path: Optional[Union[str, Path]] = None) -> Optional[str]:
        """Generate report in specified format.
        
        Args:
            format_type: The format to generate (JSON, MARKDOWN, or CONSOLE)
            output_path: Path to write file (required for JSON and MARKDOWN)
            
        Returns:
            String content for CONSOLE format, None for file formats
            
        Raises:
            ValueError: If output_path is required but not provided
            ReportGenerationError: If report generation fails
        """
        if format_type in (ReportFormat.JSON, ReportFormat.MARKDOWN) and not output_path:
            raise ValueError(f"output_path is required for {format_type.value} format")
        
        try:
            if format_type == ReportFormat.JSON:
                self.write_json_report(output_path)
            elif format_type == ReportFormat.MARKDOWN:
                self.write_markdown_report(output_path)
            elif format_type == ReportFormat.CONSOLE:
                self.print_summary()
                return self.get_markdown_content()  # Return content for further processing
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate {format_type.value} report: {e}") from e
        
        return None


# Convenience functions for backward compatibility
def generate_json_report(results: List[ClaimResult], output_path: Union[str, Path], 
                        config: Optional[ReportConfig] = None) -> None:
    """Generate JSON report with default or custom configuration."""
    generator = ReportGenerator(results, config)
    generator.write_json_report(output_path)


def generate_markdown_report(results: List[ClaimResult], output_path: Union[str, Path],
                           config: Optional[ReportConfig] = None) -> None:
    """Generate Markdown report with default or custom configuration."""
    generator = ReportGenerator(results, config)
    generator.write_markdown_report(output_path)


def print_results_summary(results: List[ClaimResult], config: Optional[ReportConfig] = None) -> None:
    """Print results summary to console."""
    generator = ReportGenerator(results, config)
    generator.print_summary()
