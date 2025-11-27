# MCP Server Security Recommendations

## Overview

This document provides comprehensive security recommendations to enhance the sandboxed tool compiler in the MCP server. The current implementation provides good baseline security, but several critical improvements can significantly strengthen the isolation and prevent potential exploits.

## Current Security Assessment

### Strengths
- ✅ Basic pattern-based dangerous code detection
- ✅ Limited allowed imports whitelist
- ✅ Execution timeout protection
- ✅ Tenant-based isolation
- ✅ API key authentication
- ✅ Controlled inter-tool communication

### Critical Vulnerabilities
- ❌ **`__import__` exposed in safe globals** - Major security risk
- ❌ Regex-based validation can be bypassed
- ❌ No resource limit enforcement
- ❌ No bytecode-level validation
- ❌ No subprocess isolation

## Priority 1: Critical Security Fixes

### 1.1 Remove `__import__` Access (IMMEDIATE ACTION REQUIRED)

**Current Code (UNSAFE):**
```python
safe_globals = {
    '__builtins__': {
        # ... other functions
        '__import__': __import__  # ❌ DANGEROUS - Allows arbitrary imports
    }
}
```

**Secure Implementation:**
```python
def create_safe_import(self):
    """Create controlled import function"""
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Only allow explicitly whitelisted modules
        if name not in self.allowed_imports:
            raise SecurityError(f"Import not allowed: {name}")
        
        # Block relative imports
        if level > 0:
            raise SecurityError("Relative imports not allowed")
            
        # Log import attempts for monitoring
        logger.info(f"Safe import: {name}")
        return __import__(name, globals, locals, fromlist, level)
    
    return safe_import

# In _compile_code method:
safe_globals = {
    '__builtins__': {
        'print': print, 'len': len, 'str': str, 'int': int, 'float': float,
        'bool': bool, 'dict': dict, 'list': list, 'tuple': tuple,
        'range': range, 'enumerate': enumerate, 'zip': zip,
        'min': min, 'max': max, 'sum': sum, 'any': any, 'all': all,
        'ValueError': ValueError, 'TypeError': TypeError, 'KeyError': KeyError,
        'Exception': Exception,
        '__import__': self.create_safe_import()  # ✅ SECURE - Controlled import
    },
    # Pre-import allowed modules
    'json': json,
    'datetime': datetime,
    'asyncio': asyncio,
    're': re
}
```

### 1.2 AST-Based Code Validation

Replace regex pattern matching with proper Abstract Syntax Tree analysis:

```python
import ast
from typing import Set, List

class SecurityVisitor(ast.NodeVisitor):
    """AST visitor for security validation"""
    
    def __init__(self):
        self.violations = []
        self.imports = set()
        self.function_calls = set()
        
    def visit_Import(self, node):
        """Check import statements"""
        for alias in node.names:
            module_name = alias.name.split('.')[0]
            self.imports.add(module_name)
            
    def visit_ImportFrom(self, node):
        """Check from X import Y statements"""
        if node.module:
            module_name = node.module.split('.')[0]
            self.imports.add(module_name)
    
    def visit_Call(self, node):
        """Check function calls for dangerous operations"""
        # Direct function calls
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            self.function_calls.add(func_name)
            
            # Block dangerous built-in functions
            dangerous_functions = {
                'exec', 'eval', 'compile', 'open', 'input', 
                'globals', 'locals', 'vars', 'dir',
                'getattr', 'setattr', 'hasattr', 'delattr'
            }
            
            if func_name in dangerous_functions:
                self.violations.append(f"Dangerous function call: {func_name} at line {node.lineno}")
        
        # Method calls on modules
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                method_name = node.func.attr
                
                # Block dangerous module methods
                dangerous_modules = {'os', 'sys', 'subprocess', 'socket', 'urllib'}
                if module_name in dangerous_modules:
                    self.violations.append(
                        f"Dangerous module method: {module_name}.{method_name} at line {node.lineno}"
                    )
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Check attribute access for dangerous attributes"""
        dangerous_attrs = {
            '__globals__', '__code__', '__dict__', '__class__', '__bases__',
            '__subclasses__', '__import__', '__builtins__'
        }
        
        if isinstance(node.attr, str) and node.attr in dangerous_attrs:
            self.violations.append(f"Dangerous attribute access: {node.attr} at line {node.lineno}")
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Validate function definitions"""
        # Only allow 'execute' function and private helper functions
        if node.name != 'execute' and not node.name.startswith('_'):
            self.violations.append(f"Unauthorized function definition: {node.name} at line {node.lineno}")
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Block class definitions"""
        self.violations.append(f"Class definition not allowed: {node.name} at line {node.lineno}")
    
    def visit_AsyncFunctionDef(self, node):
        """Handle async function definitions"""
        self.visit_FunctionDef(node)

def validate_code_with_ast(self, code: str, tool_id: str) -> None:
    """Enhanced AST-based code validation"""
    try:
        # Parse the code into AST
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SecurityError(f"Syntax error in {tool_id}: {e}")
    
    # Run security visitor
    visitor = SecurityVisitor()
    visitor.visit(tree)
    
    # Check for violations
    if visitor.violations:
        raise SecurityError(f"Security violations in {tool_id}: {'; '.join(visitor.violations)}")
    
    # Validate imports against whitelist
    unauthorized_imports = visitor.imports - self.allowed_imports
    if unauthorized_imports:
        raise SecurityError(f"Unauthorized imports in {tool_id}: {unauthorized_imports}")
    
    # Ensure execute function exists
    if 'execute' not in [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        raise SecurityError(f"Tool {tool_id} must define an 'execute' function")
```

