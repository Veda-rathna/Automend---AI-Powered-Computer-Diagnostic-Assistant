"""
Test script for PC Compatibility Checker endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_scan_hardware():
    """Test hardware scanning endpoint"""
    print("\n" + "="*50)
    print("Testing Hardware Scan Endpoint")
    print("="*50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/compatibility/scan/")
        data = response.json()
        
        if data.get('success'):
            print("✅ Hardware scan successful!")
            print(f"\nDetected Hardware:")
            print(f"  CPU: {data['hardware_specs']['cpu'].get('model', 'Unknown')}")
            print(f"  RAM: {data['hardware_specs']['ram'].get('total_gb', 0)} GB")
            
            # Safely access GPU info
            gpu_list = data['hardware_specs'].get('gpu', [])
            if gpu_list and len(gpu_list) > 0:
                print(f"  GPU: {gpu_list[0].get('model', 'Unknown')}")
            else:
                print(f"  GPU: None")
            
            if data.get('missing_fields'):
                print(f"\n⚠️ Missing fields that need user input:")
                for field in data['missing_fields']:
                    print(f"  - {field}")
            
            print(f"\n✅ Power Requirements:")
            power = data['hardware_specs'].get('power_requirements', {})
            print(f"  Estimated TDP: {power.get('estimated_tdp_watts')}W")
            print(f"  Recommended PSU: {power.get('recommended_psu_min')}-{power.get('recommended_psu_ideal')}W")
            
            return data['hardware_specs']
        else:
            print(f"❌ Error: {data.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to connect to backend: {str(e)}")
        print("   Make sure the Django server is running on port 8000")
        return None


def test_compatibility_check(current_system=None):
    """Test compatibility checking endpoint"""
    print("\n" + "="*50)
    print("Testing Compatibility Check Endpoint")
    print("="*50)
    
    test_upgrade = {
        "description": "NVIDIA RTX 4070 Ti"
    }
    
    payload = {
        "proposed_upgrade": test_upgrade,
    }
    
    if current_system:
        payload["current_system"] = current_system
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/compatibility/check/",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        data = response.json()
        
        if data.get('success'):
            print(f"✅ Compatibility check completed!")
            print(f"\nUpgrade: {test_upgrade['description']}")
            print(f"Compatible: {'✅ YES' if data.get('compatible') else '⚠️ ISSUES FOUND'}")
            print(f"Warnings: {'⚠️ YES' if data.get('has_warnings') else '✅ NO'}")
            print(f"\nAI Analysis Preview:")
            analysis = data.get('analysis', '')
            preview = analysis[:300] + "..." if len(analysis) > 300 else analysis
            print(preview)
            print(f"\nPowered by: {data.get('llm_provider', 'unknown').upper()}")
        else:
            print(f"❌ Error: {data.get('error')}")
            
    except Exception as e:
        print(f"❌ Failed to check compatibility: {str(e)}")


def test_recommendations(current_system=None):
    """Test upgrade recommendations endpoint"""
    print("\n" + "="*50)
    print("Testing Upgrade Recommendations Endpoint")
    print("="*50)
    
    payload = {
        "budget": 40000,
        "goal": "gaming"
    }
    
    if current_system:
        payload["current_system"] = current_system
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/compatibility/recommendations/",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        data = response.json()
        
        if data.get('success'):
            print(f"✅ Recommendations generated!")
            print(f"\nBudget: ₹{data.get('budget'):,.0f} INR")
            print(f"Goal: {data.get('goal')}")
            print(f"\nRecommendations Preview:")
            recommendations = data.get('recommendations', '')
            preview = recommendations[:300] + "..." if len(recommendations) > 300 else recommendations
            print(preview)
            print(f"\nPowered by: {data.get('llm_provider', 'unknown').upper()}")
        else:
            print(f"❌ Error: {data.get('error')}")
            
    except Exception as e:
        print(f"❌ Failed to get recommendations: {str(e)}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PC Compatibility Checker - Backend Test Suite")
    print("="*60)
    print("\nTesting backend endpoints at:", BASE_URL)
    print("Make sure Django server is running (python manage.py runserver)")
    
    # Test 1: Scan Hardware
    current_system = test_scan_hardware()
    
    # Test 2: Check Compatibility
    test_compatibility_check(current_system)
    
    # Test 3: Get Recommendations
    test_recommendations(current_system)
    
    print("\n" + "="*60)
    print("Testing Complete!")
    print("="*60)
    print("\nNext Steps:")
    print("1. Review the results above")
    print("2. Test the frontend at http://localhost:3000/compatibility-checker")
    print("3. Try different upgrade scenarios")
    print("\n")


if __name__ == "__main__":
    main()
