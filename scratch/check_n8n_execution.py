import pg8000
import json
import sys

def check_execution():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='n8n_db'
        )
        cursor = conn.cursor()
        
        # Get latest execution
        cursor.execute("""
            SELECT id, "workflowId", status, "startedAt", "stoppedAt", error 
            FROM execution_entity 
            ORDER BY "startedAt" DESC 
            LIMIT 1;
        """)
        row = cursor.fetchone()
        if row:
            print("Latest Execution Info:")
            print(f"  ID: {row[0]}")
            print(f"  Workflow ID: {row[1]}")
            print(f"  Status: {row[2]}")
            print(f"  Started At: {row[3]}")
            print(f"  Stopped At: {row[4]}")
            print("  Error Data:")
            print(json.dumps(row[5], indent=2) if row[5] else "No error details in column.")
        else:
            print("No executions found in database.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_execution()
