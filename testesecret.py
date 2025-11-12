# fixes.py - Correções temporárias
import os
import logging

logger = logging.getLogger(__name__)

def apply_quick_fixes():
    """Aplica correções rápidas para problemas conhecidos"""
    
    # 1. Corrigir variável de ambiente DATABASE_URL se necessário
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        os.environ['DATABASE_URL'] = database_url.replace('postgres://', 'postgresql://')
        logger.info("🔧 DATABASE_URL corrigida para postgresql://")
    
    # 2. Verificar se Firebase credentials existe
    firebase_creds_path = '/etc/secrets/firebase_credentials.json'
    if os.path.exists(firebase_creds_path):
        logger.info(f"✅ Firebase credentials encontrado: {firebase_creds_path}")
    else:
        logger.warning(f"⚠️ Firebase credentials não encontrado: {firebase_creds_path}")
    
    logger.info("🔧 Correções rápidas aplicadas")

# Executar ao importar
apply_quick_fixes()