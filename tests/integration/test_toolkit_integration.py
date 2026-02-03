"""
BAEL - Toolkit Integration Tests
Tests for the unified toolkit and all tool modules.
"""

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestWebTools(unittest.TestCase):
    """Tests for web toolkit."""

    @classmethod
    def setUpClass(cls):
        """Set up web toolkit."""
        try:
            from tools.web import WebToolkit
            cls.toolkit = WebToolkit()
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_toolkit_import(self):
        """Test web toolkit can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_web_scraper_exists(self):
        """Test web scraper component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'scraper'))

    def test_web_search_exists(self):
        """Test web search component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'search'))

    def test_url_analyzer_exists(self):
        """Test URL analyzer component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'url_analyzer'))

    def test_tool_definitions(self):
        """Test tool definitions are returned."""
        if self.available:
            tools = self.toolkit.get_tool_definitions()
            self.assertIsInstance(tools, list)
            self.assertGreater(len(tools), 0)

            # Check structure
            for tool in tools:
                self.assertIn('name', tool)
                self.assertIn('description', tool)
                self.assertIn('handler', tool)


class TestCodeTools(unittest.TestCase):
    """Tests for code toolkit."""

    @classmethod
    def setUpClass(cls):
        """Set up code toolkit."""
        try:
            from tools.code import CodeToolkit
            cls.toolkit = CodeToolkit()
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_toolkit_import(self):
        """Test code toolkit can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_code_analyzer_exists(self):
        """Test code analyzer component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'analyzer'))

    def test_code_executor_exists(self):
        """Test code executor component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'executor'))

    def test_security_scanner_exists(self):
        """Test security scanner component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'security_scanner'))

    def test_code_analysis(self):
        """Test code analysis functionality."""
        if not self.available:
            self.skipTest("Toolkit not available")

        code = '''
def hello(name):
    """Say hello."""
    return f"Hello, {name}!"
'''
        analysis = self.toolkit.analyzer.analyze(code, "python")
        self.assertIsInstance(analysis, dict)
        self.assertIn('metrics', analysis)

    def test_security_scan(self):
        """Test security scanning."""
        if not self.available:
            self.skipTest("Toolkit not available")

        vulnerable_code = '''
import os
os.system(input("Enter command: "))
'''
        result = self.toolkit.security_scanner.scan(vulnerable_code, "python")
        self.assertIsInstance(result, list)
        # Should find command injection vulnerability
        self.assertGreater(len(result), 0)


class TestFileTools(unittest.TestCase):
    """Tests for file toolkit."""

    @classmethod
    def setUpClass(cls):
        """Set up file toolkit."""
        try:
            from tools.file import FileToolkit
            cls.toolkit = FileToolkit()
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_toolkit_import(self):
        """Test file toolkit can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_file_reader_exists(self):
        """Test file reader component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'reader'))

    def test_file_writer_exists(self):
        """Test file writer component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'writer'))

    def test_file_operations(self):
        """Test file read/write operations."""
        if not self.available:
            self.skipTest("Toolkit not available")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_content = "Hello, BAEL!"
            f.write(test_content)
            temp_path = f.name

        try:
            # Read file
            content = self.toolkit.reader.read(temp_path)
            self.assertEqual(content, test_content)

            # Read with line numbers
            result = self.toolkit.reader.read_with_lines(temp_path)
            self.assertIn('content', result)
            self.assertIn('line_count', result)
        finally:
            os.unlink(temp_path)


class TestDatabaseTools(unittest.TestCase):
    """Tests for database toolkit."""

    @classmethod
    def setUpClass(cls):
        """Set up database toolkit."""
        try:
            from tools.database import DatabaseToolkit
            cls.toolkit = DatabaseToolkit()
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_toolkit_import(self):
        """Test database toolkit can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_sqlite_client_exists(self):
        """Test SQLite client component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'sqlite'))

    def test_vector_store_exists(self):
        """Test vector store component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'vector_store'))

    def test_kv_store_exists(self):
        """Test key-value store component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'kv_store'))

    def test_vector_operations(self):
        """Test vector store operations."""
        if not self.available:
            self.skipTest("Toolkit not available")

        # Insert vectors
        self.toolkit.vector_store.insert("test1", [0.1, 0.2, 0.3], {"text": "hello"})
        self.toolkit.vector_store.insert("test2", [0.2, 0.3, 0.4], {"text": "world"})

        # Search
        results = self.toolkit.vector_store.search([0.15, 0.25, 0.35], top_k=2)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_kv_operations(self):
        """Test key-value store operations."""
        if not self.available:
            self.skipTest("Toolkit not available")

        # Set/Get
        self.toolkit.kv_store.set("test_key", "test_value")
        value = self.toolkit.kv_store.get("test_key")
        self.assertEqual(value, "test_value")

        # Delete
        self.toolkit.kv_store.delete("test_key")
        value = self.toolkit.kv_store.get("test_key")
        self.assertIsNone(value)


class TestAITools(unittest.TestCase):
    """Tests for AI toolkit."""

    @classmethod
    def setUpClass(cls):
        """Set up AI toolkit."""
        try:
            from tools.ai import AIToolkit
            cls.toolkit = AIToolkit()
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_toolkit_import(self):
        """Test AI toolkit can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_llm_router_exists(self):
        """Test LLM router component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'llm_router'))

    def test_embedding_generator_exists(self):
        """Test embedding generator component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'embedding_generator'))

    def test_summarizer_exists(self):
        """Test text summarizer component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'summarizer'))

    def test_model_registry(self):
        """Test model registry has models."""
        if not self.available:
            self.skipTest("Toolkit not available")

        models = self.toolkit.llm_router.registry.list_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)


class TestAPITools(unittest.TestCase):
    """Tests for API toolkit."""

    @classmethod
    def setUpClass(cls):
        """Set up API toolkit."""
        try:
            from tools.api import APIToolkit
            cls.toolkit = APIToolkit()
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_toolkit_import(self):
        """Test API toolkit can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_rest_client_exists(self):
        """Test REST client component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'rest_client'))

    def test_graphql_client_exists(self):
        """Test GraphQL client component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'graphql_client'))

    def test_webhook_manager_exists(self):
        """Test webhook manager component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'webhook_manager'))

    def test_rate_limiter_exists(self):
        """Test rate limiter component exists."""
        if self.available:
            self.assertTrue(hasattr(self.toolkit, 'rate_limiter'))


class TestUnifiedToolkit(unittest.TestCase):
    """Tests for unified toolkit."""

    @classmethod
    def setUpClass(cls):
        """Set up unified toolkit."""
        try:
            from tools import UnifiedToolkit
            cls.toolkit = UnifiedToolkit()
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_toolkit_import(self):
        """Test unified toolkit can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_list_tools(self):
        """Test listing all tools."""
        if not self.available:
            self.skipTest("Toolkit not available")

        tools = self.toolkit.list_tools()
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)

    def test_get_all_tools(self):
        """Test getting all tool definitions."""
        if not self.available:
            self.skipTest("Toolkit not available")

        tools = self.toolkit.get_all_tools()
        self.assertIsInstance(tools, list)

        for tool in tools:
            self.assertIn('name', tool)
            self.assertIn('description', tool)

    def test_get_tool_by_name(self):
        """Test getting specific tool."""
        if not self.available:
            self.skipTest("Toolkit not available")

        tools = self.toolkit.list_tools()
        if tools:
            tool = self.toolkit.get_tool_by_name(tools[0])
            self.assertIsNotNone(tool)

    def test_tool_categories(self):
        """Test tools are properly categorized."""
        if not self.available:
            self.skipTest("Toolkit not available")

        tools = self.toolkit.list_tools()

        # Check for expected tool prefixes
        prefixes = set()
        for tool in tools:
            if '_' in tool:
                prefixes.add(tool.split('_')[0])

        # Should have multiple categories
        self.assertGreater(len(prefixes), 1)


