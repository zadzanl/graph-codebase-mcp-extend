## Why
The current single-threaded indexing process is a major bottleneck, especially for large codebases. This leads to long wait times and a poor user experience. A parallel processing model is required to significantly reduce indexing time and improve performance.

## What Changes
- Re-architect the file processing pipeline to use a `concurrent.futures` executor.
- Use a `ThreadPoolExecutor` on free-threaded Python 3.14+ and fall back to a `ProcessPoolExecutor` on older versions.
- Implement a thread-safe pattern for database operations by ensuring each worker thread uses its own Neo4j `Session`.
- Make the number of workers and the Neo4j connection pool size configurable.

## Impact
- **Affected specs**: `main`
- **Affected code**: `src/main.py`, `src/neo4j_storage/graph_db.py`

---

## Technical Assessment: Python 3.14 Free-Threading

### Overview of Python 3.14 Free-Threading
Python 3.14 (released October 7, 2025) officially supports free-threaded builds via **PEP 779**, marking the transition from experimental (3.13) to supported status. This enables true parallel execution by removing the Global Interpreter Lock (GIL), allowing threads to run simultaneously on multiple CPU cores.

**Key Facts:**
- **Release Status**: Python 3.14 released October 7, 2025 (confirmed - only ~1 week old)
- **Free-threading Status**: Officially supported (no longer experimental as of 3.14)
- **Performance Characteristics**:
  - Single-threaded overhead: **5-10%** slower than GIL-enabled build (improved from 40% in 3.13)
  - Multi-threaded CPU-bound: Can achieve near-linear scaling with CPU cores
  - I/O-bound workloads: Less impacted by overhead
- **Specializing Adaptive Interpreter**: Re-enabled in 3.14 (was disabled in 3.13), significantly improving performance

### Runtime Detection Strategy

The implementation must reliably detect whether free-threaded Python is available and the GIL is disabled:

```python
import sys
import sysconfig

def is_free_threading_available() -> bool:
    """Check if Python build supports free-threading."""
    # Check build-time configuration
    py_gil_disabled = sysconfig.get_config_var("Py_GIL_DISABLED")
    return py_gil_disabled == 1

def is_gil_enabled() -> bool:
    """Check if GIL is currently enabled at runtime."""
    # sys._is_gil_enabled() added in Python 3.13
    if hasattr(sys, '_is_gil_enabled'):
        return sys._is_gil_enabled()
    return True  # Always enabled in Python < 3.13

def should_use_threads() -> bool:
    """Determine if ThreadPoolExecutor should be used."""
    return is_free_threading_available() and not is_gil_enabled()
```

**Important**: The GIL can be re-enabled at runtime via:
- Environment variable: `PYTHON_GIL=1`
- Command-line option: `-X gil=1`
- Automatic re-enabling when importing non-compatible C extensions

### Dependency Compatibility Analysis

#### ✅ Neo4j Python Driver (v5.14.0+)
**Status**: **COMPATIBLE - Thread-safe with proper session management**

**Key Findings**:
- **Driver object**: Thread-safe, immutable, expensive to create
- **Session objects**: **NOT thread-safe** - must not be shared between threads
- **Recommended Pattern**: 
  - Single shared `Driver` instance across all threads
  - Each thread creates its own `Session` from the driver
  - Connection pool size must be ≥ number of workers
- **Python 3.13+ Support**: Officially supported since driver version 5.26.0
- **No known free-threading issues**: Pure Python with no problematic C extensions

**Implementation Pattern**:
```python
# Single driver instance (thread-safe, shared)
driver = GraphDatabase.driver(uri, auth=(user, password), 
                               max_connection_pool_size=max_workers)

# In each worker thread (NOT shared)
def worker_function(file_path):
    with driver.session() as session:
        # Process file and write to database
        session.execute_write(tx_function, data)
```

#### ✅ OpenAI SDK (v1.0.0+)
**Status**: **COMPATIBLE - HTTP client is thread-safe**

**Key Findings**:
- Uses `httpx` library internally, which is thread-safe
- Client instances can be shared across threads
- No known issues with free-threaded Python
- Mostly I/O-bound operations (network requests)

#### ✅ NumPy (v1.24.0+, recommended v2.1.0+)
**Status**: **COMPATIBLE with caveats**

**Key Findings**:
- **NumPy 2.1.0+**: Experimental free-threading support (August 2024)
- **NumPy 2.3.0**: Improved free-threading support (June 2025)
- Core operations are thread-safe
- Global state issues mostly resolved in 2.x series
- Recommendation: Upgrade to NumPy ≥2.1.0 for optimal free-threading support

**Current requirement**: `numpy>=1.24.0` - **Should be updated to `numpy>=2.1.0`**

#### ⚠️ Other Dependencies
- **tiktoken**: Pure Python + Rust extensions (likely compatible, needs testing)
- **python-dotenv**: Pure Python (compatible)
- **mcp**: Need to verify (likely pure Python)

### ThreadPoolExecutor vs ProcessPoolExecutor

#### ThreadPoolExecutor (Free-threaded Python)
**Advantages**:
- ✅ True parallelism without GIL limitations
- ✅ Lightweight thread creation
- ✅ Shared memory - no pickling overhead
- ✅ Easy state sharing (shared Driver instance)
- ✅ Lower memory footprint
- ✅ Better for I/O-bound + CPU-mixed workloads

**Disadvantages**:
- ⚠️ 5-10% single-threaded overhead
- ⚠️ Requires Python 3.14t (free-threaded build)
- ⚠️ Not all dependencies may be compatible

