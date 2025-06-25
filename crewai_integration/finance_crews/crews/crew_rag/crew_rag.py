import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from crewai import LLM, Agent, Crew, Process, Task, TaskOutput
from crewai.knowledge.knowledge_config import KnowledgeConfig
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

import weave

load_dotenv()


# Initialize Weave with your project name
weave.init(project_name='finance_rag')

# Store knowledge in project directory
project_root = Path(__file__).parent.parent.parent
os.environ['CREWAI_STORAGE_DIR'] = str(project_root)

load_dotenv()


@CrewBase
class RAGCrew:
    """RAGCrew crew."""

    agents_config: Dict[str, Any]
    tasks_config: Dict[str, Any]
    agents: List[Any]
    tasks: List[Any]

    def __init__(
        self,
        llm: LLM,
        filename: str | Path,
        output_file: str = '/results/app_rag/report.md',
        verbose: bool = True,
    ) -> None:
        """Initialize the RAGCrew crew."""

        super().__init__()
        self.agents_config = dict()
        self.tasks_config = dict()
        self.agents = list()
        self.tasks = list()
        self.llm = llm
        self.filename = filename
        self.output_file = output_file
        self.verbose = verbose
        self.embedder = dict(
            provider='openai',
            config=dict(
                api_key=os.getenv('SAMBANOVA_API_KEY'),
                api_base=os.getenv('SAMBANOVA_URL', 'https://api.sambanova.ai/v1'),
                model='E5-Mistral-7B-Instruct',
            ),
        )

    @agent  # type: ignore
    def rag_researcher(self) -> Agent:
        """Add the RAG Agent."""

        # Create a PDF knowledge source
        self.pdf_source = PDFKnowledgeSource(file_paths=[Path(self.filename)], collection_name='pdf_knowledge')

        # Create a PDF knowledge config
        self.knowledge_config = KnowledgeConfig(results_limit=10, score_threshold=0.5)

        return Agent(
            config=self.agents_config['rag_researcher'],
            verbose=self.verbose,
            llm=self.llm,
            allow_delegation=False,
            knowledge_sources=[self.pdf_source],
            knowledge_config=self.knowledge_config,
            embedder=self.embedder,
        )

    @task  # type: ignore
    def rag_research_task(self) -> Task:
        """Add the RAG Research Task."""

        return Task(
            config=self.tasks_config['rag_research_task'],
        )

    @agent  # type: ignore
    def analyst(self) -> Task:
        """Add the Analyst."""
        return Agent(
            config=self.agents_config['analyst'],
            verbose=self.verbose,
            llm=self.llm,
            allow_delegation=False,
        )

    @task  # type: ignore
    def analysis(self) -> Task:
        """Add the Analysis."""

        # Decorate your guardrail function with `@weave.op()`
        @weave.op(name='guardrail-validate_report')
        def validate_report(result: TaskOutput) -> Tuple[bool, Any]:
            # Get raw string result
            result = result.raw

            """Validate blog content meets requirements."""
            try:
                # Check word count
                word_count = len(result.split())

                if word_count > 1000:
                    return (
                        False,
                        {
                            'error': 'Answer exceeds 1000 words',
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
            config=self.tasks_config['analysis'],
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
    rag_crew = RAGCrew(
        llm=LLM(
            model='sambanova/Meta-Llama-3.3-70B-Instruct',
            temperature=0,
            base_url=os.getenv('SAMBANOVA_URL'),
            api_key=os.getenv('SAMBANOVA_API_KEY'),
        ),
        filename=project_root / 'sources' / 'article.pdf',
    )
    rag_crew_results = rag_crew.crew().kickoff(inputs={'query': 'What are the conclusion of this article?'})
    print(rag_crew_results)