## Priority 2: Enhanced Security Measures

### 2.1 Bytecode Inspection

Add bytecode-level security validation:

```python
import dis
from types import CodeType

def validate_bytecode(self, code_obj: CodeType, tool_id: str) -> None:
    """Inspect compiled bytecode for dangerous operations"""
    dangerous_opcodes = {
        'IMPORT_NAME', 'IMPORT_FROM', 'IMPORT_STAR',
        'LOAD_BUILD_CLASS', 'LOAD_LOCALS', 'LOAD_GLOBAL',
        'STORE_GLOBAL', 'DELETE_GLOBAL'
    }
    
    def check_code_object(code_obj: CodeType, depth: int = 0):
        """Recursively check code object and nested functions"""
        if depth > 10:  # Prevent infinite recursion
            raise SecurityError(f"Code nesting too deep in {tool_id}")
        
        for instruction in dis.get_instructions(code_obj):
            if instruction.opname in dangerous_opcodes:
                # Allow specific safe global loads
                if instruction.opname == 'LOAD_GLOBAL' and instruction.argval in self.allowed_globals:
                    continue
                    
                raise SecurityError(
                    f"Dangerous bytecode instruction in {tool_id}: {instruction.opname} "
                    f"with argument {instruction.argval}"
                )
            
            # Check nested code objects (functions, lambdas)
            if isinstance(instruction.argval, CodeType):
                check_code_object(instruction.argval, depth + 1)
    
    check_code_object(code_obj)

# Add to compile_tool method after AST validation
def _compile_code(self, code: str, tool_id: str) -> Callable:
    """Enhanced secure compilation with bytecode validation"""
    try:
        # Compile code
        compiled_code = compile(code, f"<tool_{tool_id}>", 'exec')
        
        # Validate bytecode before execution
        self.validate_bytecode(compiled_code, tool_id)
        
        # Create safe execution environment
        safe_globals = self._create_safe_globals()
        local_vars = {}
        
        # Execute in controlled environment
        exec(compiled_code, safe_globals, local_vars)
        
        # Extract and validate execute function
        if 'execute' not in local_vars:
            raise ValueError(f"Tool {tool_id} does not define execute function")
        
        return local_vars['execute']
        
    except Exception as e:
        logger.error(f"Compilation failed for {tool_id}: {e}")
        raise
```

### 2.2 Resource Monitoring and Limits

Implement comprehensive resource limiting:

