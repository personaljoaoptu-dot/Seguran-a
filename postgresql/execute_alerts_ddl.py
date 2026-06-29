import pg8000
import os

DB_HOST = "144.91.121.55"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASS = "KtnYcxnVOGjD4thzS6tlBcW9"
DB_NAME = "aegisyear"

def execute_ddl():
    print("Conectando ao banco de dados PostgreSQL na VPS...")
    try:
        conn = pg8000.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        # Read SQL file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sql_path = os.path.join(base_dir, 'aegiseye_alerts_schema.sql')
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_queries = f.read()
            
        print("Executando DDL de criação da tabela 'alertas'...")
        # Execute queries (split by semicolon if needed, but pg8000 cursor can execute multi-statement strings if supported, or we split them)
        for statement in sql_queries.split(';'):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)
                
        conn.commit()
        print("[SUCESSO] Tabela 'alertas' criada ou já existente no banco de dados!")
        cursor.close()
        conn.close()
    except Exception as e:
        print("[ERRO] Falha ao executar DDL:", e)

if __name__ == '__main__':
    execute_ddl()
