import pg8000
import json
import sys

def parse_n8n_json(raw_str):
    try:
        data = json.loads(raw_str)
        if not isinstance(data, list) or len(data) < 2:
            return "Invalid n8n format"
            
        # The last element in the array is usually the string lookup table
        lookup = data[-1]
        if not isinstance(lookup, list):
            # Check other elements
            for item in reversed(data):
                if isinstance(item, list):
                    lookup = item
                    break
            else:
                return "Lookup table not found"
                
        def resolve(val):
            if isinstance(val, str) and val.isdigit():
                idx = int(val)
                if idx < len(lookup):
                    return lookup[idx]
            elif isinstance(val, dict):
                return {k: resolve(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [resolve(v) for v in val]
            return val

        # Resolve the entire list
        resolved_list = [resolve(item) for item in data]
        return resolved_list
    except Exception as e:
        return f"Resolution error: {e}"

def print_resolved_error():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='n8n_db'
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ed.data, ee.status
            FROM execution_data ed
            JOIN execution_entity ee ON ed."executionId" = ee.id
            WHERE ee.status = 'error'
            ORDER BY ed."executionId" DESC
            LIMIT 1;
        """)
        row = cursor.fetchone()
        if row:
            raw_str, status = row
            resolved = parse_n8n_json(raw_str)
            
            # Print the resolved error details
            print("Resolved Status:", status)
            found_error = False
            
            # Search for error messages in the resolved structure
            if isinstance(resolved, list):
                for item in resolved:
                    if isinstance(item, dict):
                        # Look for error keys
                        if 'error' in item and item['error']:
                            print("\nFound error object:")
                            print(json.dumps(item['error'], indent=2))
                            found_error = True
                        if 'runData' in item and item['runData']:
                            for node_name, runs in item['runData'].items():
                                for r in runs:
                                    if 'error' in r and r['error']:
                                        print(f"\nNode '{node_name}' error:")
                                        print(json.dumps(r['error'], indent=2))
                                        found_error = True
            if not found_error:
                print("No node errors found in the resolved data.")
        else:
            print("No execution data found.")
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    print_resolved_error()
