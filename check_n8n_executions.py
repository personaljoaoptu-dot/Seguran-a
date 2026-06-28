import pg8000
import sys
import json

def check_executions():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='n8n_db'
        )
        cursor = conn.cursor()
        
        # Query column names of execution_entity
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'execution_entity';")
        cols = [c[0] for c in cursor.fetchall()]
        print("execution_entity columns:", cols)
        
        # Query most recent execution
        cursor.execute("""
            SELECT e.id, e."workflowId", e.status, e."startedAt", e."stoppedAt", d."workflowData"
            FROM execution_entity e
            LEFT JOIN execution_data d ON e.id = d."executionId"
            ORDER BY e."startedAt" DESC
            LIMIT 5;
        """)
        rows = cursor.fetchall()
        print("\nRecent Executions:")
        for r in rows:
            print(f"ID: {r[0]}, Workflow ID: {r[1]}, Status: {r[2]}, Started: {r[3]}, Stopped: {r[4]}")
            if r[5]:
                print(f"  Data snippet: {str(r[5])[:300]}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_executions()