#### ProcessPoolExecutor (GIL-enabled Python)
**Advantages**:
- ✅ Works on all Python versions
- ✅ True parallelism (separate processes)
- ✅ Process isolation (crash isolation)

**Disadvantages**:
- ❌ High memory overhead (each process loads full Python interpreter)
- ❌ Pickling overhead for data transfer
- ❌ Cannot share Driver instances (need separate connections)
- ❌ Slower startup time
- ❌ More complex state management

### Performance Expectations

**Baseline (Single-threaded)**:
- Current implementation time: T

**With ThreadPoolExecutor (Free-threaded Python 3.14)**:
- Expected speedup: **3-6x** for CPU-bound portions (depending on core count)
- I/O operations (database writes, API calls): Remains I/O-bound
- Overall: Estimated **2-4x** improvement for typical codebases

**With ProcessPoolExecutor (GIL-enabled Python)**:
- Expected speedup: **2-4x** (higher overhead reduces gains)
- Memory usage: **N × baseline** (where N = number of workers)

### Risk Assessment

#### High-Priority Risks

**1. Technology Maturity Risk** ⚠️⚠️⚠️
- **Issue**: Python 3.14 free-threading released only 1 week ago (October 7, 2025)
- **Impact**: Unknown edge cases, immature tooling, limited production experience
- **Mitigation**:
  - Extensive testing in staging environments
  - Gradual rollout with feature flags
  - Maintain ProcessPoolExecutor fallback
  - Monitor error rates and performance metrics

**2. Dependency Compatibility Risk** ⚠️⚠️
- **Issue**: Not all dependencies fully tested with free-threading
- **Impact**: Potential runtime errors or performance degradation
- **Mitigation**:
  - Upgrade NumPy to ≥2.1.0
  - Test all dependencies in free-threaded environment
  - Implement automatic GIL re-enabling detection
  - Warn users if GIL is re-enabled by incompatible extensions

**3. Single-Threaded Performance Penalty** ⚠️
- **Issue**: 5-10% slower for single-threaded workloads on free-threaded build
- **Impact**: Small codebases may experience degraded performance
- **Mitigation**:
  - Provide configuration to set worker count = 1 for small codebases
  - Document performance characteristics
  - Consider adaptive worker count based on codebase size

**4. Database Connection Pool Exhaustion** ⚠️
- **Issue**: Concurrent threads may exhaust connection pool
- **Impact**: Failed transactions, degraded performance
- **Mitigation**:
  - Set connection pool size ≥ worker count
  - Implement proper connection pool monitoring
  - Add retry logic with exponential backoff

#### Medium-Priority Risks

**5. Memory Usage (Immortalization)** ⚠️
- **Issue**: 3.13 free-threaded builds immortalize certain objects (improved in 3.14)
- **Impact**: Increased memory usage for large codebases
- **Mitigation**:
  - Monitor memory usage in production
  - Profile memory allocation patterns
  - Document memory requirements

**6. Iterator Sharing Issues** ⚠️
- **Issue**: Sharing iterators between threads is unsafe
- **Impact**: Duplicate/missing elements or interpreter crashes
- **Mitigation**:
  - Ensure each thread has its own iterators
  - Code review for shared state
  - Comprehensive testing

### Recommended Implementation Strategy

#### Phase 1: Preparation (Week 1-2)
1. Upgrade dependencies:
   - `numpy>=2.1.0`
   - Verify other dependency compatibility
2. Set up Python 3.14t testing environment
3. Create runtime detection utilities
4. Implement configuration system (worker count, connection pool size)

#### Phase 2: Core Implementation (Week 3-4)
1. Implement `ProcessingPoolManager` with dual-mode support
2. Refactor file processing loop to use executor
3. Ensure thread-safe Neo4j session management
4. Add comprehensive logging and monitoring

#### Phase 3: Testing & Validation (Week 5-6)
1. Unit tests for both execution modes
2. Integration tests with various codebase sizes
3. Performance benchmarking
4. Load testing for connection pool behavior
5. Memory profiling

#### Phase 4: Gradual Rollout (Week 7+)
1. Deploy with feature flag (disabled by default)
2. Enable for select users/projects
3. Monitor metrics (performance, errors, memory)
4. Iterate based on feedback
5. Enable by default after confidence threshold

### Success Metrics

**Performance**:
- ✅ 2x+ speedup for large codebases (>1000 files) on free-threaded Python
- ✅ 1.5x+ speedup on GIL-enabled Python with ProcessPoolExecutor
- ✅ No regression for small codebases (<100 files)

**Reliability**:
- ✅ <1% error rate increase
- ✅ No database connection failures
- ✅ No memory leaks

**Compatibility**:
- ✅ Works on Python 3.10-3.14 (all builds)
- ✅ Automatic fallback to ProcessPoolExecutor on GIL-enabled builds
- ✅ Graceful handling of incompatible dependencies

### Open Questions

1. **Should we require Python 3.14 or maintain backward compatibility?**
   - **Recommendation**: Maintain compatibility with Python 3.10+ (current requirement), but optimize for 3.14t

2. **What should be the default worker count?**
   - **Recommendation**: `min(os.cpu_count(), 8)` with configuration override

3. **Should we auto-detect codebase size and adjust strategy?**
   - **Recommendation**: Yes - use single-threaded for <50 files to avoid overhead

4. **How to handle GIL re-enablement during runtime?**
   - **Recommendation**: Log warning, continue with ThreadPoolExecutor (GIL provides safety)
