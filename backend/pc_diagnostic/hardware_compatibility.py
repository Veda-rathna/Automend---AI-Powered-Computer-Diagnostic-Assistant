"""
Hardware Compatibility Checker Module
Detects detailed hardware specifications and checks upgrade compatibility
"""

import platform
import subprocess
import json
import re
from typing import Dict, Any, Optional, List
import psutil

class HardwareCompatibilityChecker:
    """Comprehensive hardware detection and compatibility checking"""
    
    def __init__(self):
        self.system_info = {}
        
    def get_detailed_hardware_specs(self) -> Dict[str, Any]:
        """Collect comprehensive hardware specifications for compatibility checking"""
        
        specs = {
            'cpu': self._get_cpu_details(),
            'motherboard': self._get_motherboard_details(),
            'ram': self._get_ram_details(),
            'gpu': self._get_gpu_details(),
            'storage': self._get_storage_details(),
            'psu': {
                'wattage': None,  # User must input
                'efficiency': None,  # User must input
                'manufacturer': None,
            },
            'case': {
                'form_factor': None,  # User must input
                'gpu_clearance_mm': None,  # User must input
                'max_cpu_cooler_height_mm': None,
            },
            'os': self._get_os_details(),
        }
        
        return specs
    
    def _get_cpu_details(self) -> Dict[str, Any]:
        """Get detailed CPU information"""
        cpu_info = {
            'model': platform.processor(),
            'architecture': platform.machine(),
            'cores': psutil.cpu_count(logical=False),
            'threads': psutil.cpu_count(logical=True),
            'socket': None,
            'manufacturer': None,
            'generation': None,
            'base_clock_ghz': None,
            'tdp_watts': None,
        }
        
        # Try to get more details on Windows
        if platform.system() == 'Windows':
            try:
                # Get CPU name using WMIC
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'Name', '/value'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Name=' in line:
                            cpu_name = line.split('=')[1].strip()
                            cpu_info['model'] = cpu_name
                            
                            # Extract manufacturer
                            if 'Intel' in cpu_name:
                                cpu_info['manufacturer'] = 'Intel'
                                cpu_info['socket'] = self._detect_intel_socket(cpu_name)
                            elif 'AMD' in cpu_name:
                                cpu_info['manufacturer'] = 'AMD'
                                cpu_info['socket'] = self._detect_amd_socket(cpu_name)
                
                # Get max clock speed
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'MaxClockSpeed', '/value'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'MaxClockSpeed=' in line:
                            mhz = line.split('=')[1].strip()
                            if mhz.isdigit():
                                cpu_info['base_clock_ghz'] = round(int(mhz) / 1000, 2)
                                
            except Exception as e:
                print(f"Error getting CPU details: {str(e)}")
        
        return cpu_info
    
    def _detect_intel_socket(self, cpu_name: str) -> Optional[str]:
        """Detect Intel CPU socket from model name"""
        # Intel socket detection patterns
        if re.search(r'i[3579]-1[0-4]\d{3}', cpu_name):  # 10th-14th gen
            return 'LGA1700' if re.search(r'i[3579]-1[2-4]\d{3}', cpu_name) else 'LGA1200'
        elif re.search(r'i[3579]-[789]\d{3}', cpu_name):  # 7th-9th gen
            return 'LGA1151'
        elif re.search(r'i[3579]-[456]\d{3}', cpu_name):  # 4th-6th gen
            return 'LGA1150'
        return None
    
    def _detect_amd_socket(self, cpu_name: str) -> Optional[str]:
        """Detect AMD CPU socket from model name"""
        # AMD socket detection patterns
        if 'Ryzen' in cpu_name:
            if re.search(r'[79]\d{3}', cpu_name):  # Ryzen 7000/9000 series
                return 'AM5'
            else:  # Older Ryzen
                return 'AM4'
        elif 'Threadripper' in cpu_name:
            return 'sTRX4'
        return None
    
    def _get_motherboard_details(self) -> Dict[str, Any]:
        """Get motherboard information"""
        mb_info = {
            'manufacturer': None,
            'model': None,
            'chipset': None,
            'form_factor': None,
            'ram_slots': None,
            'max_ram_gb': None,
            'ram_type_supported': [],  # e.g., ['DDR4', 'DDR5']
            'pcie_slots': {
                'pcie_x16': None,
                'pcie_x8': None,
                'pcie_x4': None,
                'pcie_x1': None,
            },
            'm2_slots': None,
            'sata_ports': None,
            'bios_version': None,
        }
        
        if platform.system() == 'Windows':
            try:
                # Get motherboard manufacturer
                result = subprocess.run(
                    ['wmic', 'baseboard', 'get', 'Manufacturer', '/value'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Manufacturer=' in line:
                            mb_info['manufacturer'] = line.split('=')[1].strip()
                
                # Get motherboard model/product
                result = subprocess.run(
                    ['wmic', 'baseboard', 'get', 'Product', '/value'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Product=' in line:
                            mb_info['model'] = line.split('=')[1].strip()
                
                # Get BIOS version
                result = subprocess.run(
                    ['wmic', 'bios', 'get', 'SMBIOSBIOSVersion', '/value'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'SMBIOSBIOSVersion=' in line:
                            mb_info['bios_version'] = line.split('=')[1].strip()
                            
            except Exception as e:
                print(f"Error getting motherboard details: {str(e)}")
        
        return mb_info
    
    def _get_ram_details(self) -> Dict[str, Any]:
        """Get RAM information"""
        memory = psutil.virtual_memory()
        
        ram_info = {
            'total_gb': round(memory.total / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'percentage_used': memory.percent,
            'type': None,  # DDR4, DDR5, etc.
            'speed_mhz': None,
            'slots_total': None,
            'slots_used': None,
            'modules': [],
        }
        
        if platform.system() == 'Windows':
            try:
                # Get RAM speed
                result = subprocess.run(
                    ['wmic', 'memorychip', 'get', 'Speed', '/value'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    speeds = []
                    for line in result.stdout.split('\n'):
                        if 'Speed=' in line:
                            speed = line.split('=')[1].strip()
                            if speed.isdigit():
                                speeds.append(int(speed))
                    if speeds:
                        ram_info['speed_mhz'] = max(speeds)
                
                # Get RAM capacity per module
                result = subprocess.run(
                    ['wmic', 'memorychip', 'get', 'Capacity', '/value'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    capacities = []
                    for line in result.stdout.split('\n'):
                        if 'Capacity=' in line:
                            capacity = line.split('=')[1].strip()
                            if capacity.isdigit():
                                capacities.append(int(capacity))
                    if capacities:
                        ram_info['slots_used'] = len(capacities)
                        ram_info['modules'] = [
                            {'size_gb': round(cap / (1024**3), 2)} for cap in capacities
                        ]
                
                # Get RAM type (MemoryType code)
                result = subprocess.run(
                    ['wmic', 'memorychip', 'get', 'SMBIOSMemoryType', '/value'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'SMBIOSMemoryType=' in line:
                            mem_type = line.split('=')[1].strip()
                            # Decode memory type (simplified)
                            type_map = {
                                '26': 'DDR4',
                                '34': 'DDR5',
                                '24': 'DDR3',
                            }
                            ram_info['type'] = type_map.get(mem_type, f'Type_{mem_type}')
                            break
                            
            except Exception as e:
                print(f"Error getting RAM details: {str(e)}")
        
        return ram_info
    
    def _get_gpu_details(self) -> List[Dict[str, Any]]:
        """Get GPU information"""
        gpus = []
        
        if platform.system() == 'Windows':
            try:
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 
                     'Name,AdapterRAM,DriverVersion', '/format:list'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    gpu_data = {}
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            if key == 'Name' and value:
                                if gpu_data:
                                    gpus.append(gpu_data)
                                gpu_data = {
                                    'model': value,
                                    'vram_gb': None,
                                    'driver_version': None,
                                    'manufacturer': None,
                                    'pcie_version': None,
                                    'tdp_watts': None,
                                    'length_mm': None,
                                }
                                
                                # Detect manufacturer
                                if 'NVIDIA' in value or 'GeForce' in value or 'RTX' in value or 'GTX' in value:
                                    gpu_data['manufacturer'] = 'NVIDIA'
                                elif 'AMD' in value or 'Radeon' in value:
                                    gpu_data['manufacturer'] = 'AMD'
                                elif 'Intel' in value:
                                    gpu_data['manufacturer'] = 'Intel'
                                    
                            elif key == 'AdapterRAM' and value:
                                try:
                                    vram_bytes = int(value)
                                    gpu_data['vram_gb'] = round(vram_bytes / (1024**3), 2)
                                except:
                                    pass
                            elif key == 'DriverVersion' and value:
                                gpu_data['driver_version'] = value
                    
                    if gpu_data:
                        gpus.append(gpu_data)
                        
            except Exception as e:
                print(f"Error getting GPU details: {str(e)}")
        
        return gpus if gpus else [{'model': 'Integrated Graphics', 'manufacturer': 'Unknown'}]
    
    def _get_storage_details(self) -> List[Dict[str, Any]]:
        """Get storage device information"""
        storage_devices = []
        
        # Get partition info
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                storage_devices.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'filesystem': partition.fstype,
                    'total_gb': round(usage.total / (1024**3), 2),
                    'used_gb': round(usage.used / (1024**3), 2),
                    'free_gb': round(usage.free / (1024**3), 2),
                    'percentage_used': usage.percent,
                })
            except PermissionError:
                continue
        
        # Try to get physical disk info on Windows
        if platform.system() == 'Windows':
            try:
                result = subprocess.run(
                    ['wmic', 'diskdrive', 'get', 'Model,Size,InterfaceType', '/format:list'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    disk_data = {}
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            if key == 'Model' and value:
                                if disk_data:
                                    storage_devices.append(disk_data)
                                disk_data = {
                                    'model': value,
                                    'interface': None,
                                    'capacity_gb': None,
                                    'type': 'Unknown',
                                }
                                # Detect SSD vs HDD
                                if 'SSD' in value.upper() or 'NVME' in value.upper():
                                    disk_data['type'] = 'SSD'
                                elif 'HDD' in value.upper():
                                    disk_data['type'] = 'HDD'
                                    
                            elif key == 'InterfaceType' and value:
                                disk_data['interface'] = value
                            elif key == 'Size' and value:
                                try:
                                    size_bytes = int(value)
                                    disk_data['capacity_gb'] = round(size_bytes / (1024**3), 2)
                                except:
                                    pass
                    
                    if disk_data:
                        storage_devices.append(disk_data)
                        
            except Exception as e:
                print(f"Error getting physical disk details: {str(e)}")
        
        return storage_devices
    
    def _get_os_details(self) -> Dict[str, Any]:
        """Get operating system information"""
        return {
            'name': platform.system(),
            'version': platform.version(),
            'release': platform.release(),
            'architecture': platform.machine(),
        }
    
    def calculate_power_requirements(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate estimated power requirements for a system configuration"""
        
        # Rough TDP estimates (watts)
        tdp_estimates = {
            'cpu': 125,  # Default mid-range CPU
            'gpu': 250,  # Default mid-range GPU
            'motherboard': 80,
            'ram_per_stick': 3,
            'storage_ssd': 5,
            'storage_hdd': 10,
            'fans': 5,
            'other': 50,
        }
        
        total_tdp = 0
        breakdown = {}
        
        # CPU
        cpu_tdp = components.get('cpu', {}).get('tdp_watts') or tdp_estimates['cpu']
        total_tdp += cpu_tdp
        breakdown['cpu'] = cpu_tdp
        
        # GPU
        gpus = components.get('gpu', [])
        if isinstance(gpus, list) and gpus:
            gpu_tdp = gpus[0].get('tdp_watts') or tdp_estimates['gpu']
        else:
            gpu_tdp = tdp_estimates['gpu']
        total_tdp += gpu_tdp
        breakdown['gpu'] = gpu_tdp
        
        # RAM
        ram = components.get('ram', {})
        ram_sticks = ram.get('slots_used') or 2
        ram_tdp = ram_sticks * tdp_estimates['ram_per_stick']
        total_tdp += ram_tdp
        breakdown['ram'] = ram_tdp
        
        # Storage
        storage = components.get('storage', [])
        storage_tdp = len(storage) * tdp_estimates['storage_ssd']
        total_tdp += storage_tdp
        breakdown['storage'] = storage_tdp
        
        # Overhead
        overhead = tdp_estimates['motherboard'] + tdp_estimates['fans'] + tdp_estimates['other']
        total_tdp += overhead
        breakdown['overhead'] = overhead
        
        # Recommended PSU (add 20-30% headroom)
        recommended_min = int(total_tdp * 1.25)
        recommended_ideal = int(total_tdp * 1.35)
        
        return {
            'estimated_tdp_watts': total_tdp,
            'breakdown': breakdown,
            'recommended_psu_min': recommended_min,
            'recommended_psu_ideal': recommended_ideal,
            'efficiency_recommendation': '80+ Gold or better',
        }
