import paramiko
import sys

def deploy_creds():
    js_code = """
const crypto = require('crypto');
const { Client } = require('/usr/local/lib/node_modules/n8n/node_modules/pg');

const RANDOM_BYTES = Buffer.from('Salted__', 'binary');

class CipherAes256CBC {
    encrypt(data, key) {
        const salt = crypto.randomBytes(8);
        const [derivedKey, iv] = this.getKeyAndIv(salt, key);
        const cipher = crypto.createCipheriv('aes-256-cbc', derivedKey, iv);
        const encrypted = cipher.update(data);
        return Buffer.concat([RANDOM_BYTES, salt, encrypted, cipher.final()]).toString('base64');
    }
    getKeyAndIv(salt, key) {
        const password = Buffer.concat([Buffer.from(key, 'binary'), salt]);
        const hash1 = crypto.createHash('md5').update(password).digest();
        const hash2 = crypto.createHash('md5')
            .update(Buffer.concat([hash1, password]))
            .digest();
        const iv = crypto.createHash('md5')
            .update(Buffer.concat([hash2, password]))
            .digest();
        const derivedKey = Buffer.concat([hash1, hash2]);
        return [derivedKey, iv];
    }
}

const key = 'dfb0dbc04a430ae06bcb3a0ffa662e87f2f2dac21901aa3d';
const credentialsData = {
    host: "postgres",
    port: 5432,
    database: "aegisyear",
    user: "postgres",
    password: "KtnYcxnVOGjD4thzS6tlBcW9"
};
const plainText = JSON.stringify(credentialsData);
const cipher = new CipherAes256CBC();
const encryptedData = cipher.encrypt(plainText, key);

const client = new Client({
    host: 'postgres',
    port: 5432,
    user: 'postgres',
    password: 'KtnYcxnVOGjD4thzS6tlBcW9',
    database: 'n8n_db'
});

async function main() {
    await client.connect();
    
    const res = await client.query("SELECT id FROM credentials_entity WHERE id = 'c5ef944b-4b10-4ff5-b9f0-c5ef54ab6903';");
    if (res.rows.length === 0) {
        console.log("Inserting PostgreSQL credential...");
        await client.query(`
            INSERT INTO credentials_entity (name, data, type, "createdAt", "updatedAt", id, "isManaged", "isGlobal", "isResolvable", "resolvableAllowFallback")
            VALUES ($1, $2, $3, NOW(), NOW(), $4, false, false, false, false);
        `, ['PostgreSQL production', encryptedData, 'postgres', 'c5ef944b-4b10-4ff5-b9f0-c5ef54ab6903']);
        console.log("PostgreSQL credential inserted successfully!");
    } else {
        console.log("PostgreSQL credential already exists. Updating data...");
        await client.query(`
            UPDATE credentials_entity 
            SET data = $1, "updatedAt" = NOW()
            WHERE id = 'c5ef944b-4b10-4ff5-b9f0-c5ef54ab6903';
        `, [encryptedData]);
        console.log("PostgreSQL credential updated successfully!");
    }
    
    await client.end();
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Writing JS script inside container...")
        
        # Write JS code to a file in container
        # Escape single quotes and write
        escaped_js = js_code.replace("'", "'\\''")
        cmd_write = f"docker exec -i n8n_app sh -c \"cat > /tmp/insert_creds.js\""
        
        stdin, stdout, stderr = ssh.exec_command(cmd_write)
        stdin.write(js_code)
        stdin.close()
        
        # Execute the JS script
        print("Executing script inside n8n container...")
        cmd_exec = "docker exec -u node n8n_app node /tmp/insert_creds.js"
        stdin, stdout, stderr = ssh.exec_command(cmd_exec)
        stdout_str = stdout.read().decode('utf-8').strip()
        stderr_str = stderr.read().decode('utf-8').strip()
        if stdout_str:
            print("STDOUT:", stdout_str)
        if stderr_str:
            print("STDERR:", stderr_str)
            
        # Clean up
        print("Cleaning up /tmp/insert_creds.js...")
        ssh.exec_command("docker exec -u root n8n_app rm -f /tmp/insert_creds.js")
        
        ssh.close()
        print("Credentials setup completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    deploy_creds()