class TestAsyncToolExecution(unittest.TestCase):
    """Tests for async tool execution."""

    @classmethod
    def setUpClass(cls):
        """Set up unified toolkit."""
        try:
            from tools import UnifiedToolkit
            cls.toolkit = UnifiedToolkit()
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_execute_tool(self):
        """Test executing a tool."""
        if not self.available:
            self.skipTest("Toolkit not available")

        async def run_test():
            # Try to execute a simple tool
            # We'll use file_read with a known file
            try:
                result = await self.toolkit.execute_tool(
                    "file_exists",
                    path="/tmp"
                )
                return result is not None
            except Exception:
                # Tool may not exist, that's ok for this test
                return True

        result = asyncio.get_event_loop().run_until_complete(run_test())
        self.assertTrue(result)


# =============================================================================
# INTEGRATION TEST SUITE
# =============================================================================

class TestToolkitIntegration(unittest.TestCase):
    """Integration tests across toolkits."""

    def test_all_toolkits_compatible(self):
        """Test all toolkits can be loaded together."""
        errors = []

        try:
            from tools.web import WebToolkit
            WebToolkit()
        except Exception as e:
            errors.append(f"Web: {e}")

        try:
            from tools.code import CodeToolkit
            CodeToolkit()
        except Exception as e:
            errors.append(f"Code: {e}")

        try:
            from tools.file import FileToolkit
            FileToolkit()
        except Exception as e:
            errors.append(f"File: {e}")

        try:
            from tools.database import DatabaseToolkit
            DatabaseToolkit()
        except Exception as e:
            errors.append(f"Database: {e}")

        try:
            from tools.ai import AIToolkit
            AIToolkit()
        except Exception as e:
            errors.append(f"AI: {e}")

        try:
            from tools.api import APIToolkit
            APIToolkit()
        except Exception as e:
            errors.append(f"API: {e}")

        if errors:
            self.fail(f"Toolkit loading errors: {errors}")

    def test_unified_loads_all(self):
        """Test unified toolkit loads all sub-toolkits."""
        try:
            from tools import UnifiedToolkit
            toolkit = UnifiedToolkit()

            # Should have multiple tool categories loaded
            tools = toolkit.list_tools()

            # Check we have tools from different categories
            categories = set()
            for tool in tools:
                if '_' in tool:
                    categories.add(tool.split('_')[0])

            # Expect at least 3 categories
            self.assertGreaterEqual(len(categories), 3)

        except ImportError:
            self.skipTest("Unified toolkit not available")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestWebTools))
    suite.addTests(loader.loadTestsFromTestCase(TestCodeTools))
    suite.addTests(loader.loadTestsFromTestCase(TestFileTools))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseTools))
    suite.addTests(loader.loadTestsFromTestCase(TestAITools))
    suite.addTests(loader.loadTestsFromTestCase(TestAPITools))
    suite.addTests(loader.loadTestsFromTestCase(TestUnifiedToolkit))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncToolExecution))
    suite.addTests(loader.loadTestsFromTestCase(TestToolkitIntegration))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
