"""
Analysis Agent implementation.
Specialized for data analysis, pattern recognition, and insight generation.
"""

import json
from typing import Any, Optional
from uuid import UUID

import structlog

from shared.models.schemas import AgentType
from agents.base_agent import BaseAgent
from config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class AnalysisAgent(BaseAgent):
    """
    Agent specialized for data analysis tasks.
    Capabilities include data processing, pattern recognition, and insight generation.
    """

    def __init__(
        self,
        agent_id: UUID,
        name: str = "AnalysisAgent",
        **kwargs,
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.ANALYSIS,
            name=name,
            **kwargs,
        )

    def _get_default_system_prompt(self) -> str:
        """Get the analysis agent's system prompt."""
        return """You are an Analysis Agent specialized in data analysis and insight generation.

Your capabilities include:
1. Analyzing structured and unstructured data
2. Identifying patterns and trends
3. Generating insights and recommendations
4. Statistical analysis and interpretation
5. Creating clear visualizations descriptions
6. Comparative analysis

Guidelines:
- Always validate data before analysis
- Quantify findings when possible
- Highlight significant patterns and outliers
- Provide actionable recommendations
- Acknowledge limitations in the data
- Present findings in a clear, structured manner

When analyzing data:
1. Understand the analysis objective
2. Examine data quality and structure
3. Apply appropriate analytical methods
4. Identify key patterns and insights
5. Formulate conclusions and recommendations"""

    async def _analyze_structure(self, data: Any) -> dict:
        """
        Analyze the structure of input data.

        Args:
            data: Input data to analyze

        Returns:
            Structure analysis results
        """
        structure = {
            "type": type(data).__name__,
            "size": None,
            "fields": [],
            "sample": None,
        }

        if isinstance(data, dict):
            structure["size"] = len(data)
            structure["fields"] = list(data.keys())
            structure["sample"] = {k: type(v).__name__ for k, v in list(data.items())[:5]}
        elif isinstance(data, list):
            structure["size"] = len(data)
            if data and isinstance(data[0], dict):
                structure["fields"] = list(data[0].keys()) if data else []
                structure["sample"] = data[:3] if len(data) >= 3 else data
        elif isinstance(data, str):
            structure["size"] = len(data)
            structure["sample"] = data[:200] if len(data) > 200 else data

        return structure

    async def _calculate_statistics(self, data: list[dict], numeric_fields: list[str]) -> dict:
        """
        Calculate basic statistics for numeric fields.

        Args:
            data: List of data records
            numeric_fields: Fields to calculate statistics for

        Returns:
            Statistics dictionary
        """
        stats = {}

        for field in numeric_fields:
            values = []
            for record in data:
                val = record.get(field)
                if val is not None:
                    try:
                        values.append(float(val))
                    except (ValueError, TypeError):
                        continue

            if values:
                sorted_vals = sorted(values)
                n = len(values)
                stats[field] = {
                    "count": n,
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / n,
                    "median": sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2,
                }

        return stats

    async def _identify_patterns(self, data: Any, context: dict) -> list[str]:
        """
        Use LLM to identify patterns in data.

        Args:
            data: Data to analyze
            context: Analysis context

        Returns:
            List of identified patterns
        """
        # Prepare data sample for LLM
        if isinstance(data, list):
            sample = data[:20]  # Limit to 20 records
        elif isinstance(data, dict):
            sample = {k: v for k, v in list(data.items())[:20]}
        else:
            sample = str(data)[:5000]

        prompt = f"""Analyze the following data and identify key patterns, trends, and anomalies:

Data Sample:
{json.dumps(sample, indent=2, default=str) if not isinstance(sample, str) else sample}

Analysis Context:
{json.dumps(context, indent=2) if context else "General analysis"}

Please identify:
1. Key patterns and trends
2. Notable anomalies or outliers
3. Relationships between data points
4. Potential areas of concern

List each finding as a separate point."""

        response = await self.invoke_llm(prompt, include_memory=False)

        # Parse patterns from response
        patterns = []
        for line in response.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•") or line[0].isdigit()):
                patterns.append(line.lstrip("-•0123456789. "))

        return patterns if patterns else [response]

    async def _generate_insights(
        self,
        data: Any,
        structure: dict,
        statistics: dict,
        patterns: list[str],
        objective: str,
    ) -> dict:
        """
        Generate comprehensive insights from analysis.

        Args:
            data: Original data
            structure: Data structure analysis
            statistics: Calculated statistics
            patterns: Identified patterns
            objective: Analysis objective

        Returns:
            Insights dictionary
        """
        analysis_summary = f"""
Data Structure:
- Type: {structure['type']}
- Size: {structure['size']}
- Fields: {', '.join(structure['fields'][:10]) if structure['fields'] else 'N/A'}

Statistics:
{json.dumps(statistics, indent=2) if statistics else 'N/A'}

Identified Patterns:
{chr(10).join(f'- {p}' for p in patterns[:10])}
"""

        prompt = f"""Based on the following analysis of the data, provide actionable insights and recommendations.

Analysis Objective: {objective}

{analysis_summary}

Please provide:
1. Executive Summary (2-3 sentences)
2. Key Insights (3-5 bullet points)
3. Actionable Recommendations (2-4 items)
4. Potential Risks or Concerns
5. Suggested Next Steps

Format your response with clear headers."""

        insights_text = await self.invoke_llm(prompt)

        return {
            "executive_summary": insights_text.split("\n\n")[0] if insights_text else "",
            "full_analysis": insights_text,
            "patterns_count": len(patterns),
            "statistics_available": bool(statistics),
        }

    async def execute(self, task_input: dict) -> dict:
        """
        Execute an analysis task.

        Args:
            task_input: Task input containing:
                - data: Data to analyze (dict, list, or string)
                - objective: Analysis objective
                - context: Additional context
                - analysis_type: Type of analysis (descriptive, diagnostic, predictive)

        Returns:
            Analysis results including:
                - structure: Data structure analysis
                - statistics: Calculated statistics
                - patterns: Identified patterns
                - insights: Generated insights
                - recommendations: Actionable recommendations
        """
        data = task_input.get("data") or task_input.get("query", "")
        objective = task_input.get("objective", "General data analysis")
        context = task_input.get("context", {})
        analysis_type = task_input.get("analysis_type", "descriptive")

        if not data:
            return {"error": "No data provided for analysis"}

        logger.info(
            "Starting analysis task",
            agent_id=str(self.agent_id),
            objective=objective[:100],
            analysis_type=analysis_type,
        )

        await self.report_progress(0.1, "Analyzing data structure...")

        # Step 1: Analyze structure
        structure = await self._analyze_structure(data)

        await self.report_progress(0.3, "Calculating statistics...")

        # Step 2: Calculate statistics (if applicable)
        statistics = {}
        if isinstance(data, list) and data and isinstance(data[0], dict):
            numeric_fields = [
                k for k, v in data[0].items()
                if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "").isdigit())
            ]
            if numeric_fields:
                statistics = await self._calculate_statistics(data, numeric_fields)

        await self.report_progress(0.5, "Identifying patterns...")

        # Step 3: Identify patterns
        patterns = await self._identify_patterns(data, context)

        await self.report_progress(0.7, "Generating insights...")

        # Step 4: Generate insights
        insights = await self._generate_insights(
            data=data,
            structure=structure,
            statistics=statistics,
            patterns=patterns,
            objective=objective,
        )

        await self.report_progress(1.0, "Analysis complete")

        # Store insights in memory
        if self.memory_enabled:
            memory_manager = await self.get_memory_manager()
            await memory_manager.store_knowledge(
                content=f"Analysis of '{objective}': {insights['executive_summary']}",
                metadata={"objective": objective, "patterns_count": len(patterns)},
            )

        return {
            "objective": objective,
            "analysis_type": analysis_type,
            "structure": structure,
            "statistics": statistics,
            "patterns": patterns,
            "insights": insights,
            "data_size": structure.get("size"),
        }
