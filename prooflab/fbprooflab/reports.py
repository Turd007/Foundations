"""Report generation utilities for proof results."""

from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .claims import ClaimResult


logger = logging.getLogger(__name__)


class ReportGenerator:
    """Handles generation of various report formats from proof results."""
    
    def __init__(self, results: List[ClaimResult]):
        """Initialize with proof results."""
        self.results = results
        self.stats = self._calculate_stats()
    
    def _calculate_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics from results."""
        total = len(self.results)
        if total == 0:
            return {"total": 0, "proved": 0, "rejected": 0, "inconclusive": 0}
        
        proved = sum(1 for r in self.results if r.status == "proved")
        rejected = sum(1 for r in self.results if r.status == "rejected")
        inconclusive = sum(1 for r in self.results if r.status == "inconclusive")
        
        # Group by type
        by_type = {}
        for result in self.results:
            if result.type not in by_type:
                by_type[result.type] = {"total": 0, "proved": 0, "rejected": 0, "inconclusive": 0}
            by_type[result.type]["total"] += 1
            by_type[result.type][result.status] += 1
        
        return {
            "total": total,
            "proved": proved,
            "rejected": rejected,
            "inconclusive": inconclusive,
            "success_rate": round(proved / total * 100, 1) if total > 0 else 0,
            "by_type": by_type,
            "timestamp": datetime.now().isoformat()
        }
    
    def write_json_report(self, output_path: str) -> None:
        """Write results to JSON file with metadata."""
        logger.info(f"Writing JSON report to {output_path}")
        
        json_path = Path(output_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            report_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_claims": len(self.results),
                    "statistics": self.stats
                },
                "results": [self._result_to_dict(r) for r in self.results]
            }
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully wrote JSON report with {len(self.results)} results")
            
        except Exception as e:
            logger.error(f"Failed to write JSON report: {e}")
            raise
    
    def write_markdown_report(self, output_path: str) -> None:
        """Write results to Markdown file with enhanced formatting."""
        logger.info(f"Writing Markdown report to {output_path}")
        
        md_path = Path(output_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(md_path, "w", encoding="utf-8") as f:
                self._write_markdown_content(f)
            
            logger.info(f"Successfully wrote Markdown report with {len(self.results)} results")
            
        except Exception as e:
            logger.error(f"Failed to write Markdown report: {e}")
            raise
    
    def _write_markdown_content(self, file) -> None:
        """Write the complete Markdown content to file."""
        # Header
        file.write("# Proof Report\n\n")
        file.write(f"*Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n\n")
        
        # Summary statistics
        self._write_summary_section(file)
        
        # Results by type
        self._write_results_by_type(file)
        
        # Detailed results
        self._write_detailed_results(file)
    
    def _write_summary_section(self, file) -> None:
        """Write summary statistics section."""
        file.write("## Summary\n\n")
        
        stats = self.stats
        file.write(f"- **Total Claims**: {stats['total']}\n")
        file.write(f"- **Proved**: {stats['proved']} ({stats['success_rate']}%)\n")
        file.write(f"- **Rejected**: {stats['rejected']}\n")
        file.write(f"- **Inconclusive**: {stats['inconclusive']}\n\n")
        
        if stats['by_type']:
            file.write("### Results by Type\n\n")
            file.write("| Type | Total | Proved | Rejected | Inconclusive | Success Rate |\n")
            file.write("|------|-------|--------|----------|--------------|-------------|\n")
            
            for claim_type, type_stats in stats['by_type'].items():
                success_rate = round(type_stats['proved'] / type_stats['total'] * 100, 1) if type_stats['total'] > 0 else 0
                file.write(f"| {claim_type} | {type_stats['total']} | {type_stats['proved']} | "
                          f"{type_stats['rejected']} | {type_stats['inconclusive']} | {success_rate}% |\n")
            file.write("\n")
    
    def _write_results_by_type(self, file) -> None:
        """Write results grouped by type."""
        if not self.results:
            return
        
        # Group results by type
        by_type = {}
        for result in self.results:
            if result.type not in by_type:
                by_type[result.type] = []
            by_type[result.type].append(result)
        
        file.write("## Results by Type\n\n")
        
        for claim_type, results in by_type.items():
            file.write(f"### {claim_type.title()} Claims\n\n")
            
            for result in results:
                status_emoji = self._get_status_emoji(result.status)
                file.write(f"- **{result.id}** {status_emoji} {result.status.upper()}\n")
            
            file.write("\n")
    
    def _write_detailed_results(self, file) -> None:
        """Write detailed results section."""
        file.write("## Detailed Results\n\n")
        
        for i, result in enumerate(self.results):
            if i > 0:
                file.write("---\n\n")
            
            status_emoji = self._get_status_emoji(result.status)
            file.write(f"### {result.id} — {result.type} — {status_emoji} **{result.status.upper()}**\n\n")
            
            if result.details:
                file.write("**Details:**\n\n")
                for key, value in result.details.items():
                    # Format the value nicely
                    formatted_value = self._format_detail_value(value)
                    file.write(f"- **{key}**: {formatted_value}\n")
                file.write("\n")
            else:
                file.write("*No additional details available.*\n\n")
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status."""
        emoji_map = {
            "proved": "✅",
            "rejected": "❌", 
            "inconclusive": "❓"
        }
        return emoji_map.get(status, "❓")
    
    def _format_detail_value(self, value: Any) -> str:
        """Format detail values for display."""
        if isinstance(value, bool):
            return "✅ Yes" if value else "❌ No"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # Escape markdown special characters and limit length
            escaped = value.replace('|', '\\|').replace('\n', ' ')
            return escaped[:200] + "..." if len(escaped) > 200 else escaped
        elif isinstance(value, (list, dict)):
            # Convert to JSON string for complex types
            json_str = json.dumps(value, indent=None)
            return json_str[:200] + "..." if len(json_str) > 200 else json_str
        else:
            return str(value)
    
    def _result_to_dict(self, result: ClaimResult) -> Dict[str, Any]:
        """Convert ClaimResult to dictionary for JSON serialization."""
        return {
            "id": result.id,
            "type": result.type,
            "status": result.status,
            "details": result.details
        }
    
    def print_summary(self) -> None:
        """Print a brief summary to console."""
        stats = self.stats
        print(f"\n[SUMMARY] Proof Results Summary:")
        print(f"   Total: {stats['total']} claims")
        print(f"   [PROVED] Proved: {stats['proved']} ({stats['success_rate']}%)")
        print(f"   [REJECTED] Rejected: {stats['rejected']}")
        print(f"   [INCONCLUSIVE] Inconclusive: {stats['inconclusive']}")
        
        if stats['by_type']:
            print(f"\n[BY TYPE] By Type:")
            for claim_type, type_stats in stats['by_type'].items():
                success_rate = round(type_stats['proved'] / type_stats['total'] * 100, 1) if type_stats['total'] > 0 else 0
                print(f"   {claim_type}: {type_stats['proved']}/{type_stats['total']} ({success_rate}%)")