```python
import resource
import psutil
import threading
import time
from contextlib import contextmanager

class ResourceMonitor:
    """Monitor and limit resource usage during tool execution"""
    
    def __init__(self, max_memory_mb: int = 50, max_cpu_time: int = 10, max_execution_time: int = 30):
        self.max_memory = max_memory_mb * 1024 * 1024  # Convert to bytes
        self.max_cpu_time = max_cpu_time
        self.max_execution_time = max_execution_time
        self.original_limits = {}
        
    def _store_original_limits(self):
        """Store original resource limits for restoration"""
        try:
            self.original_limits = {
                'memory': resource.getrlimit(resource.RLIMIT_AS),
                'cpu': resource.getrlimit(resource.RLIMIT_CPU),
            }
        except (OSError, resource.error):
            # Some systems don't support all limits
            pass
    
    def _restore_original_limits(self):
        """Restore original resource limits"""
        try:
            if 'memory' in self.original_limits:
                resource.setrlimit(resource.RLIMIT_AS, self.original_limits['memory'])
            if 'cpu' in self.original_limits:
                resource.setrlimit(resource.RLIMIT_CPU, self.original_limits['cpu'])
        except (OSError, resource.error):
            pass
    
    @contextmanager
    def monitor_execution(self, tool_id: str):
        """Context manager for monitoring tool execution"""
        self._store_original_limits()
        
        try:
            # Set memory limit
            try:
                resource.setrlimit(resource.RLIMIT_AS, (self.max_memory, self.max_memory))
            except (OSError, resource.error):
                logger.warning(f"Could not set memory limit for {tool_id}")
            
            # Set CPU time limit
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (self.max_cpu_time, self.max_cpu_time))
            except (OSError, resource.error):
                logger.warning(f"Could not set CPU limit for {tool_id}")
            
            # Monitor memory usage in separate thread
            memory_monitor = MemoryMonitor(self.max_memory, tool_id)
            memory_monitor.start()
            
            try:
                yield
            finally:
                memory_monitor.stop()
                
        finally:
            self._restore_original_limits()

class MemoryMonitor(threading.Thread):
    """Background thread to monitor memory usage"""
    
    def __init__(self, max_memory: int, tool_id: str):
        super().__init__(daemon=True)
        self.max_memory = max_memory
        self.tool_id = tool_id
        self.running = True
        
    def run(self):
        """Monitor memory usage"""
        process = psutil.Process()
        while self.running:
            try:
                memory_info = process.memory_info()
                if memory_info.rss > self.max_memory:
                    logger.error(f"Memory limit exceeded for {self.tool_id}: {memory_info.rss} bytes")
                    # Could terminate the process here if needed
                time.sleep(0.1)  # Check every 100ms
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    
    def stop(self):
        """Stop monitoring"""
        self.running = False

# Enhanced execute_tool method with resource monitoring
async def execute_tool(self, tool_id: str, params: Dict[str, Any], 
                      tenant_id: str = None, context: ToolContext = None) -> Any:
    """Execute a compiled tool with resource monitoring"""
    if tool_id not in self.compiled_cache:
        raise ValueError(f"Tool {tool_id} not compiled")
    
    compiled_tool = self.compiled_cache[tool_id]
    
    if context is None:
        context = ToolContext(self, tenant_id)
    
    # Initialize resource monitor
    resource_monitor = ResourceMonitor(
        max_memory_mb=50,
        max_cpu_time=10,
        max_execution_time=30
    )
    
    try:
        with resource_monitor.monitor_execution(tool_id):
            enhanced_params = {**params, 'context': context}
            
            if asyncio.iscoroutinefunction(compiled_tool.func):
                result = await asyncio.wait_for(
                    compiled_tool.func(**enhanced_params), 
                    timeout=resource_monitor.max_execution_time
                )
            else:
                # Run sync function in thread pool to maintain timeout
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: compiled_tool.func(**enhanced_params)
                )
            
            return result
            
    except asyncio.TimeoutError:
        logger.error(f"Tool {tool_id} execution timed out")
        raise
    except MemoryError:
        logger.error(f"Tool {tool_id} exceeded memory limit")
        raise
    except Exception as e:
        logger.error(f"Tool {tool_id} execution failed: {e}")
        raise
```

### 2.3 Subprocess Isolation (Maximum Security)

For highest security, execute tools in completely isolated subprocesses:

