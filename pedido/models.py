from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail


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

    data = models.DateTimeField(auto_now_add=True)

    

    def save(self, *args, **kwargs):
        # Verifica se o pedido já existia no banco antes da alteração
        pedido_antigo = Pedido.objects.filter(pk=self.pk).first()
        
        # Se o pedido já existia e o status foi alterado
        if pedido_antigo and pedido_antigo.status != self.status:
            if self.status == 'E':  # Se mudou para "Enviado"
                self.enviar_email_pedido_enviado()
            elif self.status == 'F':  # Se mudou para "Finalizado"
                self.enviar_email_pedido_finalizado()

        super().save(*args, **kwargs)  # Salva normalmente no banco

    def enviar_email_pedido_enviado(self):
        """Envia um e-mail de notificação quando o pedido é enviado."""
        send_mail(
            subject='📦 Seu pedido foi enviado! - Vivan Calçados',
            message=(
                f'Olá, {self.usuario.first_name}!\n\n'
                'Temos uma ótima notícia: seu pedido foi enviado! 🚚✨\n\n'
                f'🔹 **Número do Pedido:** #{self.pk}\n'
                f'🔹 **Status:** Enviado ✅\n\n'
                '📌 O que acontece agora?\n'
                '➡️ Seu pedido está a caminho e chegará em breve!\n'
                # '➡️ Assim que possível, você receberá um código de rastreamento para acompanhar a entrega.\n\n'
                'Caso tenha dúvidas, entre em contato com nosso suporte. Estamos à disposição para te ajudar! 😊\n\n'
                'Obrigado por comprar na Vivan Calçados! 💙\n\n'
                '**Atenciosamente,**\n'
                '**Equipe Vivan Calçados**\n'
                '📧 suporte@vivancalçados.com | 📞 +55 (43) 9641-4232'
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.usuario.email],
        )

    def enviar_email_pedido_finalizado(self):
        """Envia um e-mail de notificação quando o pedido é finalizado."""
        send_mail(
            subject='🎉 Pedido Entregue - Vivan Calçados',
            message=(
                f'Olá, {self.usuario.first_name}!\n\n'
                'Seu pedido foi **entregue com sucesso!** 🎉📦\n\n'
                f'🔹 **Número do Pedido:** #{self.pk}\n'
                f'🔹 **Status:** Finalizado ✅\n\n'
                'Esperamos que você tenha gostado da sua compra! Se tiver qualquer dúvida ou precisar de suporte, '
                'estamos à disposição.\n\n'
                '✨ **Gostaríamos de saber sua opinião!** Se puder, nos avalie para ajudarmos mais clientes como você. 😃\n\n'
                'Obrigado por escolher a Vivan Calçados! Até a próxima. 💙\n\n'
                '**Atenciosamente,**\n'
                '**Equipe Vivan Calçados**\n'
                '📧 suporte@vivancalçados.com | 📞 +55 (43) 9641-4232'
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.usuario.email],
        )

    class Meta:
        verbose_name = 'Pedidos'
        verbose_name_plural = 'Pedidos Feitos'

    def __str__(self):
        return f'Pedido N. {self.pk}'


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