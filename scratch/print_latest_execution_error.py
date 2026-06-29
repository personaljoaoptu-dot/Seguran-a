import pg8000
import json
import sys

def check_error():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='n8n_db'
        )
        cursor = conn.cursor()
        
        # Get latest execution data
        cursor.execute("""
            SELECT ed."executionId", ed.data, ee.status
            FROM execution_data ed
            JOIN execution_entity ee ON ed."executionId" = ee.id
            ORDER BY ed."executionId" DESC
            LIMIT 1;
        """)
        row = cursor.fetchone()
        if row:
            execution_id, data_str, status = row
            print(f"Latest Execution ID: {execution_id} | Status: {status}")
            try:
                # n8n stores execution data as serialized JSON or a JSON string
                exec_data = json.loads(data_str)
                # Look for execution errors
                result_data = exec_data.get('resultData', {})
                error = result_data.get('error', {})
                run_data = result_data.get('runData', {})
                
                print("Error Details:")
                print(json.dumps(error, indent=2))
                
                print("\nChecking node errors in runData:")
                for node_name, node_runs in run_data.items():
                    for idx, run in enumerate(node_runs):
                        if run.get('error'):
                            print(f"Node '{node_name}' (run {idx}) failed with error:")
                            print(json.dumps(run['error'], indent=2))
            except Exception as parse_err:
                print("Failed to parse data column as JSON:", parse_err)
                print("Raw data length:", len(data_str))
                # Print entire raw data for manual inspection
                print("Raw data:\n", data_str[:10000].encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))
        else:
            print("No execution data found.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_error()
