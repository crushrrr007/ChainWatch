import socket
import asyncpg
import asyncio

async def test():
    try:
        print("Testing DNS resolution...")
        ip = socket.gethostbyname("db.wbwvsrkuumbgryskgbbb.supabase.co")
        print(f"✅ DNS resolved to: {ip}")
        
        print("Testing database connection...")
        conn = await asyncpg.connect(
            "postgresql://postgres:%40Crusher007@db.wbwvsrkuumbgryskgbbb.supabase.co:6543/postgres"
        )
        print("✅ Database connection successful!")
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())
