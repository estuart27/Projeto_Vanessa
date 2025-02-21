from django.contrib import admin
from django.utils.html import format_html
from .models import Pedido, ItemPedido
from perfil.models import Perfil

class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0  # Remove campos extras vazios
    readonly_fields = ['produto', 'quantidade']
    can_delete = False
    max_num = 0  # Impede adição de novos itens
    
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['numero_pedido', 'status_colorido', 'get_cliente', 'total', 'qtd_total']
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
    )

    readonly_fields = [
        'total', 'qtd_total', 
        'get_cliente', 'get_telefone', 
        'get_endereco_completo', 'get_cidade_estado'
    ]

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
