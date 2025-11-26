"""
Tool Compiler - Safe compilation with caching and context injection
"""
import json
import asyncio
import hashlib
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class ToolContext:
    """Context injected into tools for inter-tool communication"""
    
    def __init__(self, compiler, tenant_id: str = None):
        self.compiler = compiler
        self.tenant_id = tenant_id
        self.call_stack = []
    
    async def call_tool(self, tool_id: str, params: Dict[str, Any]) -> Any:
        """Allow tools to call other tools"""
        # Prevent circular dependencies
        if tool_id in self.call_stack:
            raise ValueError(f"Circular dependency detected: {' -> '.join(self.call_stack)} -> {tool_id}")
        
        self.call_stack.append(tool_id)
        try:
            result = await self.compiler.execute_tool(tool_id, params, self.tenant_id, self)
            return result
        finally:
            self.call_stack.pop()

class CompiledTool:
    """Represents a compiled tool"""
    
    def __init__(self, tool_id: str, name: str, func: Callable, input_schema: Dict[str, Any], code_hash: str):
        self.tool_id = tool_id
        self.name = name
        self.func = func
        self.input_schema = input_schema
        self.code_hash = code_hash
        self.compiled_at = datetime.utcnow()

class ToolCompiler:
    """Safe tool compiler with caching and context injection"""
    
    def __init__(self):
        self.compiled_cache = {}  # tool_id -> CompiledTool
        self.allowed_imports = {
            'json', 'datetime', 're', 'math', 'uuid', 'hashlib', 'asyncio'
        }
        self.dangerous_patterns = [
            r'import\s+os\b', r'import\s+sys\b', r'__import__', r'exec\s*\(',
            r'eval\s*\(', r'\bopen\s*\(', r'\bfile\s*\(', r'subprocess'
        ]
    
    async def compile_tool(self, tool_doc: Dict[str, Any]) -> CompiledTool:
        """Compile a tool from database document"""
        tool_id = tool_doc['tool_id']
        code = tool_doc['code']
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        # Check cache
        if tool_id in self.compiled_cache:
            cached_tool = self.compiled_cache[tool_id]
            if cached_tool.code_hash == code_hash:
                logger.debug(f"Using cached compilation for {tool_id}")
                return cached_tool
        
        # Validate code safety
        self._validate_code_safety(code, tool_id)
        
        # Compile the code
        compiled_func = self._compile_code(code, tool_id)
        
        # Create compiled tool
        compiled_tool = CompiledTool(
            tool_id=tool_id,
            name=tool_doc['name'],
            func=compiled_func,
            input_schema=tool_doc['input_schema'],
            code_hash=code_hash
        )
        
        # Cache it
        self.compiled_cache[tool_id] = compiled_tool
        logger.info(f"Compiled tool: {tool_id}")
        
        return compiled_tool
    
    def _validate_code_safety(self, code: str, tool_id: str):
        """Basic security validation"""
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise SecurityError(f"Dangerous code pattern detected in {tool_id}: {pattern}")
        
        # Check imports are allowed
        import_matches = re.findall(r'import\s+(\w+)', code)
        for module in import_matches:
            if module not in self.allowed_imports:
                raise SecurityError(f"Disallowed import in {tool_id}: {module}")
        
        # Must have execute function
        if 'def execute(' not in code:
            raise ValueError(f"Tool {tool_id} must define an 'execute' function")
    
    def _compile_code(self, code: str, tool_id: str) -> Callable:
        """Compile code in safe environment"""
        try:
            # Create safe globals
            safe_globals = {
                '__builtins__': {
                    'print': print, 'len': len, 'str': str, 'int': int, 'float': float,
                    'bool': bool, 'dict': dict, 'list': list, 'tuple': tuple,
                    'range': range, 'enumerate': enumerate, 'zip': zip,
                    'min': min, 'max': max, 'sum': sum, 'any': any, 'all': all,
                    'ValueError': ValueError, 'TypeError': TypeError, 'KeyError': KeyError,
                    'Exception': Exception,  # Base exception class
                    '__import__': __import__  # Allow imports
                },
                'json': json,
                'datetime': datetime,
                'asyncio': asyncio,
                're': re
            }
            
            # Compile and execute
            compiled_code = compile(code, f"<tool_{tool_id}>", 'exec')
            local_vars = {}
            exec(compiled_code, safe_globals, local_vars)
            
            # Extract execute function
            if 'execute' not in local_vars:
                raise ValueError(f"Tool {tool_id} does not define execute function")
            
            return local_vars['execute']
            
        except Exception as e:
            logger.error(f"Compilation failed for {tool_id}: {e}")
            raise
    
    async def execute_tool(self, tool_id: str, params: Dict[str, Any], 
                          tenant_id: str = None, context: ToolContext = None) -> Any:
        """Execute a compiled tool with context injection"""
        if tool_id not in self.compiled_cache:
            raise ValueError(f"Tool {tool_id} not compiled")
        
        compiled_tool = self.compiled_cache[tool_id]
        
        # Create context if not provided
        if context is None:
            context = ToolContext(self, tenant_id)
        
        try:
            # Inject context into parameters
            enhanced_params = {**params, 'context': context}
            
            # Execute with timeout
            if asyncio.iscoroutinefunction(compiled_tool.func):
                result = await asyncio.wait_for(
                    compiled_tool.func(**enhanced_params), 
                    timeout=30
                )
            else:
                result = compiled_tool.func(**enhanced_params)
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Tool {tool_id} execution timed out")
            raise
        except Exception as e:
            logger.error(f"Tool {tool_id} execution failed: {e}")
            raise
    
    def get_compiled_tool(self, tool_id: str) -> Optional[CompiledTool]:
        """Get a compiled tool from cache"""
        return self.compiled_cache.get(tool_id)
    
    def clear_cache(self):
        """Clear compilation cache"""
        self.compiled_cache.clear()
        logger.info("Tool compilation cache cleared")

class SecurityError(Exception):
    """Raised when unsafe code is detected"""
    pass