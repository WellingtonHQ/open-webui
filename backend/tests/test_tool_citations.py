import ast
import json
import logging
from pathlib import Path
import re
import unittest


class JSONCodecStub:
    JSONDecodeError = json.JSONDecodeError
    loads = staticmethod(json.loads)
    dumps = staticmethod(json.dumps)


class ToolCitationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).parents[1] / 'open_webui/utils/middleware.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        function_names = {
            '_collect_url_entries',
            '_build_url_citation_sources',
            '_parse_markdown_url_citations',
            'get_citation_source_from_tool_result',
        }
        functions = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in function_names
        ]
        namespace = {'JSONCodec': JSONCodecStub, 'log': logging.getLogger(__name__), 're': re}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), namespace)
        cls.get_citation_source = staticmethod(namespace['get_citation_source_from_tool_result'])

    def test_builtin_search_web_json_results_become_url_citations(self):
        url = 'https://example.com/filter-guide'
        result = json.dumps([{'title': 'Filter guide', 'link': url, 'snippet': 'Replacement schedule.'}])

        sources = self.get_citation_source('search_web', {}, result, tool_type='builtin')

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]['metadata'][0]['source'], url)
        self.assertEqual(sources[0]['metadata'][0]['name'], 'Filter guide')
        self.assertIn('Replacement schedule.', sources[0]['document'][0])

    def test_builtin_search_web_without_urls_produces_no_citations(self):
        result = json.dumps([{'title': 'No link result', 'snippet': 'No URL was provided.'}])

        self.assertEqual(self.get_citation_source('search_web', {}, result, tool_type='builtin'), [])

    def test_fetch_page_markdown_becomes_a_url_citation(self):
        url = 'https://example.com/filter-guide'
        result = f'Title: Filter guide\nURL: {url}\nSnippet: Replacement schedule.'

        sources = self.get_citation_source('fetch_page', {}, result, tool_type='')

        self.assertEqual(sources[0]['metadata'][0]['source'], url)
        self.assertEqual(sources[0]['metadata'][0]['name'], 'Filter guide')

    def test_openapi_external_tool_type_parses_url_blocks(self):
        url = 'https://example.com/filter-guide'
        result = f'Title: Filter guide\nURL: {url}'

        sources = self.get_citation_source('read_page', {}, result, tool_type='external')

        self.assertEqual(sources[0]['metadata'][0]['source'], url)