```python
import subprocess
import json
import tempfile
import os
import shutil
from pathlib import Path

class SubprocessExecutor:
    """Execute tools in isolated Python subprocesses"""
    
    def __init__(self, temp_dir: str = None):
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "mcp_sandbox"
        self.temp_dir.mkdir(exist_ok=True, mode=0o700)  # Secure permissions
        
    async def execute_isolated(self, tool_code: str, params: Dict[str, Any], 
                              tool_id: str, timeout: int = 30) -> Any:
        """Execute tool in completely isolated subprocess"""
        
        # Create secure temporary directory for this execution
        execution_dir = self.temp_dir / f"exec_{tool_id}_{int(time.time())}"
        execution_dir.mkdir(mode=0o700)
        
        try:
            # Create the tool execution script
            tool_script = execution_dir / "tool.py"
            wrapper_code = f'''
import json
import sys
import signal
import os

# Sandbox restrictions
def setup_sandbox():
    """Set up execution sandbox"""
    # Remove dangerous modules from sys.modules if they exist
    dangerous_modules = [
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'urllib2', 
        'httplib', 'ftplib', 'smtplib', 'telnetlib'
    ]
    
    for module in dangerous_modules:
        if module in sys.modules:
            del sys.modules[module]
    
    # Limit file descriptors
    import resource
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (10, 10))
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024*1024, 1024*1024))  # 1MB file size limit
    except (OSError, resource.error):
        pass

# Set up timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Tool execution timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({timeout})

# Set up sandbox
setup_sandbox()

# Tool code
{tool_code}

# Execute the tool
try:
    if len(sys.argv) > 1:
        params = json.loads(sys.argv[1])
    else:
        params = {{}}
    
    result = execute(**params)
    print(json.dumps({{"status": "success", "result": result}}), flush=True)
    
except Exception as e:
    print(json.dumps({{"status": "error", "error": str(e), "type": type(e).__name__}}), flush=True)
    sys.exit(1)
'''
            
            # Write the script with secure permissions
            tool_script.write_text(wrapper_code)
            tool_script.chmod(0o600)
            
            # Prepare secure environment
            secure_env = {
                'PATH': '/usr/bin:/bin',  # Minimal PATH
                'PYTHONPATH': '',         # No additional Python paths
                'PYTHONDONTWRITEBYTECODE': '1',  # Don't create .pyc files
                'PYTHONHASHSEED': 'random',      # Random hash seed for security
            }
            
            # Execute in subprocess with strict security
            cmd = [
                'python3', '-S', '-s', '-B',  # -S: no site.py, -s: no user site, -B: no .pyc
                str(tool_script),
                json.dumps(params)
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=secure_env,
                cwd=str(execution_dir),
                limit=1024 * 1024  # 1MB output limit
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(), timeout=timeout + 5  # Extra buffer
                )
            except asyncio.TimeoutError:
                result.kill()
                await result.wait()
                raise TimeoutError(f"Tool {tool_id} execution timed out")
            
            if result.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise RuntimeError(f"Tool {tool_id} execution failed: {error_msg}")
            
            # Parse result
            try:
                output = json.loads(stdout.decode('utf-8'))
                if output['status'] == 'error':
                    raise RuntimeError(f"Tool error: {output['error']}")
                return output['result']
            except json.JSONDecodeError:
                raise RuntimeError(f"Invalid tool output: {stdout.decode('utf-8', errors='ignore')}")
                
        finally:
            # Clean up temporary files securely
            try:
                shutil.rmtree(execution_dir)
            except OSError:
                logger.warning(f"Could not clean up temporary directory: {execution_dir}")
    
    def cleanup(self):
        """Clean up temporary directory"""
        try:
            shutil.rmtree(self.temp_dir)
        except OSError:
            logger.warning(f"Could not clean up sandbox directory: {self.temp_dir}")
```

## Priority 3: Advanced Security Features

### 3.1 Enhanced Pattern Detection

Comprehensive dangerous pattern detection:

