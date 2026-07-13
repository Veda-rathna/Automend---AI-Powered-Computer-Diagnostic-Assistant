"""
System File Checker Tools

Tools for system file integrity verification
"""

import subprocess
import logging
import platform
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SystemFileChecker:
    """Tools for system file integrity checks"""
    
    @staticmethod
    def scan_system_files() -> Dict[str, Any]:
        """
        Scan system files for potential corruption using SFC
        
        Note: This requires administrator privileges
        
        Returns:
            Dictionary with SFC scan results
        """
        try:
            result = {
                "success": True,
                "task": "System File Checker (SFC) Scan",
                "data": {}
            }
            
            if platform.system() != "Windows":
                return {
                    "success": False,
                    "task": "SFC Scan",
                    "error": "SFC scan only available on Windows"
                }
            
            # Check if running as admin
            try:
                is_admin = os.getuid() == 0
            except AttributeError:
                # Windows
                import ctypes
                try:
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                except:
                    is_admin = False
            
            if not is_admin:
                result["success"] = False
                result["error"] = "Administrator privileges required for SFC scan"
                result["recommendation"] = "Run this application as Administrator to perform SFC scan"
                result["manual_command"] = "sfc /scannow"
                logger.warning("SFC scan requires admin privileges")
                return result
            
            # Run SFC scan (this can take a long time)
            result["data"]["status"] = "Starting SFC scan (this may take several minutes)..."
            
            try:
                # For safety, we'll just verify instead of full scan in automated mode
                # Full scan: sfc /scannow
                # Verify only: sfc /verifyonly
                cmd = "sfc /verifyonly"
                # Keep interactive API responses responsive by capping automated SFC runtime.
                output = subprocess.check_output(cmd, shell=True, text=True, timeout=120)
                
                result["data"]["scan_output"] = output
                
                # Parse results
                if "did not find any integrity violations" in output.lower():
                    result["analysis"] = "✅ No system file corruption detected"
                    result["severity"] = "low"
                elif "found corrupt files" in output.lower() or "integrity violations" in output.lower():
                    result["analysis"] = "⚠️ System file corruption detected"
                    result["severity"] = "high"
                    result["recommendation"] = "Run 'sfc /scannow' as Administrator to repair files"
                elif "could not perform" in output.lower() or "windows resource protection" in output.lower():
                    result["analysis"] = "⚡ SFC scan encountered issues"
                    result["severity"] = "medium"
                else:
                    result["analysis"] = "SFC scan completed - review output for details"
                    result["severity"] = "medium"
                
            except subprocess.TimeoutExpired:
                result["data"]["scan_note"] = "SFC scan timed out after 2 minutes"
                result["recommendation"] = "Run SFC scan manually: sfc /scannow"
            except subprocess.CalledProcessError as e:
                result["data"]["scan_note"] = f"SFC scan returned error code {e.returncode}"
                result["data"]["error_output"] = e.output if hasattr(e, 'output') else str(e)
            
            logger.info(f"SFC scan completed: {result.get('analysis', 'No analysis')}")
            return result
            
        except Exception as e:
            logger.error(f"SFC scan failed: {str(e)}")
            return {
                "success": False,
                "task": "System File Checker (SFC) Scan",
                "error": str(e),
                "recommendation": "Run 'sfc /scannow' manually as Administrator"
            }
    
    @staticmethod
    def check_dism_health() -> Dict[str, Any]:
        """
        Check Windows image health using DISM
        
        Note: This requires administrator privileges
        
        Returns:
            Dictionary with DISM check results
        """
        try:
            result = {
                "success": True,
                "task": "DISM Health Check",
                "data": {}
            }
            
            if platform.system() != "Windows":
                return {
                    "success": False,
                    "task": "DISM Check",
                    "error": "DISM check only available on Windows"
                }
            
            # Check if running as admin
            try:
                is_admin = os.getuid() == 0
            except AttributeError:
                import ctypes
                try:
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                except:
                    is_admin = False
            
            if not is_admin:
                result["success"] = False
                result["error"] = "Administrator privileges required for DISM check"
                result["recommendation"] = "Run as Administrator to perform DISM check"
                result["manual_command"] = "DISM /Online /Cleanup-Image /CheckHealth"
                logger.warning("DISM check requires admin privileges")
                return result
            
            # Run DISM CheckHealth (quick check)
            try:
                cmd = "DISM /Online /Cleanup-Image /CheckHealth"
                output = subprocess.check_output(cmd, shell=True, text=True, timeout=120)
                
                result["data"]["check_output"] = output
                
                if "no component store corruption detected" in output.lower():
                    result["analysis"] = "✅ Windows image health OK"
                    result["severity"] = "low"
                elif "corruption" in output.lower():
                    result["analysis"] = "⚠️ Windows image corruption detected"
                    result["severity"] = "high"
                    result["recommendation"] = "Run 'DISM /Online /Cleanup-Image /RestoreHealth' as Administrator"
                else:
                    result["analysis"] = "DISM check completed - review output"
                    result["severity"] = "low"
                
            except subprocess.TimeoutExpired:
                result["data"]["check_note"] = "DISM check timed out"
            except subprocess.CalledProcessError as e:
                result["data"]["check_note"] = f"DISM returned error code {e.returncode}"
            
            logger.info(f"DISM check completed: {result.get('analysis', 'No analysis')}")
            return result
            
        except Exception as e:
            logger.error(f"DISM check failed: {str(e)}")
            return {
                "success": False,
                "task": "DISM Health Check",
                "error": str(e),
                "recommendation": "Run 'DISM /Online /Cleanup-Image /CheckHealth' manually as Administrator"
            }
