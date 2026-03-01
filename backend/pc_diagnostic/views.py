from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.conf import settings
from django.http import FileResponse, Http404
from typing import Dict, List, Any
import random
import requests
import os
import uuid
import json
import platform
from datetime import datetime
import csv
import math
import urllib3

# Disable SSL warnings for cloudflare tunnels
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import hardware monitoring modules
from .hardware_monitor import HardwareMonitor
from .report_generator import ReportGenerator
from .hardware_hash import HardwareHashProtection
from .hardware_compatibility import HardwareCompatibilityChecker

# Import LLM provider factory
from .llm.factory import get_llm_provider

# Initialize hardware monitor and report generator
hardware_monitor = HardwareMonitor()
hardware_compatibility = HardwareCompatibilityChecker()
report_generator = ReportGenerator()
hardware_hash_protection = HardwareHashProtection()

# Local LLM API Configuration (kept for backward compatibility)
# Using Cloudflare tunnel for http://localhost:8888
LLM_API_BASE = "http://127.0.0.1:1234"
# Model ID - llama.cpp server auto-detects the loaded model, so we can use a simple identifier
LLM_MODEL_ID = "reasoning-llama-3.1-cot-re1-nmt-v2-orpo-i1"


def generate_mock_analysis(issue_description, telemetry_data):
    """Generate a mock diagnostic analysis when LLM server is unavailable"""
    
    # Analyze the telemetry data to provide a basic diagnosis
    analysis_sections = []
    
    # System Overview
    system_info = telemetry_data.get('system_info', {})
    analysis_sections.append(f"""
## System Analysis for: {issue_description}

**System Information:**
- Platform: {system_info.get('platform', 'Unknown')}
- Processor: {system_info.get('processor', 'Unknown')}
- Architecture: {system_info.get('machine', 'Unknown')}
- Python Version: {system_info.get('python_version', 'Unknown')}
""")

    # CPU Analysis
    cpu_data = telemetry_data.get('cpu', {})
    if cpu_data:
        cpu_usage = cpu_data.get('total_usage', 0)
        analysis_sections.append(f"""
**CPU Analysis:**
- Current Usage: {cpu_usage:.1f}%
- Status: {'⚠️ High Usage' if cpu_usage > 80 else '✅ Normal' if cpu_usage < 50 else '⚡ Moderate Usage'}
""")

    # Memory Analysis
    memory_data = telemetry_data.get('memory', {})
    if memory_data:
        memory_usage = memory_data.get('percentage', 0)
        memory_total = memory_data.get('total', 0)
        analysis_sections.append(f"""
**Memory Analysis:**
- Usage: {memory_usage:.1f}% ({memory_total // (1024**3):.1f} GB total)
- Status: {'⚠️ High Memory Usage' if memory_usage > 85 else '✅ Normal' if memory_usage < 70 else '⚡ Moderate Usage'}
""")

    # Basic Recommendations
    recommendations = []
    
    if 'screen' in issue_description.lower() or 'display' in issue_description.lower():
        recommendations.extend([
            "1. **Update Graphics Drivers**: Check Device Manager for display adapter updates",
            "2. **Check Cable Connections**: Ensure monitor cables are securely connected",
            "3. **Adjust Refresh Rate**: Try lowering the display refresh rate",
            "4. **Test Different Monitor**: Connect to another display to isolate the issue"
        ])
    elif 'slow' in issue_description.lower() or 'performance' in issue_description.lower():
        if cpu_usage > 80:
            recommendations.append("1. **High CPU Usage Detected**: Check Task Manager for resource-intensive processes")
        if memory_usage > 85:
            recommendations.append("2. **High Memory Usage**: Consider closing unnecessary applications or adding more RAM")
        recommendations.extend([
            "3. **Disk Cleanup**: Run disk cleanup and defragmentation",
            "4. **Startup Programs**: Disable unnecessary startup programs",
            "5. **Malware Scan**: Run a full system antivirus scan"
        ])
    else:
        recommendations.extend([
            "1. **System Update**: Ensure Windows is up to date",
            "2. **Driver Updates**: Check Device Manager for any driver issues",
            "3. **Event Viewer**: Check Windows Event Viewer for error messages",
            "4. **Safe Mode**: Test if the issue persists in Safe Mode"
        ])

    # Combine all sections
    mock_response = "\n".join(analysis_sections)
    
    if recommendations:
        mock_response += "\n\n## Recommended Solutions:\n\n"
        mock_response += "\n".join(recommendations)
    
    mock_response += f"""

## Next Steps:
1. **Try the recommended solutions** in order of priority
2. **Monitor system performance** using the collected telemetry data
3. **Contact support** if issues persist with the detailed diagnostic report

---
*Note: This analysis was generated using offline diagnostic capabilities. The AI diagnostic service is currently unavailable (Gemini API → Local LLaMA → Offline mode).*
"""
    
    return mock_response


