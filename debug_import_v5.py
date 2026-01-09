
import sys
import os

# Ensure V9 root is in path
sys.path.append(os.getcwd())

print("Testing import of mega.engines.ms17_v5_engine...")
try:
    import mega.engines.ms17_v5_engine
    print("SUCCESS: Imported mega.engines.ms17_v5_engine")
    if hasattr(mega.engines.ms17_v5_engine, 'gerar'):
        print("SUCCESS: 'gerar' function found.")
    else:
        print("FAILURE: 'gerar' function NOT found.")
except Exception as e:
    print(f"FAILURE: Could not import. Error: {e}")
    import traceback
    traceback.print_exc()
