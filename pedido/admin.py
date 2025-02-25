from django.contrib import admin
from django.utils.html import format_html
from .models import Pedido, ItemPedido
from perfil.models import Perfil

class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ['produto', 'quantidade']
    can_delete = False
    max_num = 0
    
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['numero_pedido', 'status_colorido', 'get_cliente', 'total', 'qtd_total', 'data']
    list_filter = ['status']
    search_fields = ['usuario__username', 'usuario__email']
    inlines = [ItemPedidoInline]

    fieldsets = (
        ('INFORMAÇÕES DO PEDIDO', {
            'fields': (
                'usuario',
                'status',
                'total',
                'qtd_total',
                'data',  # Agora aparece no INFORMAÇÕES DO PEDIDO como somente leitura
            )
        }),
        ('DADOS PARA ENTREGA', {
            'fields': (
                'get_cliente',
                'get_telefone',
                'get_endereco_completo',
                'get_cidade_estado',
            ),
        }),
        ('DADOS DO PAGAMENTO', {
            'classes': ('collapse',),  # Torna a seção expansível
            'fields': (
                'get_payment_info',
                'collection_id',
                'payment_id',
                'payment_type',
                'merchant_order_id',
                'preference_id',
                'site_id',
                'processing_mode',
            ),
        }),
    )

    readonly_fields = [
        'total', 'qtd_total',
        'get_cliente', 'get_telefone',
        'get_endereco_completo', 'get_cidade_estado',
        'get_payment_info',
        'collection_id', 'payment_id', 'payment_type',
        'merchant_order_id', 'preference_id', 'site_id',
        'processing_mode',
        'data',  # Aqui garante que ele seja apenas leitura
    ]


    def get_payment_info(self, obj):
        """Retorna um resumo formatado dos dados de pagamento"""
        return format_html(
            '<div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px;">'
            '<strong style="color: #666;">Resumo do Pagamento</strong><br>'
            '<strong>ID da Transação:</strong> {}<br>'
            '<strong>Tipo de Pagamento:</strong> {}<br>'
            '<strong>Ordem:</strong> {}'
            '</div>',
            obj.payment_id or 'Não disponível',
            obj.payment_type or 'Não disponível',
            obj.merchant_order_id or 'Não disponível',
        )
    get_payment_info.short_description = "Informações do Pagamento"

    # ... resto dos seus métodos existentes ...
    def numero_pedido(self, obj):
        return format_html('<strong>Pedido #{}</strong>', obj.id)
    numero_pedido.short_description = "Número do Pedido"

    def status_colorido(self, obj):
        cores = {
            'Em processamento': '#FFA500',
            'Aprovado': '#0066CC',
            'Preparando': '#9370DB',
            'Enviado': '#32CD32',
            'Entregue': '#006400',
            'Cancelado': '#FF0000',
        }
        cor = cores.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 5px;">{}</span>',
            cor,
            obj.status
        )
    status_colorido.short_description = "Status"

    def get_cliente(self, obj):
        nome = obj.usuario.get_full_name() or obj.usuario.username
        email = obj.usuario.email
        return format_html(
            '<strong>Nome:</strong> {}<br>'
            '<strong>Email:</strong> {}',
            nome, 
            email,
        )
    get_cliente.short_description = "Informações do Cliente"

    def get_telefone(self, obj):
        if hasattr(obj.usuario, 'perfil'):
            return format_html('<strong>Telefone:</strong> {}', obj.usuario.perfil.telefone)
        return "Telefone não informado"
    get_telefone.short_description = "Contato"

    def get_endereco_completo(self, obj):
        if hasattr(obj.usuario, 'perfil'):
            perfil = obj.usuario.perfil
            return format_html(
                '<strong>Endereço:</strong> {}, Nº {}<br>'
                '<strong>Bairro:</strong> {}',
                perfil.endereco, 
                perfil.numero,
                perfil.bairro
            )
        return "Endereço não informado"
    get_endereco_completo.short_description = "Endereço"

    def get_cidade_estado(self, obj):
        if hasattr(obj.usuario, 'perfil'):
            perfil = obj.usuario.perfil
            return format_html(
                '<strong>Cidade:</strong> {} - {}<br>'
                '<strong>CEP:</strong> {}',
                perfil.cidade,
                perfil.estado,
                perfil.cep
            )
        return "Localização não informada"
    get_cidade_estado.short_description = "Localização"

admin.site.register(Pedido, PedidoAdmin)

# from django.contrib import admin
# from . import models


# class ItemPedidoInline(admin.TabularInline):
#     model = models.ItemPedido
#     extra = 1


# class PedidoAdmin(admin.ModelAdmin):
#     inlines = [
#         ItemPedidoInline
#     ]


# admin.site.register(models.Pedido, PedidoAdmin)
# admin.site.register(models.ItemPedido)
