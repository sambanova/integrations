import base64
import os
import time
from typing import Any
import sys
import streamlit
from crewai import LLM
from dotenv import load_dotenv
from pathlib import Path

# Main directories
sys.path.append(str(Path(__file__).parent.parent))

from crews.crew_rag.crew_rag import RAGCrew  # type: ignore
from utils.utilities import clean_markdown_content, convert_html_to_pdf, st_capture  # type: ignore

# Load environment variables
load_dotenv()

# Define cache directory
CACHE_DIR = 'results/app_rag'
# Create cache directory
os.makedirs(CACHE_DIR, exist_ok=True)
# Output file for the report
output_file = CACHE_DIR + f'/report.md'


def main() -> None:
    """Main entry point for the Streamlit application."""
    init_session_state()

    # Page config
    streamlit.set_page_config(
        page_title='Financial Assistant - PDF RAG',
        page_icon='💸',
        layout='wide',
        initial_sidebar_state='collapsed',
    )

    # Custom CSS with improved styling
    streamlit.markdown(
        """
        <style>
        /* Base layout padding */
        .main > div { padding-top: 1rem; }
        .block-container { padding-top: 1rem; }

        /* Logo container styling */
        .logo-container {
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0.5rem 0;
        }
        .logo-container img {
            height: 2rem; /* Adjust the height to control the size of the logo */
            margin-right: 0.5rem;
        }
        .logo-container h2 {
            color: #ee7624;
            margin: 0;
            text-align: center;
        }

        /* Bold all text input / select labels, remove extra margin */
        .stTextInput label, .stSelectbox label {
            font-weight: bold !important;
            margin-bottom: 0.35rem !important;
        }

        /* Button styling */
        .stButton > button {
            width: 100%;
            margin-top: 1.5rem;  /* roughly aligns with input fields if they are short */
        }

        /* We use .custom-panel to unify both agent and content panels at same height */
        .custom-panel {
            height: 600px;
            overflow-y: auto !important;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* The placeholder with same .custom-panel height */
        .custom-placeholder {
            display: flex;
            height: 100%;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: #ee7624;
        }

        /* Code block styling for real-time logs */
        pre {
            height: auto;
            max-height: 530px !important;  /* just a bit less than 600 so the scrollbar is fully visible */
            overflow-y: auto !important;
            white-space: pre-wrap !important;
            background-color: #f8f9fa;
            margin: 0;
            padding: 10px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            line-height: 1.4;
            border-radius: 4px;
        }
        /* Scrollbar styling in the code block */
        pre::-webkit-scrollbar {
            width: 8px;
        }
        pre::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        pre::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        pre::-webkit-scrollbar-thumb:hover {
            background: #ee7624;
        }

        /* Markdown styling in final content */
        .markdown-content {
            height: 100%;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.6;
        }
        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
            color: #ee7624;
            margin: 1rem 0;
            font-weight: bold;
        }

        /* Adjust container heights for smaller screens */
        @media (max-width: 1200px) {
            .custom-panel {
                height: 400px !important;
            }
            pre {
                max-height: 330px !important;
            }
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Logos + Title
    streamlit.markdown(
        """
        <div class="logo-container">
            <img src="https://sambanova.ai/hubfs/logotype_sambanova_orange.png" 
                alt="SambaNova Logo">
            <h2>Financial Assistant - PDF RAG</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------- FORM --------------------
    with streamlit.form('generation_form'):
        streamlit.write('**User query**')
        query = streamlit.text_input(
            label='Enter research topic (hidden)',
            placeholder='E.g., What are the conclusions of this article?',
            help='Enter the main subject for content generation',
            key='compact_topic',
            label_visibility='collapsed',
        )

        col21, col22 = streamlit.columns([0.5, 0.5], vertical_alignment='center')

        with col21:
            uploaded_file = streamlit.file_uploader('Choose a PDF file', type='pdf')
            if uploaded_file is not None:
                # Define the path to save the PDF file
                filename = os.path.join(CACHE_DIR, uploaded_file.name)

                # Save the uploaded file locally
                with open(filename, 'wb') as f:
                    f.write(uploaded_file.getbuffer())

        with col22:
            # Create a select box in the sidebar with several options
            with streamlit.expander('LLM'):
                model_name = streamlit.selectbox(
                    'Select an option:',
                    [
                        'Meta-Llama-3.1-8B-Instruct',
                        'Meta-Llama-3.3-70B-Instruct',
                        'Meta-Llama-3.1-405B-Instruct',
                    ],
                )

        # Generate button
        generate_button = streamlit.form_submit_button(
            label='🚀 Generate',
            type='secondary',
            disabled=streamlit.session_state.running,
            help='Click to start generating content',
        )

    # -------------------- ACTIONS ON SUBMIT --------------------
    if generate_button:
        if not query:
            streamlit.error('❌ Please enter a query.')
            return

        try:
            start_time = time.time()
            streamlit.session_state.running = True
            streamlit.session_state.final_content = None

            if streamlit.session_state.running:
                streamlit.markdown(
                    "<h4 style='margin: 0 0 0.5rem;'>🔄 Agent Progress</h4>",
                    unsafe_allow_html=True,
                )
                # We keep an empty container that we'll fill with logs or a placeholder
                execution_output = streamlit.empty()

                # Show real-time logs
                with streamlit.spinner('Our research agents are working on your query...'):
                    with st_capture(execution_output.info):
                        try:
                            model_name = 'sambanova/' + model_name
                        except NameError:
                            model_name = 'sambanova/Meta-Llama-3.3-70B-Instruct'
                        # Create an LLM with a temperature of 0 to ensure deterministic outputs
                        llm = LLM(
                            model=model_name,
                            temperature=0,
                            base_url=os.getenv('SAMBANOVA_URL'),
                            api_key=os.getenv('SAMBANOVA_API_KEY'),
                        )

                        rag_crew = RAGCrew(llm=llm, filename=filename, output_file=output_file)
                        results = rag_crew.crew().kickoff(inputs={'query': query})

            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            time_msg = f'⚡ Generated in {minutes}m {seconds}s' if minutes > 0 else f'⚡ Generated in {seconds}s'

            streamlit.session_state.running = False
            streamlit.session_state.final_content = output_file
            streamlit.success('✨ Content generated successfully!')
            streamlit.markdown(f'{time_msg} using our medical research assistant.')

            # If the output file was written, show it
            if os.path.exists(output_file):
                output_col1, output_col2 = streamlit.columns([0.5, 0.5], gap='large')
                with output_col1:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        report_md = f.read()
                        streamlit.session_state.final_content = report_md
                        # Clean the Markdown (base64 images, table classes) -> HTML
                        cleaned_html = clean_markdown_content(report_md)
                        content_output = streamlit.empty()
                        content_output.markdown(
                            f"""
                            <div class="custom-panel">
                                <div class="markdown-content">
                                    {cleaned_html}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Download the Markdown report
                    download_section(
                        label='📥 Download Markdown',
                        data=report_md,
                        file_name=f'report.md',
                        mime='text/markdown',
                    )

                with output_col2:
                    # Convert the cleaned HTML to a PDF
                    pdf_data = convert_html_to_pdf(cleaned_html)

                    # Encode the PDF to Base64
                    base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
                    pdf_display = (
                        f'<embed src="data:application/pdf;base64,{base64_pdf}"'
                        ' width="700" height="400" type="application/pdf">'
                    )
                    streamlit.markdown(pdf_display, unsafe_allow_html=True)

                    # Download the PDF report
                    download_section(
                        label='📥 Download PDF',
                        data=pdf_data,
                        file_name='report.pdf',
                        mime='application/pdf',
                    )

        except Exception as e:
            streamlit.error(f'❌ An error occurred: {str(e)}')
            streamlit.info('🔄 Please try again or contact support if the issue persists.')
        finally:
            streamlit.session_state.running = False


def init_session_state() -> None:
    """Initialize Streamlit session state variables."""
    if 'running' not in streamlit.session_state:
        streamlit.session_state.running = False
    if 'final_content' not in streamlit.session_state:
        streamlit.session_state.final_content = None


@streamlit.fragment
def download_section(
    label: str = '📥 Download',
    data: Any = '',
    file_name: str = 'file.txt',
    mime: str = 'text/plain',
) -> None:
    """This function prevents streamlit from refreshing the page when the download button is clicked."""

    if streamlit.download_button(
        label=label,
        data=data,
        file_name=file_name,
        mime=mime,
    ):
        pass


if __name__ == '__main__':
    main()
