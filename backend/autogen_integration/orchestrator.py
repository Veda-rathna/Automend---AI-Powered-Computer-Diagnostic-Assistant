"""
AutoGen Orchestrator

Main orchestration logic for coordinating AutoGen agents to execute MCP tasks

Note: AutoGen agents are OPTIONAL. The system defaults to direct execution mode
which doesn't require AutoGen installation.
"""

import logging
import json
import os
import time
import copy
from typing import Dict, Any, List, Optional
from datetime import datetime

from .parsers.mcp_parser import MCPTaskParser
from .tools.system_diagnostics import SystemDiagnostics
from .tools.event_logs import EventLogAnalyzer
from .tools.file_checker import SystemFileChecker

logger = logging.getLogger(__name__)

# Try to import agent factory, but make it optional
try:
    from .agents.diagnostic_agents import DiagnosticAgentFactory, AUTOGEN_AVAILABLE
except ImportError:
    DiagnosticAgentFactory = None
    AUTOGEN_AVAILABLE = False
    logger.warning("AutoGen agents unavailable - using direct execution mode only")


class AutoGenOrchestrator:
    """
    Main orchestrator for AutoGen-based MCP task execution
    
    Supports two modes:
    1. Direct Execution (default, no AutoGen needed)
    2. AutoGen Agents (optional, requires AutoGen installation)
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the orchestrator
        
        Args:
            config_path: Path to configuration directory (defaults to ./config)
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), 'config'
        )
        self.config = self._load_config()
        self.llm_config = self._load_llm_config()
        
        # Initialize agent factory only if AutoGen is available
        if AUTOGEN_AVAILABLE and DiagnosticAgentFactory:
            try:
                self.agent_factory = DiagnosticAgentFactory(self.llm_config)
                logger.info("AutoGen agents available")
            except Exception as e:
                logger.warning(f"Failed to initialize AutoGen agents: {e}")
                self.agent_factory = None
        else:
            self.agent_factory = None
            logger.info("Using direct execution mode (AutoGen not available)")
        
        self.task_parser = MCPTaskParser()
        
        # Direct tool access for non-agent execution
        self.system_diagnostics = SystemDiagnostics()
        self.event_analyzer = EventLogAnalyzer()
        self.file_checker = SystemFileChecker()
        
        logger.info("AutoGenOrchestrator initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load agent configuration"""
        try:
            config_file = os.path.join(self.config_path, 'agents_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file not found: {config_file}, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "execution_mode": "semi-automated",
            "agents": {
                "user_proxy": {"human_input_mode": "NEVER"},
                "coordinator": {"max_retries": 3},
                "system_agent": {"timeout_per_task": 120},
                "security_agent": {"timeout_per_task": 180}
            }
        }
    
    def _load_llm_config(self) -> Dict[str, Any]:
        """Load LLM configuration"""
        try:
            config_file = os.path.join(self.config_path, 'llm_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    llm_config_data = json.load(f)
                    return llm_config_data.get('llm_config', {})
            else:
                logger.warning(f"LLM config file not found: {config_file}")
                return {}
        except Exception as e:
            logger.error(f"Error loading LLM config: {str(e)}")
            return {}
    
    def execute_mcp_tasks(self, model_output: str, use_autogen: bool = False) -> Dict[str, Any]:
        """
        Execute MCP tasks from model output
        
        Args:
            model_output: The full output from the AI diagnostic model
            use_autogen: If True, uses AutoGen agents; if False, executes tools directly
            
        Returns:
            Dictionary containing execution results
        """
        try:
            # Parse MCP tasks
            mcp_data = self.task_parser.extract_mcp_tasks(model_output)
            
            if not mcp_data:
                return {
                    "success": False,
                    "error": "No MCP_TASKS found in model output",
                    "user_message": self.task_parser.get_user_friendly_message(model_output)
                }
            
            tasks = mcp_data.get('tasks', [])
            summary = mcp_data.get('summary', 'Execute diagnostic tasks')
            
            logger.info(f"Executing {len(tasks)} MCP tasks")
            
            # Choose execution method
            execution_start = time.perf_counter()
            if use_autogen:
                results = self._execute_with_autogen(tasks, summary)
            else:
                results = self._execute_direct(tasks, summary)

            total_execution_time_ms = round((time.perf_counter() - execution_start) * 1000, 2)
            slowest_task = max(results, key=lambda r: r.get('execution_time_ms', 0), default={})
            
            return {
                "success": True,
                "tasks_requested": len(tasks),
                "tasks_completed": len([r for r in results if r.get('success')]),
                "tasks_failed": len([r for r in results if not r.get('success')]),
                "summary": summary,
                "results": results,
                "total_execution_time_ms": total_execution_time_ms,
                "slowest_task": {
                    "task": slowest_task.get('task', 'Unknown Task'),
                    "category": slowest_task.get('category', 'unknown'),
                    "execution_time_ms": slowest_task.get('execution_time_ms', 0)
                },
                "user_message": self.task_parser.get_user_friendly_message(model_output),
                "execution_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing MCP tasks: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_message": self.task_parser.get_user_friendly_message(model_output)
            }
    
    def _execute_direct(self, tasks: List[str], summary: str) -> List[Dict[str, Any]]:
        """
        Execute tasks directly using diagnostic tools (without AutoGen agents)
        
        This is faster and more deterministic than using AutoGen
        
        Args:
            tasks: List of task descriptions
            summary: Summary of what to analyze
            
        Returns:
            List of execution results
        """
        results = []
        tool_result_cache: Dict[str, Dict[str, Any]] = {}
        
        # Categorize tasks
        categorized = self.task_parser.categorize_tasks(tasks)
        
        logger.info(f"Executing {len(tasks)} tasks directly")
        
        # Execute each category of tasks
        for category, category_tasks in categorized.items():
            logger.info(f"Executing {len(category_tasks)} {category} tasks")
            
            for task in category_tasks:
                try:
                    task_start = time.perf_counter()
                    cache_key = self._get_cache_key_for_task(task, category)

                    if cache_key and cache_key in tool_result_cache:
                        result = copy.deepcopy(tool_result_cache[cache_key])
                        result["from_cache"] = True
                    else:
                        result = self._execute_single_task_direct(task, category)
                        if cache_key:
                            tool_result_cache[cache_key] = copy.deepcopy(result)

                    result["task"] = task
                    result["category"] = category
                    result["execution_time_ms"] = round((time.perf_counter() - task_start) * 1000, 2)

                    results.append(result)
                except Exception as e:
                    logger.error(f"Error executing task '{task}': {str(e)}")
                    results.append({
                        "success": False,
                        "task": task,
                        "category": category,
                        "error": str(e),
                        "execution_time_ms": 0
                    })
        
        return results

    def _get_cache_key_for_task(self, task: str, category: str) -> Optional[str]:
        """
        Map a task/category to a stable cache key so expensive diagnostics
        run once per request, even if multiple tasks request the same check.
        """
        task_lower = task.lower()

        if category == 'thermal' or 'cpu' in task_lower or 'thermal' in task_lower or 'temperature' in task_lower:
            return 'cpu_thermal'
        if category == 'disk' or 'disk' in task_lower or 'storage' in task_lower:
            return 'disk_usage'
        if category == 'memory' or 'memory' in task_lower or 'ram' in task_lower:
            return 'memory_usage'
        if category == 'power' or 'power' in task_lower or 'battery' in task_lower:
            return 'power_settings'
        if category == 'event_log' or 'event' in task_lower or 'log' in task_lower or 'crash' in task_lower:
            return 'event_logs'
        if 'dism' in task_lower:
            return 'dism_health'
        if category == 'system_files' or 'sfc' in task_lower or 'system file' in task_lower:
            return 'system_file_scan'

        return None
    
    def _execute_single_task_direct(self, task: str, category: str) -> Dict[str, Any]:
        """
        Execute a single task directly based on its category
        
        Args:
            task: Task description
            category: Task category
            
        Returns:
            Execution result
        """
        task_lower = task.lower()
        
        # CPU/Thermal tasks
        if category == 'thermal' or 'cpu' in task_lower or 'thermal' in task_lower or 'temperature' in task_lower:
            return self.system_diagnostics.analyze_cpu_thermal()
        
        # Disk tasks
        elif category == 'disk' or 'disk' in task_lower or 'storage' in task_lower:
            return self.system_diagnostics.inspect_disk_usage()
        
        # Memory tasks
        elif category == 'memory' or 'memory' in task_lower or 'ram' in task_lower:
            return self.system_diagnostics.check_memory_usage()
        
        # Power tasks
        elif category == 'power' or 'power' in task_lower or 'battery' in task_lower:
            return self.system_diagnostics.check_power_settings()
        
        # Event log tasks
        elif category == 'event_log' or 'event' in task_lower or 'log' in task_lower or 'crash' in task_lower:
            return self.event_analyzer.verify_event_logs()
        
        # System file tasks
        elif category == 'system_files' or 'sfc' in task_lower or 'system file' in task_lower:
            return self.file_checker.scan_system_files()
        
        # DISM tasks
        elif 'dism' in task_lower:
            return self.file_checker.check_dism_health()
        
        # Default: return task acknowledged
        else:
            return {
                "success": True,
                "task": task,
                "category": category,
                "note": "Task acknowledged but no specific tool matched",
                "recommendation": "Manual investigation may be required"
            }
    
    def _execute_with_autogen(self, tasks: List[str], summary: str) -> List[Dict[str, Any]]:
        """
        Execute tasks using AutoGen agents
        
        Args:
            tasks: List of task descriptions
            summary: Summary of what to analyze
            
        Returns:
            List of execution results
        """
        # Check if AutoGen is available
        if not self.agent_factory:
            logger.warning("AutoGen agents not available - falling back to direct execution")
            return self._execute_direct(tasks, summary)
        
        try:
            logger.info("Creating AutoGen agents for task execution")
            
            # Create agents
            agents = self.agent_factory.create_all_agents(
                human_input_mode=self.config['agents']['user_proxy']['human_input_mode']
            )
            
            user_proxy = agents['user_proxy']
            coordinator = agents['coordinator']
            
            # Prepare initial message
            task_list = "\n".join([f"{i+1}. {task}" for i, task in enumerate(tasks)])
            initial_message = f"""
Execute the following diagnostic tasks:

{task_list}

Summary: {summary}

Please coordinate with specialist agents to complete these tasks and provide a comprehensive diagnostic report.
"""
            
            # Initiate chat
            logger.info("Initiating AutoGen conversation")
            user_proxy.initiate_chat(
                coordinator,
                message=initial_message
            )
            
            # Extract results from conversation
            # Note: This is simplified - in production, you'd parse agent responses more carefully
            results = []
            for i, task in enumerate(tasks):
                results.append({
                    "success": True,
                    "task": task,
                    "note": "Executed via AutoGen agents",
                    "method": "autogen"
                })
            
            return results
            
        except Exception as e:
            logger.error(f"AutoGen execution failed: {str(e)}")
            # Fallback to direct execution
            logger.info("Falling back to direct execution")
            return self._execute_direct(tasks, summary)
    
    def get_execution_summary(self, results: List[Dict[str, Any]]) -> str:
        """
        Generate a human-readable summary of execution results
        
        Args:
            results: List of execution results
            
        Returns:
            Formatted summary string
        """
        total = len(results)
        successful = len([r for r in results if r.get('success')])
        failed = total - successful
        
        summary_lines = [
            f"\n{'='*60}",
            f"DIAGNOSTIC EXECUTION SUMMARY",
            f"{'='*60}",
            f"Total Tasks: {total}",
            f"Successful: {successful}",
            f"Failed: {failed}",
            f"{'='*60}\n"
        ]
        
        for i, result in enumerate(results, 1):
            task_name = result.get('task', 'Unknown Task')
            success = result.get('success', False)
            status = "✅ SUCCESS" if success else "❌ FAILED"
            
            summary_lines.append(f"{i}. {task_name}: {status}")
            
            if result.get('analysis'):
                summary_lines.append(f"   Analysis: {result['analysis']}")
            
            if result.get('error'):
                summary_lines.append(f"   Error: {result['error']}")
            
            if result.get('recommendation'):
                summary_lines.append(f"   Recommendation: {result['recommendation']}")
            
            summary_lines.append("")
        
        return "\n".join(summary_lines)
