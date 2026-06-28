# mcp Specification

## Purpose
TBD - created by archiving change add-semantic-relationships-and-grouping. Update Purpose after archive.
## Requirements
### Requirement: Semantic Code Relationships
The MCP server SHALL include relationship data in search results showing code element connections.

#### Scenario: Relationships included by default
- **WHEN** user calls `search_code("database connection")`
- **THEN** each result SHALL include a `relationships` object with arrays: `calls`, `called_by`, `extends`, `extended_by`, `imports`, `imported_by`
- **AND** each array SHALL contain max 5 items (3 for inheritance)
- **AND** each relationship item SHALL include: `id`, `name`, `type`, `file_path`

#### Scenario: Relationships can be disabled
- **WHEN** user calls `search_code("query", include_relationships=False)`
- **THEN** results SHALL NOT include `relationships` object
- **AND** response time SHALL be faster than with relationships enabled

#### Scenario: Missing relationships handled gracefully
- **WHEN** a node has no relationships of a specific type
- **THEN** that relationship array SHALL be empty `[]`
- **AND** the search SHALL NOT fail

### Requirement: Smart Result Grouping
The MCP server SHALL group search results by semantic similarity when requested.

#### Scenario: Grouping with explicit threshold
- **WHEN** user calls `search_code("error handling", group_threshold=0.8, limit=20)`
- **THEN** response SHALL contain `groups` and `ungrouped` arrays instead of `results`
- **AND** items within each group SHALL have cosine similarity >= 0.8
- **AND** each group SHALL have fields: `id`, `representative`, `items`, `similarity_score`

#### Scenario: Grouping disabled by default
- **WHEN** user calls `search_code("query")` without `group_threshold`
- **THEN** response SHALL contain `results` array (not grouped)
- **AND** behavior SHALL match pre-enhancement version

#### Scenario: Invalid threshold handling
- **WHEN** user provides `group_threshold=2.5` (invalid)
- **THEN** system SHALL clamp to 1.0 and log warning
- **AND** when user provides `group_threshold=-0.3`, system SHALL clamp to 0.0

### Requirement: Environment Configuration
The system SHALL support environment-based grouping configuration.

#### Scenario: GROUP_THRESHOLD environment variable
- **WHEN** `GROUP_THRESHOLD=0.75` is set in environment
- **THEN** `search_code(query, group_threshold=None)` SHALL use 0.75 as default
- **AND** explicit parameter SHALL override environment value

#### Scenario: GROUP_MAX_GROUPS limit
- **WHEN** `GROUP_MAX_GROUPS=5` and system identifies 8 potential groups
- **THEN** only top 5 groups SHALL be created
- **AND** remaining items SHALL be in `ungrouped` array

#### Scenario: Missing environment variables
- **WHEN** environment variables are not set
- **THEN** system SHALL use hardcoded defaults: `GROUP_THRESHOLD=0.7`, `GROUP_MAX_GROUPS=10`

### Requirement: Backward Compatibility
Enhanced search SHALL maintain compatibility with existing clients.

#### Scenario: Default behavior unchanged
- **WHEN** existing client calls `search_code("query", limit=10)`
- **THEN** response format SHALL be `{"results": [...]}`
- **AND** each result SHALL contain same fields as before (id, name, type, file_path, score, node)
- **AND** new `relationships` object SHALL be added without breaking existing fields

#### Scenario: Grouped response is distinguishable
- **WHEN** grouping is active
- **THEN** response SHALL contain `groups` key instead of `results` key
- **AND** clients checking for `results` key SHALL detect grouped response

