"""Language detection utilities for multi-language parsing.

Maps file extensions to ast-grep language identifiers.
"""

import os
from typing import Optional


# Extension to ast-grep language mapping
# Map file extensions to ast-grep language identifiers
EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".rs": "rust",
    ".go": "go",
}


def detect_language(file_path: str) -> Optional[str]:
    """
    Detect the programming language from a file extension.
    
    Args:
        file_path: Path to the source file
        
    Returns:
        Language identifier (e.g., 'python', 'javascript') or None if unsupported
    """
    ext = os.path.splitext(file_path)[1].lower()
    return EXT_TO_LANG.get(ext)


def is_supported_extension(file_path: str) -> bool:
    """
    Check if a file extension is supported for parsing.
    
    Args:
        file_path: Path to the source file
        
    Returns:
        True if the file extension is supported, False otherwise
    """
    return detect_language(file_path) is not None