@api_view(['POST'])
def diagnose(request):
    """
    AI-driven PC diagnostic endpoint
    Accepts a query and returns a diagnostic message
    """
    query = request.data.get('query', '')
    
    if not query:
        return Response(
            {'error': 'Query is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Simulate AI diagnostic responses
    diagnostics = [
        f"Analyzing your issue: '{query}'. Based on my assessment, this could be related to system resources.",
        f"I've processed your query: '{query}'. Consider checking your disk space and memory usage.",
        f"Regarding '{query}': I recommend running a system scan and updating your drivers.",
        f"Your query '{query}' suggests a possible software conflict. Try restarting the affected application.",
        f"After analyzing '{query}', I suggest clearing your cache and temporary files.",
    ]
    
    response_message = random.choice(diagnostics)
    
    return Response({
        'query': query,
        'diagnosis': response_message,
        'timestamp': request.data.get('timestamp', None)
    })


@api_view(['POST'])
def predict(request):
    """
    Handle prediction requests using the local reasoning model with telemetry data
    
    Request Body:
        {
            "input_text": "User's problem description",
            "telemetry_data": {...},  // Optional: system telemetry data
            "generate_report": true,   // Optional: generate downloadable report
            "execute_mcp_tasks": true  // Optional: auto-execute MCP tasks
        }
    
    Response:
        {
            "success": true,
            "message": "The AI assistant's full response text",
            "model": "model-name",
            "finish_reason": "stop",
            "session_id": "uuid",
            "telemetry_collected": true,
            "telemetry_summary": {...},
            "reports": {...},  // If generate_report=true
            "mcp_execution": {...},  // If execute_mcp_tasks=true
            "usage": {...},
            "metadata": {...}
        }
    """
    try:
        # Extract input from the request
        input_text = request.data.get('input_text', '')
        provided_telemetry = request.data.get('telemetry_data', None)
        generate_report = request.data.get('generate_report', False)
        execute_mcp = request.data.get('execute_mcp_tasks', True)  # Auto-execute by default
        
        if not input_text:
            return Response(
                {
                    'success': False,
                    'error': 'No input provided. Please provide input_text in the request body.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate session ID for this diagnosis
        session_id = str(uuid.uuid4())
        
        # Collect system telemetry data based on the issue type
        print(f"Collecting telemetry data for issue: {input_text}")
        
        if provided_telemetry:
            telemetry_data = provided_telemetry
        else:
            telemetry_data = hardware_monitor.get_system_health(input_text)
        
        # Check telemetry data size and potentially summarize if too large
        telemetry_json = json.dumps(telemetry_data, indent=2, default=str)
        telemetry_size = len(telemetry_json)
        
        # If telemetry data is very large (>20KB), create a summary instead
        if telemetry_size > 20000:
            print(f"⚠️ Telemetry data is large ({telemetry_size} chars), creating summary...")
            telemetry_summary = {
                'timestamp': telemetry_data.get('timestamp'),
                'system_info': telemetry_data.get('system_info'),
                'cpu': {
                    'total_usage': telemetry_data.get('cpu', {}).get('total_usage'),
                    'per_cpu_usage': 'omitted for brevity'
                },
                'memory': telemetry_data.get('memory'),
                'disk': 'omitted for brevity' if len(str(telemetry_data.get('disk', {}))) > 1000 else telemetry_data.get('disk'),
                'issue_specific': telemetry_data.get('issue_specific'),
                'note': 'Full telemetry data available in generated report'
            }
            telemetry_json = json.dumps(telemetry_summary, indent=2, default=str)
            print(f"[INFO] Summarized to {len(telemetry_json)} chars")
        
        # Prepare the enhanced prompt with telemetry data
        user_prompt = f"""
User Problem: {input_text}

System Telemetry Data:
{telemetry_json}

Please provide a comprehensive diagnosis and solution based on this real-time system data.
"""
        
        # Prepare the system prompt
        system_prompt = """You are an AI PC Diagnostic Expert. Analyze real-time telemetry data to distinguish hardware from software issues.

CORE RULES:
1. Base diagnosis ONLY on provided telemetry data - show specific metrics
2. Classify issue as HARDWARE or SOFTWARE
3. Generate MCP tasks ONLY for SOFTWARE issues that can be fixed programmatically
4. For HARDWARE issues: skip MCP tasks, recommend service center

HARDWARE INDICATORS:
- Abnormal temps (CPU >85°C, GPU >80°C)
- SMART errors, bad sectors
- Component not detected (PCI, display)
- Issues persist in Safe Mode/BIOS
- Physical damage symptoms

SOFTWARE INDICATORS:
- Normal hardware metrics but instability
- Event Viewer errors (drivers, apps)
- Started after update/installation
- Resolves in Safe Mode
- High CPU/RAM by specific process

RESPONSE FORMAT:

**Diagnosis Summary:**
- Issue Type: [HARDWARE / SOFTWARE]
- Root Cause: [specific component/service]
- Key Telemetry: [show only issue-relevant metrics with values]
- Confidence: [High/Medium/Low]

**Analysis:**
Explain correlation between symptoms and telemetry data.

**If SOFTWARE:**
✅ Automated fixes available
[Manual steps user can try]

I'll run automated diagnostics to:
- [What will be checked/fixed]

<MCP_TASKS>
{
  "issue_type": "software",
  "tasks": [
    "Specific system-level diagnostic 1",
    "Specific system-level diagnostic 2"
  ],
  "summary": "Automated software diagnostics"
}
</MCP_TASKS>

**If HARDWARE:**
⚠️ HARDWARE FAILURE DETECTED
- Component: [specific part]
- Why Hardware: [telemetry evidence]
- User Actions:
  1. [Physical check if safe]
  2. [Testing steps]
  3. Service center required

<MCP_TASKS>
{
  "issue_type": "hardware",
  "tasks": [],
  "summary": "Hardware issue - automated tasks skipped",
  "hardware_component": "[component]",
  "service_required": true
}
</MCP_TASKS>

EXAMPLES:

Ex1: "Computer slow" | Telemetry: Disk 100% by Windows Update, CPU 45°C, RAM 92%
→ SOFTWARE (process bottleneck)
→ Generate MCP tasks: Clear update cache, optimize services
→ Show: Disk usage metrics only

Ex2: "Screen has lines" | Telemetry: GPU 42°C, no driver errors, artifacts in BIOS
→ HARDWARE (GPU/LCD failure)
→ NO MCP tasks
→ Recommend: External monitor test, service center
→ Show: GPU/display metrics only

Focus on issue-specific telemetry only. Be decisive. Provide actionable next steps."""
        
        # Combine system prompt and user prompt for providers that don't support roles
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Call the LLM using the provider factory pattern
        try:
            print("[LLM] Initializing LLM provider...")
            provider = get_llm_provider()
            provider_name = provider.get_provider_name()
            print(f"[LLM] Using {provider_name} for prediction")
            
            # Call the provider's complete method
            llm_result = provider.complete(
                prompt=full_prompt,
                temperature=0.7,
                max_tokens=4000
            )
            
            # Extract results from provider response
            prediction = llm_result['content']
            model_used = llm_result['model']
            finish_reason = llm_result['finish_reason']
            usage = llm_result['usage']
            metadata = llm_result['metadata']
            
            if not prediction:
                return Response(
                    {
                        'success': False,
                        'error': 'No content in model response'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Detect if this is a hardware issue by parsing the MCP_TASKS block
            is_hardware_issue = False
            hardware_component = None
            
            try:
                # Extract MCP_TASKS JSON from the response
                if '<MCP_TASKS>' in prediction and '</MCP_TASKS>' in prediction:
                    start_idx = prediction.find('<MCP_TASKS>') + len('<MCP_TASKS>')
                    end_idx = prediction.find('</MCP_TASKS>')
                    mcp_json_str = prediction[start_idx:end_idx].strip()
                    
                    # Parse the JSON
                    mcp_data = json.loads(mcp_json_str)
                    
                    # Check if it's a hardware issue
                    if mcp_data.get('issue_type') == 'hardware':
                        is_hardware_issue = True
                        hardware_component = mcp_data.get('hardware_component', 'Unknown Component')
                        print(f"[HW] Hardware issue detected: {hardware_component}")
            except Exception as parse_error:
                print(f"Warning: Could not parse MCP tasks for hardware detection: {str(parse_error)}")
            
            # Build response data
            response_data = {
                'success': True,
                'message': prediction,
                'prediction': prediction,
                'model': model_used,
                'ai_provider': provider_name,  # Add provider name for judges
                'finish_reason': finish_reason,
                'session_id': session_id,
                'is_hardware_issue': is_hardware_issue,
                'telemetry_collected': True,
                'telemetry_summary': {
                    'timestamp': telemetry_data.get('timestamp'),
                    'system': telemetry_data.get('system_info', {}).get('platform'),
                    'cpu_usage': telemetry_data.get('cpu', {}).get('total_usage'),
                    'memory_usage': telemetry_data.get('memory', {}).get('percentage'),
                    'issue_specific_data': list(telemetry_data.get('issue_specific', {}).keys())
                },
                'usage': usage,
                'metadata': metadata
            }
            
            # Add hardware-specific navigation options if it's a hardware issue
            if is_hardware_issue:
                response_data['hardware_issue_details'] = {
                    'component': hardware_component,
                    'requires_service': True,
                    'navigation_options': {
                        'service_center': {
                            'label': 'Find Nearby Service Centers',
                            'description': 'Locate authorized repair centers near your location',
                            'action': 'navigate_to_service_centers',
                            'icon': 'location'
                        },
                        'hardware_protection': {
                            'label': 'Hardware Protection',
                            'description': 'Generate hardware fingerprint to verify component authenticity',
                            'action': 'navigate_to_hardware_protection',
                            'icon': 'shield'
                        }
                    },
                    'recommendation': 'This issue requires professional hardware service. Use the buttons below to find service centers or protect your hardware identity.'
                }
                print(f"[HW] Added hardware navigation options to response")
            
            # Execute MCP tasks if requested
            if execute_mcp:
                try:
                    from autogen_integration.orchestrator import AutoGenOrchestrator
                    
                    print("Executing MCP tasks...")
                    orchestrator = AutoGenOrchestrator()
                    mcp_result = orchestrator.execute_mcp_tasks(prediction, use_autogen=False)
                    
                    if mcp_result.get('success'):
                        # Format detailed task results for display in chat
                        task_results = mcp_result.get('results', [])
                        formatted_tasks = []
                        
                        for i, task_result in enumerate(task_results, 1):
                            # Limit the size of details to prevent response bloat
                            details = task_result.get('details', {})
                            if isinstance(details, dict):
                                # Limit string lengths in details
                                limited_details = {}
                                for key, value in details.items():
                                    if isinstance(value, str) and len(value) > 500:
                                        limited_details[key] = value[:500] + "... (truncated)"
                                    elif isinstance(value, list) and len(value) > 10:
                                        limited_details[key] = value[:10] + ["... (truncated)"]
                                    else:
                                        limited_details[key] = value
                                details = limited_details
                            
                            task_info = {
                                'task_number': i,
                                'task_name': task_result.get('task', 'Unknown Task'),
                                'success': task_result.get('success', False),
                                'status': "✅ Completed" if task_result.get('success') else "❌ Failed",
                                'analysis': task_result.get('analysis', '')[:1000] if task_result.get('analysis') else '',  # Limit analysis length
                                'error': task_result.get('error', ''),
                                'recommendation': task_result.get('recommendation', ''),
                                'details': details,
                                'timestamp': task_result.get('timestamp', '')
                            }
                            formatted_tasks.append(task_info)
                        
                        response_data['mcp_execution'] = {
                            'executed': True,
                            'tasks_completed': mcp_result.get('tasks_completed', 0),
                            'tasks_failed': mcp_result.get('tasks_failed', 0),
                            'total_tasks': len(task_results),
                            'tasks': formatted_tasks,  # Detailed task-by-task results (size-limited)
                            'summary': mcp_result.get('summary', ''),
                            'execution_summary': orchestrator.get_execution_summary(mcp_result.get('results', []))
                        }
                        print(f"MCP tasks executed: {mcp_result.get('tasks_completed', 0)} completed")
                    else:
                        response_data['mcp_execution'] = {
                            'executed': False,
                            'note': mcp_result.get('error', 'No MCP tasks found in response')
                        }
                except Exception as mcp_error:
                    print(f"MCP execution error: {str(mcp_error)}")
                    import traceback
                    traceback.print_exc()
                    response_data['mcp_execution'] = {
                        'executed': False,
                        'error': str(mcp_error),
                        'note': 'MCP task execution failed - diagnostics available via /api/mcp/execute endpoint'
                    }
            
            # Generate reports if requested
            if generate_report:
                try:
                    # Generate JSON report
                    json_filename, json_filepath = report_generator.generate_json_report(
                        input_text, telemetry_data, prediction, session_id
                    )
                    
                    response_data['reports'] = {
                        'json': {
                            'filename': json_filename,
                            'download_url': f'/api/download_report/{json_filename}'
                        }
                    }
                    
                    print(f"Report generated: {json_filename}")
                    
                except Exception as report_error:
                    print(f"Report generation error: {str(report_error)}")
                    response_data['report_error'] = f"Failed to generate reports: {str(report_error)}"
            
            # Ensure all response data is JSON serializable and log response size
            try:
                import sys
                response_json = json.dumps(response_data, default=str)
                response_size = sys.getsizeof(response_json)
                print(f"✅ Response prepared: {response_size / 1024:.2f} KB")
                print(f"📤 Sending response to frontend with keys: {list(response_data.keys())}")
                
                # If response is very large, warn about it
                if response_size > 500000:  # 500KB
                    print(f"⚠️ Large response size: {response_size / 1024:.2f} KB - may cause network issues")
            except Exception as json_err:
                print(f"❌ Response serialization check failed: {str(json_err)}")
                import traceback
                traceback.print_exc()
            
            print(f"🚀 Returning Response object to Django...")
            return Response(response_data)
                
        except Exception as provider_error:
            # Provider failed - fall back to offline mock analysis
            print(f"⚠️ LLM Provider Error: {str(provider_error)}")
            print("🔄 Falling back to offline diagnostic mode...")
            
            # Use simplified fallback analysis
            prediction = generate_mock_analysis(input_text, telemetry_data)
            model_used = "Offline Diagnostic Engine"
            finish_reason = "offline_mode"
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            metadata = {
                "provider": "Offline Mock",
                "id": "",
                "created": "",
                "object": "",
                "system_fingerprint": ""
            }
            
            # Detect potential hardware issues in offline mode based on keywords and telemetry
            is_hardware_issue = False
            hardware_keywords = ['screen', 'display', 'monitor', 'lines', 'artifacts', 'flickering', 
                               'dead pixel', 'won\'t turn on', 'no power', 'beeping', 'clicking',
                               'overheat', 'burning smell', 'physical damage', 'broken', 'cracked']
            
            # Check if user description contains hardware-related keywords
            input_lower = input_text.lower()
            for keyword in hardware_keywords:
                if keyword in input_lower:
                    is_hardware_issue = True
                    break
            
            # Also check telemetry for hardware issues
            if telemetry_data.get('cpu', {}).get('temperature', 0) > 85:
                is_hardware_issue = True
            
            response_data = {
                'success': True,
                'prediction': prediction,
                'message': prediction,
                'model': model_used,
                'ai_provider': "Offline Mock Engine",
                'finish_reason': finish_reason,
                'session_id': session_id,
                'is_hardware_issue': is_hardware_issue,
                'telemetry_collected': True,
                'telemetry_summary': {
                    'timestamp': telemetry_data.get('timestamp'),
                    'system': telemetry_data.get('system_info', {}).get('platform'),
                    'cpu_usage': telemetry_data.get('cpu', {}).get('total_usage'),
                    'memory_usage': telemetry_data.get('memory', {}).get('percentage'),
                    'issue_specific_data': list(telemetry_data.get('issue_specific', {}).keys())
                },
                'usage': usage,
                'metadata': metadata
            }
            
            # Add hardware navigation options if suspected hardware issue
            if is_hardware_issue:
                response_data['hardware_issue_details'] = {
                    'component': 'Suspected Hardware Component',
                    'requires_service': True,
                    'navigation_options': {
                        'service_center': {
                            'label': 'Find Nearby Service Centers',
                            'description': 'Locate authorized repair centers near your location',
                            'action': 'navigate_to_service_centers',
                            'icon': 'location'
                        },
                        'hardware_protection': {
                            'label': 'Hardware Protection',
                            'description': 'Generate hardware fingerprint to verify component authenticity',
                            'action': 'navigate_to_hardware_protection',
                            'icon': 'shield'
                        }
                    },
                    'recommendation': 'This appears to be a hardware-related issue. Use the buttons below to find service centers or protect your hardware identity.'
                }
                print(f"[HW] Hardware issue suspected in offline mode - added navigation options")
            
            # Generate reports if requested
            if generate_report:
                try:
                    json_filename, json_filepath = report_generator.generate_json_report(
                        input_text, telemetry_data, prediction, session_id
                    )
                    
                    response_data['reports'] = {
                        'json': {
                            'filename': json_filename,
                            'download_url': f'/api/download_report/{json_filename}'
                        }
                    }
                except Exception as report_error:
                    print(f"Report generation error: {str(report_error)}")
                    response_data['report_error'] = f"Failed to generate reports: {str(report_error)}"
            
            return Response(response_data)
    
    except Exception as outer_error:
        # Outer exception handler for any unexpected errors
        print(f"💥 Unexpected error in predict endpoint: {str(outer_error)}")
        import traceback
        traceback.print_exc()
        return Response(
            {
                'success': False,
                'error': f'Unexpected error: {str(outer_error)}',
                'type': type(outer_error).__name__
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):
    """Handle file uploads"""
    try:
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        
        if not file.name:
            return Response(
                {'error': 'No file selected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure upload directory exists
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # TODO: Process the file with your model
        # Example: result = your_model.predict_from_file(file_path)
        
        return Response({
            'success': True,
            'message': f'File {file.name} uploaded successfully',
            'filename': file.name
        })
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def download_report(request, filename):
    """Download generated diagnostic reports"""
    try:
        reports_folder = report_generator.reports_folder
        file_path = os.path.join(reports_folder, filename)
        
        # Security check: ensure the file exists and is in the reports folder
        if not os.path.exists(file_path) or not os.path.abspath(file_path).startswith(os.path.abspath(reports_folder)):
            raise Http404("Report not found")
        
        # Return the file
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to download report: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_reports(request):
    """List available diagnostic reports"""
    try:
        available_reports = report_generator.get_available_reports()
        return Response({
            'success': True,
            'reports': available_reports,
            'total_reports': len(available_reports)
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to list reports: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_telemetry(request):
    """Get current system telemetry without AI analysis"""
    try:
        issue_description = request.GET.get('issue', 'general')
        telemetry_data = hardware_monitor.get_system_health(issue_description)
        
        return Response({
            'success': True,
            'telemetry_data': telemetry_data,
            'timestamp': telemetry_data.get('timestamp')
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to collect telemetry: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def generate_hardware_hash(request):
    """
    Generate encrypted hardware hash file
    
    Request Body:
        {
            "password": "optional_custom_password"
        }
    
    Response:
        {
            "success": true,
            "file_path": "path/to/file",
            "hardware_hash": "hash_string",
            "download_url": "/api/download_hardware_hash/filename"
        }
    """
    try:
        password = request.data.get('password', 'default_password')
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        hostname = platform.node()
        filename = f"hardware_hash_{hostname}_{timestamp}.hwh"
        
        # Ensure hardware_hash directory exists
        hash_dir = os.path.join(settings.MEDIA_ROOT, 'hardware_hashes')
        os.makedirs(hash_dir, exist_ok=True)
        
        output_path = os.path.join(hash_dir, filename)
        
        # Generate hardware hash file
        result = hardware_hash_protection.create_hardware_hash_file(output_path, password)
        
        if result.get('success'):
            return Response({
                'success': True,
                'filename': filename,
                'file_path': output_path,
                'file_size': result.get('file_size'),
                'hardware_hash': result.get('hardware_hash'),
                'created': result.get('created'),
                'components_captured': result.get('components_captured'),
                'download_url': f'/api/download_hardware_hash/{filename}'
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Unknown error occurred')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to generate hardware hash: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def analyze_hardware_hash(request):
    """
    Analyze uploaded hardware hash file and compare with current hardware
    
    Request:
        - file: Hardware hash file (.hwh)
        - password: Password for decryption (optional)
    
    Response:
        {
            "success": true,
            "comparison": {
                "overall_status": "changed|unchanged",
                "changes_detected": [...],
                "changeable_components_changes": [...]
            }
        }
    """
    try:
        if 'file' not in request.FILES:
            return Response({
                'success': False,
                'error': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        password = request.data.get('password', 'default_password')
        
        # Save uploaded file temporarily
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        temp_file_path = os.path.join(upload_dir, file.name)
        with open(temp_file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Analyze the file
        analysis_result = hardware_hash_protection.analyze_hardware_hash_file(temp_file_path, password)
        
        # Clean up temporary file
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        if analysis_result.get('success'):
            return Response({
                'success': True,
                'comparison': analysis_result.get('comparison'),
                'file_info': analysis_result.get('comparison', {}).get('file_info'),
                'summary': analysis_result.get('comparison', {}).get('summary')
            })
        else:
            return Response({
                'success': False,
                'error': analysis_result.get('error', 'Analysis failed')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to analyze hardware hash: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def download_hardware_hash(request, filename):
    """Download generated hardware hash file"""
    try:
        hash_dir = os.path.join(settings.MEDIA_ROOT, 'hardware_hashes')
        file_path = os.path.join(hash_dir, filename)
        
        # Security check
        if not os.path.exists(file_path) or not os.path.abspath(file_path).startswith(os.path.abspath(hash_dir)):
            raise Http404("Hardware hash file not found")
        
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to download file: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula
    Returns distance in kilometers
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in kilometers
    r = 6371
    
    return c * r


@api_view(['POST'])
def get_nearby_service_centers(request):
    """
    Get nearby service centers based on user location
    
    Request Body:
        {
            "latitude": 13.0827,
            "longitude": 80.2707,
            "radius_km": 30,  // Optional, defaults to 30km
            "brand": "Dell"    // Optional, filter by brand
        }
    
    Response:
        {
            "success": true,
            "user_location": {"latitude": x, "longitude": y},
            "total_centers": 5,
            "service_centers": [...]
        }
    """
    try:
        # Get user location from request
        user_lat = request.data.get('latitude')
        user_lon = request.data.get('longitude')
        radius_km = request.data.get('radius_km', 30)
        brand_filter = request.data.get('brand')
        
        if user_lat is None or user_lon is None:
            return Response({
                'success': False,
                'error': 'Latitude and longitude are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_lat = float(user_lat)
            user_lon = float(user_lon)
            radius_km = float(radius_km)
        except ValueError:
            return Response({
                'success': False,
                'error': 'Invalid latitude, longitude, or radius values'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Read service centers from CSV
        csv_path = os.path.join(settings.BASE_DIR.parent, 'service_centers.csv')
        
        if not os.path.exists(csv_path):
            return Response({
                'success': False,
                'error': 'Service centers database not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        service_centers = []
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                # Skip if brand filter is applied and doesn't match
                if brand_filter and row['Brand'].lower() != brand_filter.lower():
                    continue
                
                # Skip if latitude or longitude is missing
                if not row.get('Latitude') or not row.get('Longitude'):
                    continue
                
                try:
                    center_lat = float(row['Latitude'])
                    center_lon = float(row['Longitude'])
                    
                    # Calculate distance
                    distance = calculate_distance(user_lat, user_lon, center_lat, center_lon)
                    
                    # Include only centers within the specified radius
                    if distance <= radius_km:
                        service_centers.append({
                            'brand': row['Brand'],
                            'name': row['Name'],
                            'phone': row['Phone'],
                            'address': row['Address'],
                            'city': row['City'],
                            'latitude': center_lat,
                            'longitude': center_lon,
                            'distance_km': round(distance, 2)
                        })
                
                except (ValueError, KeyError) as e:
                    # Skip invalid rows
                    continue
        
        # Sort by distance
        service_centers.sort(key=lambda x: x['distance_km'])
        
        return Response({
            'success': True,
            'user_location': {
                'latitude': user_lat,
                'longitude': user_lon
            },
            'radius_km': radius_km,
            'total_centers': len(service_centers),
            'service_centers': service_centers,
            'brands_available': list(set([center['brand'] for center in service_centers]))
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to fetch service centers: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def scan_hardware_specs(request):
    """
    Scan and return detailed hardware specifications for compatibility checking
    """
    try:
        specs = hardware_compatibility.get_detailed_hardware_specs()
        
        # Calculate power requirements
        power_info = hardware_compatibility.calculate_power_requirements(specs)
        specs['power_requirements'] = power_info
        
        return Response({
            'success': True,
            'hardware_specs': specs,
            'detected_fields': _get_detected_fields(specs),
            'missing_fields': _get_missing_fields(specs),
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to scan hardware: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def check_upgrade_compatibility(request):
    """
    Check if a proposed upgrade is compatible with existing hardware
    """
    try:
        # Get current system specs
        current_system = request.data.get('current_system', {})
        proposed_upgrade = request.data.get('proposed_upgrade', {})
        user_inputs = request.data.get('user_inputs', {})
        
        # If no current system provided, scan it
        if not current_system:
            current_system = hardware_compatibility.get_detailed_hardware_specs()
        
        # Merge user inputs into current system
        complete_system = _merge_dict_deep(current_system, user_inputs)
        
        # Build compatibility analysis prompt
        compatibility_prompt = f"""
You are a PC hardware compatibility expert. Analyze this upgrade scenario:

**Current System:**
```json
{json.dumps(complete_system, indent=2)}
```

**Proposed Upgrade:**
```json
{json.dumps(proposed_upgrade, indent=2)}
```

Please analyze and provide:

1. **Compatibility Status**: Is this upgrade compatible? (YES/NO/PARTIAL)

2. **Detailed Analysis**: 
   - Physical compatibility (sockets, slots, dimensions)
   - Power requirements (PSU adequacy)
   - Potential bottlenecks
   - BIOS/firmware considerations
   - Cooling requirements

3. **Warnings**: List any compatibility issues or concerns

4. **Recommendations**: 
   - Better alternatives if available
   - What else needs upgrading
   - Budget-friendly options

5. **Performance Estimate**: Expected performance improvement (percentage or qualitative)

6. **Installation Notes**: Any special installation requirements

Provide your response in a structured format with clear sections.
"""
        
        # Use LLM to analyze compatibility
        llm_provider = get_llm_provider()
        result = llm_provider.complete(compatibility_prompt, temperature=0.7, max_tokens=4000)
        
        # Parse the response
        analysis = result.get('content', 'Analysis completed')
        
        # Extract compatibility status from response
        is_compatible = 'YES' in analysis.upper() and 'COMPATIBLE' in analysis.upper()
        has_warnings = 'WARNING' in analysis.upper() or 'ISSUE' in analysis.upper()
        
        return Response({
            'success': True,
            'compatible': is_compatible,
            'has_warnings': has_warnings,
            'analysis': analysis,
            'current_system': complete_system,
            'proposed_upgrade': proposed_upgrade,
            'llm_provider': llm_provider.get_provider_name(),
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to check compatibility: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_upgrade_recommendations(request):
    """
    Get AI-powered upgrade recommendations based on current system and budget
    """
    try:
        current_system = request.data.get('current_system', {})
        budget = request.data.get('budget', 0)
        upgrade_goal = request.data.get('goal', 'general performance')
        user_inputs = request.data.get('user_inputs', {})
        
        # If no current system provided, scan it
        if not current_system:
            current_system = hardware_compatibility.get_detailed_hardware_specs()
        
        # Merge user inputs
        complete_system = _merge_dict_deep(current_system, user_inputs)
        
        # Build recommendation prompt
        recommendation_prompt = f"""
You are a PC hardware upgrade consultant for the Indian market. Based on this system, provide upgrade recommendations:

**Current System:**
```json
{json.dumps(complete_system, indent=2)}
```

**Budget**: ₹{budget:,.0f} INR (Indian Rupees)
**Upgrade Goal**: {upgrade_goal}

Please provide:

1. **Priority Upgrades**: What should be upgraded first and why?

2. **Specific Component Recommendations**: 
   - Exact models/specifications available in India
   - Expected price range in INR
   - Why this component

3. **Budget Allocation**: How to split the ₹{budget:,.0f} budget across components

4. **Compatibility Notes**: Ensure all recommendations are compatible

5. **Expected Performance Gains**: What improvements to expect

6. **Future-Proofing**: How long will these upgrades last?

7. **Alternative Options**: 
   - Budget-friendly alternatives available in India
   - Premium options if budget allows

8. **Where to Buy**: Mention reliable Indian retailers (Amazon.in, Flipkart, MDComputers, Vedant Computers, etc.)

Provide practical, specific recommendations with current Indian market prices and availability.
"""
        
        # Use LLM to generate recommendations
        llm_provider = get_llm_provider()
        result = llm_provider.complete(recommendation_prompt, temperature=0.7, max_tokens=4000)
        
        recommendations = result.get('content', 'Recommendations generated')
        
        return Response({
            'success': True,
            'recommendations': recommendations,
            'current_system': complete_system,
            'budget': budget,
            'goal': upgrade_goal,
            'llm_provider': llm_provider.get_provider_name(),
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to generate recommendations: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_detected_fields(specs: Dict[str, Any]) -> List[str]:
    """Get list of successfully detected hardware fields"""
    detected = []
    
    def check_dict(d, prefix=''):
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                check_dict(value, full_key)
            elif value is not None and value != '' and value != []:
                detected.append(full_key)
    
    check_dict(specs)
    return detected


def _get_missing_fields(specs: Dict[str, Any]) -> List[str]:
    """Get list of fields that need user input"""
    missing = []
    
    # Important fields that are typically None and need user input
    important_fields = [
        'psu.wattage',
        'psu.efficiency',
        'case.form_factor',
        'case.gpu_clearance_mm',
        'motherboard.ram_slots',
        'motherboard.max_ram_gb',
    ]
    
    def get_nested_value(d, path):
        keys = path.split('.')
        value = d
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    for field in important_fields:
        value = get_nested_value(specs, field)
        if value is None or value == '':
            missing.append(field)
    
    return missing


def _merge_dict_deep(base: Dict, updates: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dict_deep(result[key], value)
        else:
            result[key] = value
    
    return result