```python
def _create_enhanced_dangerous_patterns(self) -> List[str]:
    """Create comprehensive list of dangerous patterns"""
    return [
        # File system operations
        r'\bopen\s*\(', r'\bfile\s*\(', r'\.read\s*\(', r'\.write\s*\(',
        r'\.readlines\s*\(', r'\.writelines\s*\(', r'pathlib\.Path',
        
        # System operations  
        r'import\s+os\b', r'import\s+sys\b', r'import\s+subprocess\b',
        r'os\.', r'sys\.', r'subprocess\.', r'platform\.',
        
        # Dynamic execution
        r'exec\s*\(', r'eval\s*\(', r'compile\s*\(', r'__import__\s*\(',
        
        # Network operations
        r'import\s+socket\b', r'import\s+urllib\b', r'import\s+requests\b',
        r'import\s+http\b', r'import\s+ftplib\b', r'import\s+smtplib\b',
        r'socket\.', r'urllib\.', r'requests\.', r'http\.',
        
        # Introspection and reflection
        r'globals\s*\(', r'locals\s*\(', r'vars\s*\(', r'dir\s*\(',
        r'getattr\s*\(', r'setattr\s*\(', r'hasattr\s*\(', r'delattr\s*\(',
        r'callable\s*\(', r'isinstance\s*\(', r'issubclass\s*\(',
        
        # Magic methods and attributes (more comprehensive)
        r'__\w+__', r'\.__\w+__', r'\.\_\_\w+\_\_\s*\(',
        r'__globals__', r'__builtins__', r'__code__', r'__dict__',
        r'__class__', r'__bases__', r'__subclasses__', r'__import__',
        
        # Threading and multiprocessing
        r'import\s+threading\b', r'import\s+multiprocessing\b',
        r'import\s+concurrent\b', r'threading\.', r'multiprocessing\.',
        
        # Memory and garbage collection
        r'import\s+gc\b', r'import\s+ctypes\b', r'import\s+mmap\b',
        r'gc\.', r'ctypes\.', r'mmap\.',
        
        # Database and persistence
        r'import\s+sqlite3\b', r'import\s+pickle\b', r'import\s+shelve\b',
        r'import\s+dbm\b', r'pickle\.', r'sqlite3\.',
        
        # Process control
        r'import\s+signal\b', r'signal\.', r'alarm\s*\(', r'kill\s*\(',
        
        # Code manipulation
        r'import\s+ast\b', r'import\s+dis\b', r'import\s+types\b',
        r'ast\.', r'dis\.', r'types\.',
        
        # Shell commands
        r'import\s+commands\b', r'commands\.', r'popen\s*\(',
        
        # Cryptography (if not explicitly allowed)
        r'import\s+hashlib\b.*sha\d+', r'import\s+hmac\b',
        
        # Time manipulation that could be used for timing attacks
        r'time\.sleep\s*\(\s*[^0-1]', r'time\.time\s*\(',
    ]
```

### 3.2 Code Signing and Integrity Verification

```python
import hmac
import secrets
import hashlib
from datetime import datetime

class CodeSigner:
    """Handle code signing and verification for trusted tools"""
    
    def __init__(self, secret_key: bytes = None):
        self.secret_key = secret_key or secrets.token_bytes(32)
        
    def sign_tool(self, tool_doc: Dict[str, Any]) -> str:
        """Create cryptographic signature for tool"""
        # Create canonical representation
        canonical_data = {
            'tool_id': tool_doc['tool_id'],
            'code': tool_doc['code'],
            'input_schema': tool_doc['input_schema'],
            'version': tool_doc.get('version', '1.0')
        }
        
        message = json.dumps(canonical_data, sort_keys=True).encode()
        signature = hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()
        
        return signature
    
    def verify_tool(self, tool_doc: Dict[str, Any], signature: str) -> bool:
        """Verify tool hasn't been tampered with"""
        expected_signature = self.sign_tool(tool_doc)
        return hmac.compare_digest(expected_signature, signature)
    
    def sign_execution_result(self, tool_id: str, params: Dict[str, Any], 
                            result: Any, timestamp: datetime) -> str:
        """Sign execution results for audit trail"""
        execution_data = {
            'tool_id': tool_id,
            'params': params,
            'result': str(result)[:1000],  # Truncate large results
            'timestamp': timestamp.isoformat()
        }
        
        message = json.dumps(execution_data, sort_keys=True).encode()
        return hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()
```

### 3.3 Comprehensive Audit Logging

