"""Multi-language parser coordinator.

Routes files to appropriate parsers based on extension and configuration.
Supports both legacy parsers and new ast-grep adapters.
"""

import os
import logging
from typing import Dict, List, Tuple, Any, Optional

from src.ast_parser.parser import ASTParser, CodeNode, CodeRelation
from src.ast_parser.typescript_parser import TypeScriptParser
from src.ast_parser.adapters.python_adapter import PythonAstGrepAdapter
from src.ast_parser.adapters.javascript_adapter import JavaScriptAstGrepAdapter
from src.ast_parser.adapters.java_adapter import JavaAdapter
from src.ast_parser.adapters.cpp_adapter import CppAdapter
from src.ast_parser.adapters.rust_adapter import RustAdapter
from src.ast_parser.adapters.go_adapter import GoAdapter
from src.ast_parser.language_detector import detect_language

logger = logging.getLogger(__name__)


class MultiLanguageParser:
    """
    Coordinator that selects the appropriate parser for each file.
    
    When use_ast_grep=True:
        - Python files (.py) -> PythonAstGrepAdapter
        - JS/TS files (.js, .jsx, .ts, .tsx) -> JavaScriptAstGrepAdapter
    
    When use_ast_grep=False:
        - Python files (.py) -> ASTParser (legacy)
        - JS/TS files -> TypeScriptParser (legacy)
    
    Maintains compatibility with existing two-pass import resolution.
    """
    
    def __init__(self, use_ast_grep: bool = False, ast_grep_languages: Optional[List[str]] = None,
                 ast_grep_fallback: bool = True):
        """
        Initialize the multi-language parser coordinator.
        
        Args:
            use_ast_grep: If True, use ast-grep adapters when available
            ast_grep_languages: List of languages to enable for ast-grep (e.g., ['python', 'javascript'])
            ast_grep_fallback: If True, fall back to legacy parsers on error
        """
        self.use_ast_grep = use_ast_grep
        self.ast_grep_languages = set(ast_grep_languages or ['python', 'javascript', 'typescript'])
        self.ast_grep_fallback = ast_grep_fallback
        
        # Aggregated data structures for two-pass parsing
        self.nodes: Dict[str, CodeNode] = {}
        self.relations: List[CodeRelation] = []
        self.module_definitions: Dict[str, Dict[str, str]] = {}
        self.pending_imports: List[Dict[str, Any]] = []
        self.module_to_file: Dict[str, str] = {}
        self.established_relations: set = set()
        
        logger.info(f"MultiLanguageParser initialized: use_ast_grep={use_ast_grep}, "
                   f"languages={self.ast_grep_languages}, fallback={ast_grep_fallback}")
    
    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Parse a single file using the appropriate parser.
        
        Args:
            file_path: Absolute path to the source file
            build_index: If True, build module definition index for cross-file resolution
            
        Returns:
            Tuple of (nodes dict, relations list)
        """
        ext = os.path.splitext(file_path)[1].lower()
        language = detect_language(file_path)
        
        # Select parser based on extension and configuration
        parser = self._get_parser_for_file(file_path, language, ext)
        
        if parser is None:
            logger.warning(f"No parser available for file: {file_path}")
            return {}, []
        
        try:
            # Parse the file
            nodes, relations = parser.parse_file(file_path, build_index=build_index)
            
            # Aggregate indices for two-pass resolution
            if hasattr(parser, 'module_definitions'):
                self.module_definitions.update(parser.module_definitions)
            if hasattr(parser, 'pending_imports'):
                self.pending_imports.extend(parser.pending_imports)
            if hasattr(parser, 'module_to_file'):
                self.module_to_file.update(parser.module_to_file)
            if hasattr(parser, 'established_relations'):
                self.established_relations.update(parser.established_relations)
            
            # Aggregate nodes and relations
            self.nodes.update(nodes)
            self.relations.extend(relations)
            
            return nodes, relations
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            
            # Try fallback if enabled and we were using ast-grep
            if self.ast_grep_fallback and self.use_ast_grep and language in self.ast_grep_languages:
                logger.warning(f"Falling back to legacy parser for {file_path}")
                return self._parse_with_fallback(file_path, ext, build_index)
            
            # Otherwise, return empty results
            return {}, []
    
    def _get_parser_for_file(self, file_path: str, language: Optional[str], ext: str):
        """
        Select the appropriate parser based on file extension and configuration.
        
        Args:
            file_path: Path to the source file
            language: Detected language identifier
            ext: File extension (lowercase, with dot)
            
        Returns:
            Parser instance or None if unsupported
        """
        # Python files
        if ext == '.py':
            if self.use_ast_grep and 'python' in self.ast_grep_languages:
                # Use ast-grep Python adapter
                return PythonAstGrepAdapter()
            else:
                # Use legacy ASTParser
                return ASTParser()
        
        # JavaScript/TypeScript files
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            if self.use_ast_grep and (language in self.ast_grep_languages):
                # Use ast-grep JavaScript adapter
                use_tsx = (ext in ['.tsx', '.jsx'])
                return JavaScriptAstGrepAdapter(use_tsx=use_tsx)
            else:
                # Use legacy TypeScriptParser
                return TypeScriptParser()
        
        # Java files
        elif ext == '.java':
            if self.use_ast_grep and 'java' in self.ast_grep_languages:
                return JavaAdapter()
            else:
                logger.warning(f"Java parsing requires USE_AST_GREP=true and 'java' in AST_GREP_LANGUAGES")
                return None
        
        # C++ files
        elif ext in ['.cpp', '.cc', '.cxx', '.h', '.hpp']:
            if self.use_ast_grep and 'cpp' in self.ast_grep_languages:
                return CppAdapter()
            else:
                logger.warning(f"C++ parsing requires USE_AST_GREP=true and 'cpp' in AST_GREP_LANGUAGES")
                return None
        
        # Rust files
        elif ext == '.rs':
            if self.use_ast_grep and 'rust' in self.ast_grep_languages:
                return RustAdapter()
            else:
                logger.warning(f"Rust parsing requires USE_AST_GREP=true and 'rust' in AST_GREP_LANGUAGES")
                return None
        
        # Go files
        elif ext == '.go':
            if self.use_ast_grep and 'go' in self.ast_grep_languages:
                return GoAdapter()
            else:
                logger.warning(f"Go parsing requires USE_AST_GREP=true and 'go' in AST_GREP_LANGUAGES")
                return None
        
        # Unsupported extension
        else:
            logger.warning(f"Unsupported file extension: {ext} for file {file_path}")
            return None
    
    def _parse_with_fallback(self, file_path: str, ext: str, build_index: bool) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Fall back to legacy parser on error.
        
        Args:
            file_path: Path to the source file
            ext: File extension (lowercase, with dot)
            build_index: Whether to build index
            
        Returns:
            Tuple of (nodes dict, relations list)
        """
        try:
            if ext == '.py':
                parser = ASTParser()
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                parser = TypeScriptParser()
            else:
                return {}, []
            
            nodes, relations = parser.parse_file(file_path, build_index=build_index)
            
            # Aggregate indices
            if hasattr(parser, 'module_definitions'):
                self.module_definitions.update(parser.module_definitions)
            if hasattr(parser, 'pending_imports'):
                self.pending_imports.extend(parser.pending_imports)
            if hasattr(parser, 'module_to_file'):
                self.module_to_file.update(parser.module_to_file)
            
            return nodes, relations
            
        except Exception as e:
            logger.error(f"Fallback parser also failed for {file_path}: {e}")
            return {}, []
    
    def parse_directory(self, directory_path: str, build_index: bool = True) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Parse all supported source files in a directory.
        
        This is a convenience method for sequential parsing.
        For parallel parsing, use the pipeline in main.py.
        
        Args:
            directory_path: Path to the directory containing source files
            build_index: If True, build module definition index for cross-file resolution
            
        Returns:
            Tuple of (all nodes dict, all relations list)
        """
        # Collect all source files
        source_files = []
        
        # Determine which extensions to collect based on enabled languages
        if self.use_ast_grep:
            # Only collect files for languages we have adapters for
            supported_extensions = []
            if 'python' in self.ast_grep_languages:
                supported_extensions.append('.py')
            if 'javascript' in self.ast_grep_languages or 'typescript' in self.ast_grep_languages:
                supported_extensions.extend(['.js', '.ts', '.jsx', '.tsx'])
            if 'java' in self.ast_grep_languages:
                supported_extensions.append('.java')
            if 'cpp' in self.ast_grep_languages:
                supported_extensions.extend(['.cpp', '.cc', '.cxx', '.h', '.hpp'])
            if 'rust' in self.ast_grep_languages:
                supported_extensions.append('.rs')
            if 'go' in self.ast_grep_languages:
                supported_extensions.append('.go')
            supported_extensions = tuple(supported_extensions)
        else:
            # Legacy mode: respect ENABLE_JS_TS_PARSING flag
            enable_js_ts = os.getenv("ENABLE_JS_TS_PARSING", "true").lower() == "true"
            python_extensions = (".py",)
            js_ts_extensions = (".js", ".ts", ".jsx", ".tsx") if enable_js_ts else ()
            supported_extensions = python_extensions + js_ts_extensions
        
        # Collect files
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                if file_name.endswith(supported_extensions):
                    file_path = os.path.join(root, file_name)
                    source_files.append(file_path)
        
        logger.info(f"Found {len(source_files)} source files to parse")
        
        # Parse all files (first pass)
        for file_path in source_files:
            self.parse_file(file_path, build_index=build_index)
        
        # Second pass: process pending imports
        if build_index:
            self._process_pending_imports()
        
        return self.nodes, self.relations
    
    def _process_pending_imports(self):
        """
        Process pending imports to create cross-file dependency relations.
        
        This is the second pass of two-pass parsing.
        Uses the same logic as ASTParser._process_pending_imports().
        """
        # Reuse ASTParser's import resolution logic
        # Create a temporary parser with our aggregated data
        temp_parser = ASTParser()
        temp_parser.nodes = self.nodes
        temp_parser.relations = self.relations  # CRITICAL: Initialize with existing relations!
        temp_parser.module_definitions = self.module_definitions
        temp_parser.pending_imports = self.pending_imports
        temp_parser.module_to_file = self.module_to_file
        temp_parser.established_relations = self.established_relations
        
        # Process imports (adds import relations to temp_parser.relations)
        temp_parser._process_pending_imports()
        
        # Update our relations with the combined relations
        self.relations = temp_parser.relations
        self.established_relations = temp_parser.established_relations
