"""
debug_api_key.py

This script checks exactly what API key is being loaded
and why it might not be working.
"""

import os
import sys
from pathlib import Path

print("=" * 70)
print("API KEY DEBUG SCRIPT")
print("=" * 70)

# Check 1: Current working directory
print("\n1. CURRENT WORKING DIRECTORY")
print(f"   {os.getcwd()}")

# Check 2: Check if .env file exists in current directory
print("\n2. CHECKING .env FILE LOCATION")
env_file = Path(".env")
if env_file.exists():
    print(f"   ✅ .env file found at: {env_file.absolute()}")
    
    # Read .env file content
    with open(env_file, 'r') as f:
        content = f.read()
        print(f"\n   .env file content:")
        print("   " + "-" * 60)
        for line in content.split('\n'):
            if line.strip() and not line.startswith('#'):
                # Mask the API key for security
                if 'OPENAI_API_KEY' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        key = parts[1].strip()
                        if len(key) > 10:
                            masked = f"{key[:7]}...{key[-4:]}"
                            print(f"   OPENAI_API_KEY={masked}")
                        else:
                            print(f"   ⚠️  OPENAI_API_KEY is too short: {line}")
                    else:
                        print(f"   ⚠️  Invalid format: {line}")
                else:
                    print(f"   {line}")
    print("   " + "-" * 60)
else:
    print(f"   ❌ .env file NOT found in current directory!")
    print(f"   Looking for: {env_file.absolute()}")

# Check 3: Try loading with python-dotenv
print("\n3. LOADING WITH python-dotenv")
try:
    from dotenv import load_dotenv
    
    # Load from current directory
    result = load_dotenv()
    print(f"   load_dotenv() returned: {result}")
    
    # Try to get the key
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key:
        print(f"   ✅ API Key loaded successfully")
        print(f"   Length: {len(api_key)} characters")
        print(f"   Starts with: {api_key[:10]}...")
        print(f"   Ends with: ...{api_key[-10:]}")
        
        # Check if it looks valid
        if api_key.startswith("sk-proj-") or api_key.startswith("sk-"):
            print(f"   ✅ Key format looks correct")
        else:
            print(f"   ⚠️  Key doesn't start with 'sk-proj-' or 'sk-'")
            print(f"   First 20 chars: {api_key[:20]}")
        
        # Check for common issues
        if ' ' in api_key:
            print(f"   ❌ WARNING: Key contains spaces!")
        if '"' in api_key or "'" in api_key:
            print(f"   ❌ WARNING: Key contains quotes!")
        if '\n' in api_key or '\r' in api_key:
            print(f"   ❌ WARNING: Key contains newline characters!")
            
    else:
        print(f"   ❌ API Key is None (not loaded)")
        print(f"   Check if OPENAI_API_KEY is set in .env file")
        
except ImportError:
    print(f"   ❌ python-dotenv not installed")
    print(f"   Install with: pip install python-dotenv")

# Check 4: Try loading from app.config
print("\n4. CHECKING app.config")
try:
    # Add app directory to path
    sys.path.insert(0, os.path.join(os.getcwd(), 'app'))
    
    from config import OPENAI_API_KEY
    
    if OPENAI_API_KEY:
        print(f"   ✅ API Key loaded from config.py")
        print(f"   Length: {len(OPENAI_API_KEY)} characters")
        print(f"   Starts with: {OPENAI_API_KEY[:10]}...")
        print(f"   Ends with: ...{OPENAI_API_KEY[-10:]}")
        
        # Compare with direct load
        direct_key = os.getenv("OPENAI_API_KEY")
        if direct_key == OPENAI_API_KEY:
            print(f"   ✅ Matches direct load from .env")
        else:
            print(f"   ⚠️  Different from direct load!")
            if direct_key:
                print(f"      Direct: {direct_key[:10]}...{direct_key[-10:]}")
            print(f"      Config: {OPENAI_API_KEY[:10]}...{OPENAI_API_KEY[-10:]}")
    else:
        print(f"   ❌ OPENAI_API_KEY is None in config.py")
        
except ImportError as e:
    print(f"   ❌ Could not import config: {e}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check 5: Test actual OpenAI connection
print("\n5. TESTING OPENAI CONNECTION")
try:
    from openai import OpenAI
    
    # Get key from config or environment
    test_key = None
    try:
        from config import OPENAI_API_KEY
        test_key = OPENAI_API_KEY
    except:
        test_key = os.getenv("OPENAI_API_KEY")
    
    if test_key:
        print(f"   Testing with key: {test_key[:10]}...{test_key[-4:]}")
        
        try:
            client = OpenAI(api_key=test_key)
            print(f"   ✅ OpenAI client created successfully")
            
            # Try a simple API call (list models)
            print(f"   Testing API connection...")
            models = client.models.list()
            print(f"   ✅ API CONNECTION SUCCESSFUL!")
            print(f"   Your API key is VALID and WORKING!")
            
        except Exception as e:
            print(f"   ❌ OpenAI API Error: {e}")
            error_str = str(e)
            if "401" in error_str:
                print(f"   ❌ ERROR 401: Invalid API Key")
                print(f"   The key is being loaded but is INVALID")
            elif "429" in error_str:
                print(f"   ⚠️  ERROR 429: Rate limit or quota exceeded")
            else:
                print(f"   Unknown error")
    else:
        print(f"   ❌ No API key available for testing")
        
except ImportError:
    print(f"   ❌ openai library not installed")
    print(f"   Install with: pip install openai")

# Check 6: Compare with what other person has
print("\n6. COMPARISON CHECKLIST")
print("   Ask the other person to run this script and compare:")
print("   - .env file location")
print("   - API key length (should be same)")
print("   - API key first 10 and last 10 characters (should be same)")
print("   - Whether OpenAI client creation succeeds")

print("\n" + "=" * 70)
print("DEBUG COMPLETE")
print("=" * 70)

# Final recommendations
print("\n📋 RECOMMENDATIONS:")
print("\nIf API key is loading but shows as invalid:")
print("  1. Copy the EXACT key the other person is using")
print("  2. Delete your entire .env file")
print("  3. Create fresh .env file")
print("  4. Paste: OPENAI_API_KEY=sk-proj-xxxxx")
print("  5. Save with NO extra spaces, NO quotes")
print("  6. Run this script again")
print("  7. Restart your server")

print("\nIf .env file is not being found:")
print("  1. Make sure .env is in same directory as run.py")
print("  2. Check file name is exactly '.env' (not '.env.txt')")
print("  3. Make sure no spaces in filename")

print("\nIf key loads but test shows 401 error:")
print("  1. The key itself is invalid/expired")
print("  2. Get fresh key from: https://platform.openai.com/api-keys")
print("  3. The other person might be using different key")

print("\n" + "=" * 70)