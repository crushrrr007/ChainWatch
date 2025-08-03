# test_db.py - Supabase Database Connection Test
import asyncio
import os
from dotenv import load_dotenv

async def test_database_connection():
    """Test Supabase database connection"""
    
    # Load environment variables
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
        print("Make sure you have DATABASE_URL in your .env file")
        return False
    
    print("🔍 Testing Supabase database connection...")
    print(f"Database URL format: {database_url.split('@')[1].split('/')[0] if '@' in database_url else 'Invalid format'}")
    
    try:
        # Import asyncpg for direct connection test
        import asyncpg
        
        # Convert from SQLAlchemy format to asyncpg format
        if database_url.startswith("postgresql+asyncpg://"):
            asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        else:
            asyncpg_url = database_url
        
        print("⏳ Attempting connection...")
        
        # Test connection
        conn = await asyncpg.connect(asyncpg_url)
        
        # Test basic query
        result = await conn.fetchval("SELECT version()")
        print(f"✅ Connection successful!")
        print(f"PostgreSQL version: {result.split(',')[0]}")
        
        # Test table creation (to ensure we have permissions)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS connection_test (
                id SERIAL PRIMARY KEY,
                test_message TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✅ Table creation permissions: OK")
        
        # Test insert
        await conn.execute("""
            INSERT INTO connection_test (test_message) 
            VALUES ('ChainWatch connection test')
        """)
        print("✅ Insert permissions: OK")
        
        # Test select
        count = await conn.fetchval("SELECT COUNT(*) FROM connection_test")
        print(f"✅ Query permissions: OK (found {count} test records)")
        
        # Clean up test table
        await conn.execute("DROP TABLE connection_test")
        print("✅ Drop permissions: OK")
        
        await conn.close()
        print("\n🎉 Database test completed successfully!")
        print("Your Supabase database is ready for ChainWatch!")
        
        return True
        
    except ImportError:
        print("❌ asyncpg not installed. Run: pip install asyncpg")
        return False
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check your DATABASE_URL in .env file")
        print("2. Verify your Supabase password is correct")
        print("3. Make sure your Supabase project is active")
        print("4. Check if there are any special characters in your password")
        return False

async def test_sqlalchemy_connection():
    """Test using SQLAlchemy (what ChainWatch actually uses)"""
    print("\n🔍 Testing SQLAlchemy connection (ChainWatch method)...")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.core.config import settings
        
        # Create engine
        engine = create_async_engine(settings.DATABASE_URL, echo=True)
        
        # Test connection
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1 as test")
            test_value = result.scalar()
            
        print(f"✅ SQLAlchemy connection successful! Test query returned: {test_value}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 ChainWatch Database Connection Test")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_database_connection())
    
    print("\n" + "=" * 50)
    
    # Test SQLAlchemy if basic connection works
    try:
        asyncio.run(test_sqlalchemy_connection())
    except Exception as e:
        print(f"⚠️ SQLAlchemy test skipped: {e}")
    
    print("\n🎯 Next step: Run 'python main.py' to start ChainWatch!")