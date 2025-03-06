from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
import mercadopago


class Pedido(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    total = models.FloatField()
    qtd_total = models.PositiveIntegerField()
    status = models.CharField(
        default="C",
        max_length=1,
        choices=(
            ('A', 'Aprovado'),
            ('C', 'Criado'),
            ('R', 'Reprovado'),
            ('P', 'Pendente'),
            ('E', 'Enviado'),
            ('F', 'Finalizado'),
        )
    )

    # Novos campos para rastreamento do pagamento
    collection_id = models.CharField(max_length=100, blank=True, null=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_type = models.CharField(max_length=100, blank=True, null=True)
    merchant_order_id = models.CharField(max_length=100, blank=True, null=True)
    preference_id = models.CharField(max_length=100, blank=True, null=True)
    site_id = models.CharField(max_length=10, blank=True, null=True)
    processing_mode = models.CharField(max_length=50, blank=True, null=True)
    external_reference = models.CharField(max_length=100, blank=True, null=True)

    data = models.DateTimeField(auto_now_add=True)
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Verifica se o pedido já existia no banco antes da alteração
        pedido_antigo = Pedido.objects.filter(pk=self.pk).first()
        
        # Se o pedido já existia e o status foi alterado
        if pedido_antigo and pedido_antigo.status != self.status:
            if self.status == 'E':  # Se mudou para "Enviado"
                self.enviar_email_pedido_enviado()
            elif self.status == 'F':  # Se mudou para "Finalizado"
                self.enviar_email_pedido_finalizado()
            elif self.status == 'A':  # Se mudou para "Aprovado" (novo)
                self.enviar_email_pedido_aprovado()
            elif self.status == 'R':  # Se mudou para "Reprovado" (novo)
                self.enviar_email_pedido_reprovado()

        super().save(*args, **kwargs)  # Salva normalmente no banco

    def verificar_status_pagamento(self):
        """Verifica o status atual do pagamento no Mercado Pago."""
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        
        try:
            if not hasattr(settings, 'MERCADO_PAGO_ACCESS_TOKEN') or not settings.MERCADO_PAGO_ACCESS_TOKEN:
                logger.error("Token do Mercado Pago não configurado")
                return False
                
            if not self.payment_id:
                logger.warning(f"Pedido {self.pk} não possui payment_id para verificação")
                return False
                
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
            payment_info = sdk.payment().get(self.payment_id)
            
            if "status" not in payment_info or payment_info["status"] != 200:
                logger.error(f"Erro ao obter informações do pagamento: {payment_info}")
                return False
            
            # Mapear status do Mercado Pago para status do sistema
            status_map = {
                'approved': 'A',  # Aprovado
                'pending': 'P',   # Pendente
                'authorized': 'P', # Autorizado mas pendente
                'in_process': 'P', # Em processamento
                'in_mediation': 'P', # Em mediação
                'rejected': 'R',  # Rejeitado
                'cancelled': 'R', # Cancelado
                'refunded': 'R',  # Reembolsado
                'charged_back': 'R' # Estornado
            }
                
            status = payment_info["response"].get("status")
            new_status = status_map.get(status)
            
            if not new_status:
                logger.warning(f"Status desconhecido recebido do Mercado Pago: {status}")
                return False
                
            if new_status != self.status:
                logger.info(f"Atualizando status do pedido {self.pk} de {self.status} para {new_status} (MP status: {status})")
                old_status = self.status
                self.status = new_status
                
                # Atualizar outros campos relevantes se necessário
                payment_data = payment_info["response"]
                if not self.collection_id and 'collection_id' in payment_data:
                    self.collection_id = payment_data.get('collection_id')
                if not self.payment_type and 'payment_type' in payment_data:
                    self.payment_type = payment_data.get('payment_type')
                if not self.merchant_order_id and 'merchant_order_id' in payment_data:
                    self.merchant_order_id = payment_data.get('merchant_order_id')
                if not self.preference_id and 'preference_id' in payment_data:
                    self.preference_id = payment_data.get('preference_id')
                if not self.site_id and 'site_id' in payment_data:
                    self.site_id = payment_data.get('site_id')
                if not self.processing_mode and 'processing_mode' in payment_data:
                    self.processing_mode = payment_data.get('processing_mode')
                    
                self.save()
                logger.info(f"Status do pedido {self.pk} atualizado: {old_status} -> {new_status}")
                return True
            else:
                logger.debug(f"Status do pedido {self.pk} não mudou, continua {self.status}")
                return False
        except Exception as e:
            logger.error(f"Erro ao verificar status do pagamento: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def enviar_email_pedido_aprovado(self):
        """Envia um e-mail de notificação quando o pagamento é aprovado."""
        try:
            send_mail(
                subject='✅ Pagamento Aprovado - Vivan Calçados',
                message=(
                    f'Olá, {self.usuario.first_name}!\n\n'
                    'Seu pagamento foi aprovado com sucesso! 💳✅\n\n'
                    f'🔹 Número do Pedido: #{self.pk}\n'
                    f'🔹 Status: Pagamento Aprovado\n\n'
                    '📌 O que acontece agora?\n'
                    '➡️ Nossa equipe já está preparando seu pedido para envio.\n'
                    '➡️ Você receberá um e-mail assim que seu pedido for enviado.\n\n'
                    'Obrigado por comprar na Vivan Calçados! 💙\n\n'
                    'Atenciosamente,\n'
                    'Equipe Vivan Calçados\n'
                    '📧 suporte@vivancalcados.com | 📞 +55 (43) 9641-4232'
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[self.usuario.email],
                fail_silently=True,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao enviar e-mail de pagamento aprovado: {str(e)}")

    def enviar_email_pedido_reprovado(self):
        """Envia um e-mail de notificação quando o pagamento é reprovado."""
        try:
            send_mail(
                subject='❌ Pagamento Não Aprovado - Vivan Calçados',
                message=(
                    f'Olá, {self.usuario.first_name}!\n\n'
                    'Infelizmente, seu pagamento não foi aprovado. 💳❌\n\n'
                    f'🔹 Número do Pedido: #{self.pk}\n'
                    f'🔹 Status: Pagamento Não Aprovado\n\n'
                    '📌 O que você pode fazer agora?\n'
                    '➡️ Verifique os dados do seu cartão de crédito ou método de pagamento.\n'
                    '➡️ Tente novamente com outro método de pagamento.\n'
                    '➡️ Entre em contato com seu banco para verificar se há alguma restrição.\n\n'
                    'Se precisar de ajuda, entre em contato com nosso suporte. Estamos à disposição para te ajudar! 😊\n\n'
                    'Atenciosamente,\n'
                    'Equipe Vivan Calçados\n'
                    '📧 suporte@vivancalcados.com | 📞 +55 (43) 9641-4232'
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[self.usuario.email],
                fail_silently=True,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao enviar e-mail de pagamento reprovado: {str(e)}")

    def enviar_email_pedido_enviado(self):
        """Envia um e-mail de notificação quando o pedido é enviado."""
        try:
            send_mail(
                subject='📦 Seu pedido foi enviado! - Vivan Calçados',
                message=(
                    f'Olá, {self.usuario.first_name}!\n\n'
                    'Temos uma ótima notícia: seu pedido foi enviado! 🚚✨\n\n'
                    f'🔹 Número do Pedido: #{self.pk}\n'
                    f'🔹 Status: Enviado ✅\n\n'
                    '📌 O que acontece agora?\n'
                    '➡️ Seu pedido está a caminho e chegará em breve!\n'
                    'Caso tenha dúvidas, entre em contato com nosso suporte. Estamos à disposição para te ajudar! 😊\n\n'
                    'Obrigado por comprar na Vivan Calçados! 💙\n\n'
                    'Atenciosamente,\n'
                    'Equipe Vivan Calçados\n'
                    '📧 suporte@vivancalcados.com | 📞 +55 (43) 9641-4232'
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[self.usuario.email],
                fail_silently=True,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao enviar e-mail de pedido enviado: {str(e)}")

    def enviar_email_pedido_finalizado(self):
        """Envia um e-mail de notificação quando o pedido é finalizado."""
        try:
            send_mail(
                subject='🎉 Pedido Entregue - Vivan Calçados',
                message=(
                    f'Olá, {self.usuario.first_name}!\n\n'
                    'Seu pedido foi entregue com sucesso! 🎉📦\n\n'
                    f'🔹 Número do Pedido: #{self.pk}\n'
                    f'🔹 Status: Finalizado ✅\n\n'
                    'Esperamos que você tenha gostado da sua compra! Se tiver qualquer dúvida ou precisar de suporte, '
                    'estamos à disposição.\n\n'
                    '✨ Gostaríamos de saber sua opinião! Se puder, nos avalie para ajudarmos mais clientes como você. 😃\n\n'
                    'Obrigado por escolher a Vivan Calçados! Até a próxima. 💙\n\n'
                    'Atenciosamente,\n'
                    'Equipe Vivan Calçados\n'
                    '📧 suporte@vivancalcados.com | 📞 +55 (43) 9641-4232'
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[self.usuario.email],
                fail_silently=True,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao enviar e-mail de pedido finalizado: {str(e)}")

    class Meta:
        verbose_name = 'Pedidos'
        verbose_name_plural = 'Pedidos Feitos'

    def __str__(self):
        return f'Pedido N. {self.pk}'


# class Pedido(models.Model):
#     usuario = models.ForeignKey(User, on_delete=models.CASCADE)
#     total = models.FloatField()
#     qtd_total = models.PositiveIntegerField()
#     status = models.CharField(
#         default="C",
#         max_length=1,
#         choices=(
#             ('A', 'Aprovado'),
#             ('C', 'Criado'),
#             ('R', 'Reprovado'),
#             ('P', 'Pendente'),
#             ('E', 'Enviado'),
#             ('F', 'Finalizado'),
#         )
#     )

#     # Novos campos para rastreamento do pagamento
#     collection_id = models.CharField(max_length=100, blank=True, null=True)
#     payment_id = models.CharField(max_length=100, blank=True, null=True)
#     payment_type = models.CharField(max_length=100, blank=True, null=True)
#     merchant_order_id = models.CharField(max_length=100, blank=True, null=True)
#     preference_id = models.CharField(max_length=100, blank=True, null=True)
#     site_id = models.CharField(max_length=10, blank=True, null=True)
#     processing_mode = models.CharField(max_length=50, blank=True, null=True)

#     data = models.DateTimeField(auto_now_add=True)

    

#     def save(self, *args, **kwargs):
#         # Verifica se o pedido já existia no banco antes da alteração
#         pedido_antigo = Pedido.objects.filter(pk=self.pk).first()
        
#         # Se o pedido já existia e o status foi alterado
#         if pedido_antigo and pedido_antigo.status != self.status:
#             if self.status == 'E':  # Se mudou para "Enviado"
#                 self.enviar_email_pedido_enviado()
#             elif self.status == 'F':  # Se mudou para "Finalizado"
#                 self.enviar_email_pedido_finalizado()

#         super().save(*args, **kwargs)  # Salva normalmente no banco

#     def enviar_email_pedido_enviado(self):
#         """Envia um e-mail de notificação quando o pedido é enviado."""
#         send_mail(
#             subject='📦 Seu pedido foi enviado! - Vivan Calçados',
#             message=(
#                 f'Olá, {self.usuario.first_name}!\n\n'
#                 'Temos uma ótima notícia: seu pedido foi enviado! 🚚✨\n\n'
#                 f'🔹 **Número do Pedido:** #{self.pk}\n'
#                 f'🔹 **Status:** Enviado ✅\n\n'
#                 '📌 O que acontece agora?\n'
#                 '➡️ Seu pedido está a caminho e chegará em breve!\n'
#                 # '➡️ Assim que possível, você receberá um código de rastreamento para acompanhar a entrega.\n\n'
#                 'Caso tenha dúvidas, entre em contato com nosso suporte. Estamos à disposição para te ajudar! 😊\n\n'
#                 'Obrigado por comprar na Vivan Calçados! 💙\n\n'
#                 '**Atenciosamente,**\n'
#                 '**Equipe Vivan Calçados**\n'
#                 '📧 suporte@vivancalçados.com | 📞 +55 (43) 9641-4232'
#             ),
#             from_email=settings.EMAIL_HOST_USER,
#             recipient_list=[self.usuario.email],
#         )

#     def enviar_email_pedido_finalizado(self):
#         """Envia um e-mail de notificação quando o pedido é finalizado."""
#         send_mail(
#             subject='🎉 Pedido Entregue - Vivan Calçados',
#             message=(
#                 f'Olá, {self.usuario.first_name}!\n\n'
#                 'Seu pedido foi **entregue com sucesso!** 🎉📦\n\n'
#                 f'🔹 **Número do Pedido:** #{self.pk}\n'
#                 f'🔹 **Status:** Finalizado ✅\n\n'
#                 'Esperamos que você tenha gostado da sua compra! Se tiver qualquer dúvida ou precisar de suporte, '
#                 'estamos à disposição.\n\n'
#                 '✨ **Gostaríamos de saber sua opinião!** Se puder, nos avalie para ajudarmos mais clientes como você. 😃\n\n'
#                 'Obrigado por escolher a Vivan Calçados! Até a próxima. 💙\n\n'
#                 '**Atenciosamente,**\n'
#                 '**Equipe Vivan Calçados**\n'
#                 '📧 suporte@vivancalçados.com | 📞 +55 (43) 9641-4232'
#             ),
#             from_email=settings.EMAIL_HOST_USER,
#             recipient_list=[self.usuario.email],
#         )

#     class Meta:
#         verbose_name = 'Pedidos'
#         verbose_name_plural = 'Pedidos Feitos'

#     def __str__(self):
#         return f'Pedido N. {self.pk}'


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    produto = models.CharField(max_length=255)
    produto_id = models.PositiveIntegerField()
    variacao = models.CharField(max_length=255)
    variacao_id = models.PositiveIntegerField()
    preco = models.FloatField()
    preco_promocional = models.FloatField(default=0)
    quantidade = models.PositiveIntegerField()
    imagem = models.CharField(max_length=2000)

    def __str__(self):
        return f'Item do {self.pedido}'

    class Meta:
        verbose_name = 'Item do pedido'
        verbose_name_plural = 'Itens do pedido'