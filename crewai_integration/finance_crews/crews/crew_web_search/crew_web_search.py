import os
from typing import Any, Dict, List, Tuple

from crewai import LLM, Agent, Crew, Process, Task, TaskOutput
from crewai.project import CrewBase, agent, crew, task

# Importing crewAI tools
from crewai_tools import (
    SerperDevTool,
)
from dotenv import load_dotenv

import weave

load_dotenv()

search_tool = SerperDevTool(n_results=10)


# Initialize Weave with your project name
weave.init(project_name='finance_web_search')


@CrewBase
class WebSearchCrew:
    """WebSearchCrew crew."""

    agents_config: Dict[str, Any]
    tasks_config: Dict[str, Any]
    agents: List[Any]
    tasks: List[Any]

    def __init__(
        self,
        llm: LLM,
        output_file: str = 'results/report.md',
        verbose: bool = True,
    ) -> None:
        """Initialize the RAGCrew crew."""

        super().__init__()
        self.agents_config = dict()
        self.tasks_config = dict()
        self.agents = list()
        self.tasks = list()
        self.llm = llm
        self.output_file = output_file
        self.verbose = verbose

    @agent  # type: ignore
    def researcher(self) -> Agent:
        """Add the RAG Agent."""

        return Agent(
            config=self.agents_config['researcher'],
            verbose=self.verbose,
            llm=self.llm,
            tools=[search_tool],
            allow_delegation=False,
        )

    @task  # type: ignore
    def research_task(self) -> Task:
        """Add the RAG Research Task."""

        return Task(
            config=self.tasks_config['research_task'],
        )

    @agent  # type: ignore
    def writer(self) -> Task:
        """Add the Analyst."""
        return Agent(
            config=self.agents_config['writer'],
            verbose=self.verbose,
            llm=self.llm,
            allow_delegation=False,
        )

    @task  # type: ignore
    def writing_task(self) -> Task:
        """Add the Writing Task."""

        # Decorate your guardrail function with `@weave.op()`
        @weave.op(name='guardrail-validate_report')
        def validate_report(result: TaskOutput) -> Tuple[bool, Any]:
            # Get raw string result
            result = result.raw

            """Validate blog content meets requirements."""
            try:
                # Check word count
                word_count = len(result.split())

                if word_count > 10000:
                    return (
                        False,
                        {
                            'error': 'Blog content exceeds 10000 words',
                            'code': 'WORD_COUNT_ERROR',
                            'context': {'word_count': word_count},
                        },
                    )

                # Additional validation logic here
                return (True, result.strip())
            except Exception as e:
                return (
                    False,
                    {
                        'error': 'Unexpected error during validation',
                        'code': 'SYSTEM_ERROR',
                    },
                )

        return Task(
            config=self.tasks_config['writing_task'],
            output_file=self.output_file,
            guardrail=validate_report,
        )

    @crew  # type: ignore
    def crew(self) -> Crew:
        """Create the RAGCrew crew."""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=self.verbose,
        )


if __name__ == '__main__':
    web_search_crew = WebSearchCrew(
        llm=LLM(
            model='sambanova/Meta-Llama-3.3-70B-Instruct',
            temperature=0,
            base_url=os.getenv('SAMBANOVA_URL'),
            api_key=os.getenv('SAMBANOVA_API_KEY'),
        ),
    )
    rag_crew_results = web_search_crew.crew().kickoff(inputs={'query': 'How can AI be used in finance?'})
    print(rag_crew_results)
