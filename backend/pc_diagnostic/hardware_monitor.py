import psutil
import platform
import json
import subprocess
import socket
import time
import os
import sys
from datetime import datetime

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

# Try to import advanced telemetry module
try:
    from .advanced_telemetry import AdvancedTelemetry
    ADVANCED_TELEMETRY_AVAILABLE = True
except ImportError:
    ADVANCED_TELEMETRY_AVAILABLE = False
    print("⚠️ Advanced telemetry not available. Install: pip install pythonnet nvidia-ml-py3")

class HardwareMonitor:
    def __init__(self):
        self.wmi_conn = None
        if WMI_AVAILABLE and platform.system() == "Windows":
            try:
                self.wmi_conn = wmi.WMI()
            except:
                pass
        
        # Initialize advanced telemetry if available
        self.advanced_telemetry = None
        if ADVANCED_TELEMETRY_AVAILABLE:
            try:
                self.advanced_telemetry = AdvancedTelemetry()
                print("✅ Advanced telemetry initialized (LibreHardwareMonitor + NVML)")
            except Exception as e:
                print(f"⚠️ Advanced telemetry initialization failed: {str(e)}")

    def run_terminal_command(self, command, timeout=10):
        """Execute terminal command and return output"""
        try:
            if platform.system() == "Windows":
                # Use PowerShell for Windows
                result = subprocess.run(
                    ["powershell", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Use bash for Unix-like systems
                result = subprocess.run(
                    ["bash", "-c", command],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            
            return {
                "command": command,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "command": command,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": -1,
                "success": False
            }
        except Exception as e:
            return {
                "command": command,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "success": False
            }

    def _parse_json_output(self, stdout):
        """Parse command JSON output and normalize to a list of dicts."""
        if not stdout:
            return []

        try:
            parsed = json.loads(stdout)
        except Exception:
            return []

        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            return [parsed]
        return []

    def _load_display_info_from_powershell(self, display_data):
        """Fallback display detection using CIM via PowerShell on Windows."""
        if platform.system() != "Windows":
            return

        # GPU controllers (integrated + dedicated)
        if not display_data["graphics_cards"]:
            gpu_cmd = (
                "Get-CimInstance Win32_VideoController | "
                "Select-Object Name,DeviceID,PNPDeviceID,AdapterRAM,DriverVersion,DriverDate,Status,"
                "CurrentRefreshRate,CurrentHorizontalResolution,CurrentVerticalResolution | "
                "ConvertTo-Json -Depth 4"
            )
            gpu_result = self.run_terminal_command(gpu_cmd, timeout=20)
            if gpu_result.get("success"):
                for gpu in self._parse_json_output(gpu_result.get("stdout", "")):
                    display_data["graphics_cards"].append({
                        "name": gpu.get("Name"),
                        "device_id": gpu.get("DeviceID"),
                        "pnp_device_id": gpu.get("PNPDeviceID"),
                        "adapter_ram": gpu.get("AdapterRAM"),
                        "driver_version": gpu.get("DriverVersion"),
                        "driver_date": str(gpu.get("DriverDate")) if gpu.get("DriverDate") else None,
                        "status": gpu.get("Status"),
                        "current_refresh_rate": gpu.get("CurrentRefreshRate"),
                        "current_horizontal_resolution": gpu.get("CurrentHorizontalResolution"),
                        "current_vertical_resolution": gpu.get("CurrentVerticalResolution"),
                        "source": "powershell_cim"
                    })
            elif gpu_result.get("stderr"):
                display_data["errors"].append(f"PowerShell GPU fallback error: {gpu_result.get('stderr')}")

        # Monitor devices
        if not display_data["monitors"]:
            monitor_cmd = (
                "Get-CimInstance Win32_DesktopMonitor | "
                "Select-Object Name,DeviceID,PNPDeviceID,ScreenWidth,ScreenHeight,Status,Availability,MonitorType | "
                "ConvertTo-Json -Depth 4"
            )
            monitor_result = self.run_terminal_command(monitor_cmd, timeout=20)
            if monitor_result.get("success"):
                for monitor in self._parse_json_output(monitor_result.get("stdout", "")):
                    display_data["monitors"].append({
                        "name": monitor.get("Name"),
                        "device_id": monitor.get("DeviceID"),
                        "pnp_device_id": monitor.get("PNPDeviceID"),
                        "screen_width": monitor.get("ScreenWidth"),
                        "screen_height": monitor.get("ScreenHeight"),
                        "status": monitor.get("Status"),
                        "availability": monitor.get("Availability"),
                        "monitor_type": monitor.get("MonitorType"),
                        "source": "powershell_cim"
                    })
            elif monitor_result.get("stderr"):
                display_data["errors"].append(f"PowerShell monitor fallback error: {monitor_result.get('stderr')}")

        # Display drivers
        if not display_data["display_drivers"]:
            driver_cmd = (
                "Get-CimInstance Win32_PnPSignedDriver | "
                "Where-Object { $_.DeviceClass -eq 'DISPLAY' } | "
                "Select-Object DeviceName,DeviceID,DriverVersion,DriverDate,Manufacturer,DriverProviderName,IsSigned | "
                "ConvertTo-Json -Depth 4"
            )
            driver_result = self.run_terminal_command(driver_cmd, timeout=20)
            if driver_result.get("success"):
                for driver in self._parse_json_output(driver_result.get("stdout", "")):
                    display_data["display_drivers"].append({
                        "device_name": driver.get("DeviceName"),
                        "device_id": driver.get("DeviceID"),
                        "driver_version": driver.get("DriverVersion"),
                        "driver_date": str(driver.get("DriverDate")) if driver.get("DriverDate") else None,
                        "manufacturer": driver.get("Manufacturer"),
                        "provider": driver.get("DriverProviderName"),
                        "is_signed": driver.get("IsSigned"),
                        "source": "powershell_cim"
                    })
            elif driver_result.get("stderr"):
                display_data["errors"].append(f"PowerShell display-driver fallback error: {driver_result.get('stderr')}")

    def identify_issue_type(self, user_input):
        """Identify the type of issue based on user input"""
        user_input_lower = user_input.lower()
        
        # Define keyword mappings for different issue types
        issue_types = {
            'display': ['screen', 'display', 'monitor', 'flicker', 'black screen', 'graphics', 'video', 'visual', 'resolution', 'brightness'],
            'performance': ['slow', 'lag', 'freeze', 'hang', 'performance', 'speed', 'fast', 'cpu', 'memory', 'ram'],
            'network': ['wifi', 'internet', 'network', 'connection', 'ethernet', 'connect', 'online', 'download', 'upload'],
            'audio': ['sound', 'audio', 'speaker', 'microphone', 'headphone', 'music', 'volume', 'noise'],
            'storage': ['disk', 'drive', 'storage', 'hard drive', 'ssd', 'hdd', 'space', 'file'],
            'hardware': ['usb', 'port', 'device', 'keyboard', 'mouse', 'printer', 'hardware']
        }
        
        detected_types = []
        for issue_type, keywords in issue_types.items():
            if any(keyword in user_input_lower for keyword in keywords):
                detected_types.append(issue_type)
        
        return detected_types if detected_types else ['general']

    def get_system_health(self, issue_description="general"):
        """Get comprehensive system health data based on issue type"""
        issue_types = self.identify_issue_type(issue_description)
        
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "issue_types_detected": issue_types,
            "user_description": issue_description,
            "system_info": self.get_system_info(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "network": self.get_network_info(),
            "processes": self.get_top_processes(),
            "issue_specific": {},
            "advanced_sensors": None  # Will contain HWiNFO-level sensor data
        }
        
        # Collect advanced sensor data if available
        if self.advanced_telemetry:
            try:
                print("📊 Collecting advanced sensor telemetry (LibreHardwareMonitor + NVML)...")
                health_data["advanced_sensors"] = self.advanced_telemetry.get_all_sensors()
                print("✅ Advanced sensor data collected successfully")
            except Exception as e:
                print(f"⚠️ Advanced sensor collection failed: {str(e)}")

        # Collect issue-specific telemetry
        for issue_type in issue_types:
            if issue_type == 'display':
                health_data["issue_specific"]["display"] = self.get_display_info()
            elif issue_type == 'network':
                health_data["issue_specific"]["network_detailed"] = self.get_detailed_network_info()
            elif issue_type == 'audio':
                health_data["issue_specific"]["audio"] = self.get_audio_info()
            elif issue_type == 'storage':
                health_data["issue_specific"]["storage_detailed"] = self.get_detailed_storage_info()
            elif issue_type == 'hardware':
                health_data["issue_specific"]["usb_devices"] = self.get_usb_info()

        return health_data

    def get_display_info(self):
        """Get detailed display/screen information with advanced diagnostics"""
        display_data = {
            "monitors": [],
            "graphics_cards": [],
            "display_drivers": [],
            "display_settings": {},
            "display_diagnostics": {},
            "errors": []
        }

        try:
            # Advanced Windows display diagnostics
            if self.wmi_conn:
                # Monitor information with detailed specs
                for monitor in self.wmi_conn.Win32_DesktopMonitor():
                    monitor_info = {
                        "name": monitor.Name,
                        "device_id": monitor.DeviceID,
                        "pnp_device_id": monitor.PNPDeviceID,
                        "screen_width": monitor.ScreenWidth,
                        "screen_height": monitor.ScreenHeight,
                        "status": monitor.Status,
                        "availability": monitor.Availability,
                        "monitor_type": monitor.MonitorType,
                    }
                    display_data["monitors"].append(monitor_info)

                # Graphics card information with detailed specs
                for gpu in self.wmi_conn.Win32_VideoController():
                    gpu_info = {
                        "name": gpu.Name,
                        "device_id": gpu.DeviceID,
                        "adapter_ram": gpu.AdapterRAM,
                        "driver_version": gpu.DriverVersion,
                        "driver_date": str(gpu.DriverDate),
                        "status": gpu.Status,
                        "current_refresh_rate": gpu.CurrentRefreshRate,
                        "current_horizontal_resolution": gpu.CurrentHorizontalResolution,
                        "current_vertical_resolution": gpu.CurrentVerticalResolution,
                    }
                    display_data["graphics_cards"].append(gpu_info)

        except Exception as e:
            display_data["errors"].append(f"WMI display info error: {str(e)}")

        # Enhanced GPU utilization using GPUtil
        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                for i, gpu in enumerate(gpus):
                    gpu_util = {
                        "id": gpu.id,
                        "name": gpu.name,
                        "load": gpu.load * 100,
                        "memory_free": gpu.memoryFree,
                        "memory_used": gpu.memoryUsed,
                        "memory_total": gpu.memoryTotal,
                        "temperature": gpu.temperature,
                    }
                    if i < len(display_data["graphics_cards"]):
                        display_data["graphics_cards"][i].update(gpu_util)
                    else:
                        display_data["graphics_cards"].append(gpu_util)
            except Exception as e:
                display_data["errors"].append(f"GPU utilization error: {str(e)}")

        # Fallback detection path for systems where WMI/GPUtil returns empty sets.
        self._load_display_info_from_powershell(display_data)

        return display_data

    def get_system_info(self):
        """Get basic system information"""
        try:
            return {
                "platform": platform.platform(),
                "system": platform.system(),
                "processor": platform.processor(),
                "architecture": platform.architecture(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
                "hostname": socket.gethostname(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "uptime_seconds": time.time() - psutil.boot_time()
            }
        except Exception as e:
            return {"error": str(e)}

    def get_cpu_info(self):
        """Get detailed CPU information and diagnostics"""
        try:
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(logical=True),
                "usage_per_core": psutil.cpu_percent(percpu=True, interval=1),
                "total_usage": psutil.cpu_percent(interval=1),
            }
            
            # Add frequency if available
            freq = psutil.cpu_freq()
            if freq:
                cpu_info.update({
                    "current_frequency": freq.current,
                    "min_frequency": freq.min,
                    "max_frequency": freq.max
                })
            
            return cpu_info
        except Exception as e:
            return {"error": str(e)}

    def get_memory_info(self):
        """Get detailed memory information and diagnostics"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percentage": memory.percent,
                "free": memory.free,
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_free": swap.free,
                "swap_percentage": swap.percent,
            }
            
            return memory_info
        except Exception as e:
            return {"error": str(e)}

    def get_disk_info(self):
        """Get disk information"""
        try:
            disk_info = []
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    disk_usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "file_system": partition.fstype,
                        "total": disk_usage.total,
                        "used": disk_usage.used,
                        "free": disk_usage.free,
                        "percentage": (disk_usage.used / disk_usage.total) * 100
                    })
                except PermissionError:
                    continue
            
            return disk_info
        except Exception as e:
            return {"error": str(e)}

    def get_network_info(self):
        """Get basic network information"""
        try:
            network_stats = psutil.net_io_counters()
            return {
                "bytes_sent": network_stats.bytes_sent,
                "bytes_recv": network_stats.bytes_recv,
                "packets_sent": network_stats.packets_sent,
                "packets_recv": network_stats.packets_recv,
                "errors_in": network_stats.errin,
                "errors_out": network_stats.errout,
                "dropin": network_stats.dropin if hasattr(network_stats, 'dropin') else 0,
                "dropout": network_stats.dropout if hasattr(network_stats, 'dropout') else 0,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_top_processes(self, limit=10):
        """Get top processes by CPU usage"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            return processes[:limit]
        except Exception as e:
            return {"error": str(e)}

    def get_audio_info(self):
        """Get comprehensive audio device and configuration information"""
        audio_data = {"devices": [], "errors": []}
        
        if self.wmi_conn:
            try:
                # Get sound devices
                for device in self.wmi_conn.Win32_SoundDevice():
                    device_info = {
                        "name": device.Name,
                        "description": device.Description,
                        "manufacturer": device.Manufacturer,
                        "device_id": device.DeviceID,
                        "status": device.Status,
                    }
                    audio_data["devices"].append(device_info)
            except Exception as e:
                audio_data["errors"].append(f"Audio device error: {str(e)}")
        
        return audio_data

    def get_detailed_network_info(self):
        """Get comprehensive network adapter and connectivity information"""
        network_data = {"adapters": [], "connections": [], "errors": []}
        
        try:
            # Basic network connections
            connections = psutil.net_connections()
            for conn in connections[:20]:
                network_data["connections"].append({
                    "family": str(conn.family),
                    "type": str(conn.type),
                    "local_address": conn.laddr,
                    "remote_address": conn.raddr,
                    "status": conn.status,
                    "pid": conn.pid
                })
        except Exception as e:
            network_data["errors"].append(f"Network connections error: {str(e)}")
        
        return network_data

    def get_detailed_storage_info(self):
        """Get comprehensive storage device information and health diagnostics"""
        storage_data = {"drives": [], "partitions": [], "errors": []}
        
        if self.wmi_conn:
            try:
                # Get physical disk drives
                for drive in self.wmi_conn.Win32_DiskDrive():
                    drive_info = {
                        "model": drive.Model,
                        "size": drive.Size,
                        "interface_type": drive.InterfaceType,
                        "media_type": drive.MediaType,
                        "status": drive.Status,
                    }
                    storage_data["drives"].append(drive_info)
            except Exception as e:
                storage_data["errors"].append(f"Storage device error: {str(e)}")
        
        return storage_data

    def get_usb_info(self):
        """Get USB device information"""
        usb_data = {"devices": [], "errors": []}
        
        if self.wmi_conn:
            try:
                for usb_device in self.wmi_conn.Win32_USBControllerDevice():
                    device_info = {
                        "dependent": str(usb_device.Dependent),
                        "antecedent": str(usb_device.Antecedent)
                    }
                    usb_data["devices"].append(device_info)
            except Exception as e:
                usb_data["errors"].append(f"USB device error: {str(e)}")
        
        return usb_data
