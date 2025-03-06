# tasks.py
import logging
from celery import shared_task
from django.conf import settings
from .models import Pedido

logger = logging.getLogger(__name__)

@shared_task
def verificar_pagamentos_pendentes():
    """
    Tarefa para verificar periodicamente o status de pagamentos pendentes.
    Esta tarefa deve ser agendada para execução periódica (por exemplo, a cada 30 minutos).
    """
    logger.info("Iniciando verificação de pagamentos pendentes")
    
    # Buscar pedidos com status pendente e que possuem payment_id
    pedidos_pendentes = Pedido.objects.filter(
        status='P',  # Pendente
        payment_id__isnull=False
    ).exclude(payment_id='')
    
    logger.info(f"Encontrados {pedidos_pendentes.count()} pedidos pendentes para verificação")
    
    atualizados = 0
    for pedido in pedidos_pendentes:
        try:
            if pedido.verificar_status_pagamento():
                atualizados += 1
        except Exception as e:
            logger.error(f"Erro ao verificar pedido {pedido.pk}: {str(e)}")
    
    logger.info(f"Verificação concluída. {atualizados} pedidos foram atualizados.")
    return atualizados