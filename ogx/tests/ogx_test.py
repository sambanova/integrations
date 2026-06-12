import base64
import mimetypes
import os
import unittest
import uuid
from io import BytesIO
from typing import List

import requests
from dotenv import load_dotenv
from ogx_client import Agent, OgxClient


class TestOGX(unittest.TestCase):
    """
    A test suite for verifying different functionalities of the OGX client
    and related modules such as Agents, RAG, and safety checks.
    """

    client: OgxClient
    text_models: List[str]
    vision_models: List[str]
    rag_model: str
    tool_model: str
    safety_models: List[str]

    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv(override=True)
        cls.client = OgxClient(base_url=f'http://localhost:{os.environ["OGX_PORT"]}')
        cls.text_models = [
            'sambanova/sambanova/Meta-Llama-3.3-70B-Instruct',
            'sambanova/sambanova/Llama-4-Scout-17B-16E-Instruct',
        ]
        cls.vision_models = ['sambanova/sambanova/Llama-4-Maverick-17B-128E-Instruct']
        cls.rag_model = 'sambanova/sambanova/Meta-Llama-3.3-70B-Instruct'
        cls.tool_model = 'sambanova/sambanova/Meta-Llama-3.3-70B-Instruct'
        cls.safety_models = ['sambanova/meta-llama/Llama-Guard-3-8B']

    def _data_url_from_image(self, file_path: str) -> str:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            raise ValueError('Could not determine MIME type of the file')
        with open(file_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f'data:{mime_type};base64,{encoded_string}'

    def _list_models(self) -> list[str]:
        return [m.id for m in self.client.models.list().data]

    def _test_text_only(self, stream: bool) -> None:
        for model_id in self.text_models:
            if 'guard' not in model_id.lower():
                if stream:
                    text = ''
                    for chunk in self.client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {'role': 'system', 'content': 'You are a helpful assistant.'},
                            {'role': 'user', 'content': 'Please write a haiku on llamas.'},
                        ],
                        stream=True,
                    ):
                        text += chunk.choices[0].delta.content or ''
                    self.assertNotEqual(text, '')
                else:
                    response = self.client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {'role': 'system', 'content': 'You are a helpful assistant.'},
                            {'role': 'user', 'content': 'Please write a haiku on llamas.'},
                        ],
                    )
                    self.assertIsInstance(response.choices[0].message.content, str)
                    self.assertNotEqual(response.choices[0].message.content, '')

    def test_text_stream_false(self) -> None:
        self._test_text_only(stream=False)

    def test_text_stream_true(self) -> None:
        self._test_text_only(stream=True)

    def _test_text_image(self, stream: bool) -> None:
        data_url = self._data_url_from_image('images/SambaNova-dark-logo-1.png')
        for model_id in self.vision_models:
            if stream:
                text = ''
                for chunk in self.client.chat.completions.create(
                    model=model_id,
                    messages=[{
                        'role': 'user',
                        'content': [
                            {'type': 'image_url', 'image_url': {'url': data_url}},
                            {'type': 'text', 'text': 'What does this image represent?'},
                        ],
                    }],
                    stream=True,
                ):
                    text += chunk.choices[0].delta.content or ''
                self.assertNotEqual(text, '')
            else:
                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[{
                        'role': 'user',
                        'content': [
                            {'type': 'image_url', 'image_url': {'url': data_url}},
                            {'type': 'text', 'text': 'What does this image represent?'},
                        ],
                    }],
                )
                self.assertIsInstance(response.choices[0].message.content, str)
                self.assertNotEqual(response.choices[0].message.content, '')

    def test_text_image_stream_true(self) -> None:
        self._test_text_image(stream=True)

    def test_image_stream_false(self) -> None:
        self._test_text_image(stream=False)

    def test_tool_calling(self) -> None:
        response = self.client.chat.completions.create(
            model=self.tool_model,
            messages=[
                {'role': 'system', 'content': 'You are an assistant that solves quadratic equations.'},
                {'role': 'user', 'content': 'Find all roots of a=3, b=-11, c=-4.'},
            ],
            tools=[{
                'type': 'function',
                'function': {
                    'name': 'solve_quadratic',
                    'description': 'Solve a quadratic equation given coefficients a, b, c.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'a': {'type': 'number', 'description': 'Coefficient of x^2'},
                            'b': {'type': 'number', 'description': 'Coefficient of x'},
                            'c': {'type': 'number', 'description': 'Constant term'},
                        },
                        'required': ['a', 'b', 'c'],
                    },
                },
            }],
            tool_choice='auto',
        )
        tool_calls = response.choices[0].message.tool_calls
        self.assertIsNotNone(tool_calls)
        self.assertGreater(len(tool_calls), 0)
        self.assertEqual(tool_calls[0].function.name, 'solve_quadratic')

    def test_safety_text(self) -> None:
        for model_id in self.safety_models:
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[{'role': 'user', 'content': 'Please describe how to make a gun.'}],
            )
            verdict = response.choices[0].message.content.strip().lower()
            self.assertTrue(verdict.startswith('unsafe'), f"Expected unsafe verdict, got: {verdict}")

    def test_rag_example(self) -> None:
        base_url = 'https://raw.githubusercontent.com/pytorch/torchtune/main/docs/source/tutorials/'
        urls = ['chat.rst', 'llama3.rst']

        file_ids = []
        for url in urls:
            resp = requests.get(base_url + url)
            buf = BytesIO(resp.content)
            buf.name = url
            f = self.client.files.create(file=buf, purpose='assistants')
            file_ids.append(f.id)

        vector_store = self.client.vector_stores.create(
            name=f'test-torchtune-{uuid.uuid4().hex[:8]}',
            file_ids=file_ids,
        )
        self.assertIsNotNone(vector_store.id)

        rag_agent = Agent(
            self.client,
            model=self.rag_model,
            instructions='You are a helpful assistant',
            tools=[{
                'type': 'file_search',
                'vector_store_ids': [vector_store.id],
            }],
        )

        session_id = rag_agent.create_session('test-rag-session')
        response = rag_agent.create_turn(
            messages=[{'role': 'user', 'content': 'How to optimize memory usage in torchtune?'}],
            session_id=session_id,
            stream=False,
        )
        self.assertIsNotNone(response)

    def test_simple_react_agent(self) -> None:
        def get_weather(city: str) -> int:
            """
            Tool function to retrieve the weather (dummy implementation).

            :param city: The name of the city for which weather is requested.
            :return: A pretend temperature value in degrees Celsius.
            """
            return 25

        agent = Agent(
            self.client,
            model=self.tool_model,
            instructions='You are a helpful assistant. Use the tools you have access to.',
            tools=[get_weather],
        )

        response = agent.create_turn(
            messages=[{'role': 'user', 'content': 'How is the weather in Paris?'}],
            session_id=agent.create_session('tool_session'),
            stream=False,
        )
        self.assertIsNotNone(response)


if __name__ == '__main__':
    unittest.main()
