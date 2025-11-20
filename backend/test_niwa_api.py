"""
Test script for NIWA DataHub API integration

NOTE: NIWA DataHub is DISABLED by default (circuit breaker active).
The API returns 404 without valid credentials. To enable:
1. Set NIWA_ENABLED=true in environment
2. Set NIWA_CUSTOMER_ID and NIWA_API_KEY from https://data.niwa.co.nz/

For regional flow data, use TRC Hilltop SOS instead (see drought_risk.py)
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from niwa_service import list_niwa_data_files, NIWA_ENABLED
from drought_risk import calculate_drought_risk

async def test_niwa_api():
    """Test NIWA DataHub API connection"""
    print("=" * 60)
    print("NIWA DataHub API Test")
    print("=" * 60)

    # Check circuit breaker status
    if not NIWA_ENABLED:
        print("\n⚠️  NIWA DataHub is DISABLED (circuit breaker active)")
        print("   To enable, set NIWA_ENABLED=true in environment")
        print("   Skipping NIWA API test...")
    else:
        print("\n1. Testing NIWA DataHub file listing...")
        try:
            niwa_data = await list_niwa_data_files()

            if niwa_data:
                print(f"✅ NIWA API connection successful!")
                print(f"   Total files available: {len(niwa_data.get('data', []))}")

                files = niwa_data.get('data', [])
                if files:
                    print(f"\n   First 5 files:")
                    for i, file in enumerate(files[:5], 1):
                        print(f"   {i}. {file.get('fileName', 'Unknown')} (ID: {file.get('id', 'Unknown')})")
            else:
                print("⚠️  NIWA API returned no data")
                print("   This could mean:")
                print("   - No files available in your account")
                print("   - API credentials need verification")

        except Exception as e:
            print(f"❌ NIWA API test failed: {e}")
            print("\n   Common issues:")
            print("   - Check NIWA_CUSTOMER_ID is correct")
            print("   - Check NIWA_API_KEY is valid")
            print("   - Ensure you have access to rainfall data products")

    print("\n" + "=" * 60)
    print("\n2. Testing full drought risk calculation (with NIWA integration)...")
    try:
        result = await calculate_drought_risk("Canterbury")
        print(f"✅ Drought risk calculated successfully!")
        print(f"   Location: {result.get('location')}")
        print(f"   Risk Level: {result.get('risk_level')}")
        print(f"   Risk Score: {result.get('risk_score')}/10")
        print(f"   NIWA Data Available: {result.get('factors', {}).get('niwa_data_available', False)}")
    except Exception as e:
        print(f"❌ Drought risk calculation failed: {e}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_niwa_api())
