import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import async_session, init_db
from app.models.models import Provider
from cryptography.fernet import Fernet

async def seed():
    await init_db()
    
    key = os.getenv('ENCRYPTION_KEY') or Fernet.generate_key()
    f = Fernet(key)
    
    async with async_session() as session:
        providers = [
            {
                'id': 'anthropic',
                'name': 'anthropic',
                'display_name': 'Anthropic Claude',
                'api_key': os.getenv('ANTHROPIC_API_KEY', 'demo-key'),
                'base_url': 'https://api.anthropic.com',
                'models': [
                    {'id': 'claude-sonnet-4-20250514', 'name': 'Claude Sonnet 4', 'max_tokens': 8192},
                    {'id': 'claude-haiku-3-20240307', 'name': 'Claude Haiku', 'max_tokens': 4096}
                ],
                'input_cost': 0.003,
                'output_cost': 0.015
            },
            {
                'id': 'openai',
                'name': 'openai', 
                'display_name': 'OpenAI',
                'api_key': os.getenv('OPENAI_API_KEY', 'demo-key'),
                'base_url': 'https://api.openai.com/v1',
                'models': [
                    {'id': 'gpt-4o', 'name': 'GPT-4o', 'max_tokens': 8192},
                    {'id': 'gpt-4o-mini', 'name': 'GPT-4o Mini', 'max_tokens': 4096}
                ],
                'input_cost': 0.005,
                'output_cost': 0.015
            },
            {
                'id': 'groq',
                'name': 'groq',
                'display_name': 'Groq',
                'api_key': os.getenv('GROQ_API_KEY', 'demo-key'),
                'base_url': 'https://api.groq.com/openai/v1',
                'models': [
                    {'id': 'llama-3.3-70b-versatile', 'name': 'Llama 3.3 70B', 'max_tokens': 4096},
                    {'id': 'mixtral-8x7b-32768', 'name': 'Mixtral 8x7B', 'max_tokens': 32768}
                ],
                'input_cost': 0.00059,
                'output_cost': 0.00079
            }
        ]
        
        for p in providers:
            encrypted_key = f.encrypt(p['api_key'].encode()).decode()
            provider = Provider(
                id=p['id'],
                name=p['name'],
                display_name=p['display_name'],
                api_key_encrypted=encrypted_key,
                base_url=p['base_url'],
                models=p['models'],
                input_cost_per_1k=p['input_cost'],
                output_cost_per_1k=p['output_cost'],
                is_active=True
            )
            session.add(provider)
        
        await session.commit()
        print(f"Seeded {len(providers)} providers with encryption key: {key.decode()}")

if __name__ == "__main__":
    asyncio.run(seed())