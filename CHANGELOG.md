# Changelog

## [2025-05-01] - Documentation and Visualization Updates

### [DOCS]
- Added knowledge graph visualization example to README.md
- Updated documentation to reflect cross-file dependency analysis functionality
- Extended MCP query examples with cross-file analysis cases
- Improved project structure documentation

## [2025-05-01] - Fixed Relationship Duplication Issues

### [FIX]
- Resolved duplicate IMPORTS_FROM relationship creation issues
- Implemented relationship uniqueness verification mechanism
- Optimized module import processing logic with source file grouping
- Added intelligent symbol import grouping tracking

## [2025-05-01] - Fixed File Node Duplication Issues

### [FIX]
- Fixed duplicate creation of module and file nodes
- Implemented direct association between module names and file nodes
- Optimized import dependency tracking mechanism
- Improved cross-file symbol reference handling

## [2025-05-01] - Enhanced Cross-File Dependency Relationships

### [FEAT]
- Implemented inter-module import relationship tracking and creation
- Enhanced AST parser to support cross-file symbol dependency analysis
- Added support for tracking relationships between imported symbols across files
- Implemented cross-file function call and class inheritance relationship tracking

## [2025-04-30] - Initial Version

### [FEAT]
- Implemented AST parser with Python code structure analysis support
- Integrated OpenAI Embeddings for code semantic encoding
- Established Neo4j graph database model for code knowledge graph
- Developed MCP Server interface for code querying and analysis

### [DOCS]
- Created detailed README.md with project overview, installation guide, and usage instructions
- Established TODO.md to track development progress and future plans

### [BUILD]
- Created basic project structure and directory organization
- Set up virtual environment and dependency management
- Configured Neo4j and OpenAI API integration
