import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://docubrain:docubrain123@docubrain-postgres:5432/docubrain')
