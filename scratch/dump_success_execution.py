import pg8000
import json
import sys
import os

def dump_success():
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
            SELECT ed.data, ee.id
            FROM execution_data ed
            JOIN execution_entity ee ON ed."executionId" = ee.id
            WHERE ee.status = 'success'
            ORDER BY ed."executionId" DESC
            LIMIT 1;
        """)
        row = cursor.fetchone()
        if row:
            raw_str, exec_id = row
            os.makedirs("scratch", exist_ok=True)
            with open("scratch/success_exec.json", "w", encoding="utf-8") as f:
                f.write(raw_str)
            print(f"Successfully dumped raw success execution log for ID {exec_id} to scratch/success_exec.json!")
        else:
            print("No successful executions found.")
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    dump_success()
