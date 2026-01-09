"""
Research Agent implementation.
Specialized for web research, document analysis, and information gathering.
"""

import asyncio
from typing import Any, Optional
from uuid import UUID

import httpx
import structlog

from shared.models.schemas import AgentType
from agents.base_agent import BaseAgent
from config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class ResearchAgent(BaseAgent):
    """
    Agent specialized for research tasks.
    Capabilities include web search, document analysis, and information synthesis.
    """

    def __init__(
        self,
        agent_id: UUID,
        name: str = "ResearchAgent",
        **kwargs,
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.RESEARCH,
            name=name,
            **kwargs,
        )
        self._register_research_tools()

    def _get_default_system_prompt(self) -> str:
        """Get the research agent's system prompt."""
        return """You are a Research Agent specialized in gathering and analyzing information.

Your capabilities include:
1. Searching the web for relevant information
2. Analyzing and summarizing documents
3. Synthesizing information from multiple sources
4. Fact-checking and verification
5. Creating comprehensive research reports

Guidelines:
- Always cite your sources when presenting information
- Be thorough but concise in your research
- Highlight key findings and insights
- Acknowledge uncertainty when information is incomplete
- Organize findings in a clear, structured manner

When researching, follow these steps:
1. Understand the research question or topic
2. Identify relevant sources and search terms
3. Gather information from multiple sources
4. Synthesize and analyze the findings
5. Present a clear summary with citations"""

    def _register_research_tools(self) -> None:
        """Register research-specific tools."""
        self.register_tool(self._web_search)
        self.register_tool(self._fetch_url)
        self.register_tool(self._summarize_text)

    async def _web_search(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Perform a web search using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })

            logger.debug(
                "Web search completed",
                query=query,
                results_count=len(results),
            )
            return results

        except Exception as e:
            logger.error("Web search failed", query=query, error=str(e))
            return []

    async def _fetch_url(self, url: str) -> str:
        """
        Fetch and extract text content from a URL.

        Args:
            url: URL to fetch

        Returns:
            Extracted text content
        """
        try:
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    timeout=30,
                    follow_redirects=True,
                    headers={"User-Agent": "ResearchBot/1.0"},
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)

            # Truncate if too long
            if len(text) > 10000:
                text = text[:10000] + "\n\n[Content truncated...]"

            logger.debug("URL fetched successfully", url=url, length=len(text))
            return text

        except Exception as e:
            logger.error("Failed to fetch URL", url=url, error=str(e))
            return f"Error fetching URL: {str(e)}"

    async def _summarize_text(self, text: str, max_length: int = 500) -> str:
        """
        Summarize a long text.

        Args:
            text: Text to summarize
            max_length: Maximum summary length

        Returns:
            Summary text
        """
        if len(text) < max_length:
            return text

        prompt = f"""Please provide a concise summary of the following text in no more than {max_length} characters:

{text[:5000]}

Summary:"""

        return await self.invoke_llm(prompt, include_memory=False)

    async def execute(self, task_input: dict) -> dict:
        """
        Execute a research task.

        Args:
            task_input: Task input containing:
                - query: Research query or topic
                - context: Additional context
                - depth: Research depth (shallow, medium, deep)

        Returns:
            Research results including:
                - summary: Executive summary
                - findings: Detailed findings
                - sources: List of sources used
        """
        query = task_input.get("query", "")
        context = task_input.get("context", {})
        depth = task_input.get("depth", "medium")

        if not query:
            return {"error": "No research query provided"}

        logger.info(
            "Starting research task",
            agent_id=str(self.agent_id),
            query=query[:100],
            depth=depth,
        )

        await self.report_progress(0.1, "Starting research...")

        # Step 1: Web search
        await self.report_progress(0.2, "Searching the web...")
        max_results = {"shallow": 3, "medium": 5, "deep": 10}.get(depth, 5)
        search_results = await self._web_search(query, max_results=max_results)

        if not search_results:
            # Fallback to LLM knowledge
            await self.report_progress(0.5, "No web results, using knowledge base...")
            response = await self.invoke_llm(
                f"Research the following topic: {query}",
                context=context,
            )
            return {
                "summary": response,
                "findings": [{"source": "LLM Knowledge", "content": response}],
                "sources": [],
            }

        # Step 2: Fetch content from top results
        await self.report_progress(0.4, "Gathering detailed information...")
        findings = []
        sources = []

        for i, result in enumerate(search_results[:3]):  # Limit to top 3
            try:
                content = await self._fetch_url(result["url"])
                if content and not content.startswith("Error"):
                    summary = await self._summarize_text(content)
                    findings.append({
                        "source": result["title"],
                        "url": result["url"],
                        "content": summary,
                    })
                    sources.append({
                        "title": result["title"],
                        "url": result["url"],
                    })
            except Exception as e:
                logger.warning(
                    "Failed to process search result",
                    url=result.get("url"),
                    error=str(e),
                )

        await self.report_progress(0.7, "Synthesizing findings...")

        # Step 3: Synthesize findings
        findings_text = "\n\n".join([
            f"Source: {f['source']}\n{f['content']}"
            for f in findings
        ])

        synthesis_prompt = f"""Based on the following research findings, provide a comprehensive summary for the query: "{query}"

Research Findings:
{findings_text}

Please provide:
1. An executive summary (2-3 sentences)
2. Key findings (bullet points)
3. Conclusions and recommendations

Format your response clearly with headers."""

        synthesis = await self.invoke_llm(synthesis_prompt, context=context)

        await self.report_progress(1.0, "Research complete")

        # Store findings in memory
        if self.memory_enabled:
            memory_manager = await self.get_memory_manager()
            await memory_manager.store_knowledge(
                content=f"Research on '{query}': {synthesis[:500]}",
                metadata={"query": query, "sources_count": len(sources)},
            )

        return {
            "summary": synthesis,
            "findings": findings,
            "sources": sources,
            "query": query,
            "depth": depth,
        }