```python
import logging
from datetime import datetime
from typing import Optional
import json

class SecurityAuditor:
    """Comprehensive security event logging and monitoring"""
    
    def __init__(self):
        # Create separate logger for security events
        self.security_logger = logging.getLogger('mcp_security')
        self.security_logger.setLevel(logging.INFO)
        
        # Add file handler for security logs
        security_handler = logging.FileHandler('mcp_security.log')
        security_formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        self.security_logger.addHandler(security_handler)
    
    def log_compilation_attempt(self, tool_id: str, tenant_id: str, 
                               code_hash: str, success: bool, 
                               violation: Optional[str] = None):
        """Log tool compilation attempts"""
        event = {
            'event_type': 'tool_compilation',
            'tool_id': tool_id,
            'tenant_id': tenant_id,
            'code_hash': code_hash,
            'success': success,
            'violation': violation,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        level = logging.INFO if success else logging.WARNING
        self.security_logger.log(level, json.dumps(event))
    
    def log_execution_attempt(self, tool_id: str, tenant_id: str,
                             params: Dict[str, Any], success: bool,
                             execution_time: float, error: Optional[str] = None):
        """Log tool execution attempts"""
        # Sanitize parameters to prevent log injection
        sanitized_params = self._sanitize_params(params)
        
        event = {
            'event_type': 'tool_execution',
            'tool_id': tool_id,
            'tenant_id': tenant_id,
            'params': sanitized_params,
            'success': success,
            'execution_time': execution_time,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        level = logging.INFO if success else logging.ERROR
        self.security_logger.log(level, json.dumps(event))
    
    def log_security_violation(self, violation_type: str, tool_id: str,
                             tenant_id: str, details: Dict[str, Any]):
        """Log security violations"""
        event = {
            'event_type': 'security_violation',
            'violation_type': violation_type,
            'tool_id': tool_id,
            'tenant_id': tenant_id,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.security_logger.error(json.dumps(event))
    
    def log_authentication_event(self, tenant_id: str, success: bool,
                                ip_address: str, user_agent: str):
        """Log authentication attempts"""
        event = {
            'event_type': 'authentication',
            'tenant_id': tenant_id,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        level = logging.INFO if success else logging.WARNING
        self.security_logger.log(level, json.dumps(event))
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters to prevent log injection"""
        sanitized = {}
        for key, value in params.items():
            if isinstance(value, str):
                # Truncate long strings and remove control characters
                sanitized_value = ''.join(char for char in str(value)[:200] 
                                        if char.isprintable())
                sanitized[key] = sanitized_value
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            else:
                sanitized[key] = str(type(value).__name__)
        
        return sanitized
```

## Implementation Plan

### Phase 1: Critical Fixes (Immediate - Within 1 week)
1. **Remove `__import__` from safe globals** - CRITICAL
2. **Implement controlled import system**
3. **Add basic AST validation**
4. **Enhanced dangerous pattern detection**

### Phase 2: Enhanced Security (1-2 weeks)
1. **Complete AST-based validation system**
2. **Add bytecode inspection**
3. **Implement resource monitoring**
4. **Add comprehensive audit logging**

### Phase 3: Maximum Security (2-4 weeks)
1. **Implement subprocess isolation**
2. **Add code signing system**
3. **Performance optimization**
4. **Security testing and validation**

## Testing and Validation

### Security Test Cases

Create comprehensive test cases to validate security:

```python
# tests/test_security.py
import pytest
from core.tool_compiler import ToolCompiler, SecurityError

class TestSecurityValidation:
    """Test security validation mechanisms"""
    
    def setup_method(self):
        self.compiler = ToolCompiler()
    
    def test_import_blocking(self):
        """Test that dangerous imports are blocked"""
        dangerous_codes = [
            "import os\ndef execute(): return os.system('ls')",
            "import sys\ndef execute(): return sys.exit()",
            "import subprocess\ndef execute(): return subprocess.call(['ls'])",
            "from os import system\ndef execute(): return system('ls')"
        ]
        
        for code in dangerous_codes:
            with pytest.raises(SecurityError):
                self.compiler._validate_code_safety(code, "test_tool")
    
    def test_function_call_blocking(self):
        """Test that dangerous function calls are blocked"""
        dangerous_codes = [
            "def execute(): return exec('print(1)')",
            "def execute(): return eval('1+1')",
            "def execute(): return open('/etc/passwd')",
            "def execute(): return __import__('os')"
        ]
        
        for code in dangerous_codes:
            with pytest.raises(SecurityError):
                self.compiler._validate_code_safety(code, "test_tool")
    
    def test_safe_code_passes(self):
        """Test that safe code passes validation"""
        safe_code = """
import json
import datetime

def execute(name: str = "World"):
    return f"Hello, {name}! Time: {datetime.datetime.now()}"
"""
        
        # Should not raise exception
        self.compiler._validate_code_safety(safe_code, "test_tool")
```

## Monitoring and Alerting

### Security Metrics Dashboard

Monitor key security metrics:

- Tool compilation success/failure rates
- Security violation frequency by tenant
- Resource usage patterns
- Execution timeouts
- Authentication failures

### Alert Conditions

Set up alerts for:

- Multiple security violations from same tenant
- Unusual resource usage patterns  
- Repeated authentication failures
- Tool execution timeouts exceeding threshold
- Suspected code injection attempts

## Conclusion

These recommendations provide a comprehensive security enhancement strategy for the MCP server tool compiler. The priority-based implementation plan ensures that critical vulnerabilities are addressed first while building towards a robust, production-ready sandboxed execution environment.

Regular security reviews and updates to the validation patterns will be necessary as new attack vectors are discovered. The audit logging system will provide valuable insights for detecting and responding to security incidents.