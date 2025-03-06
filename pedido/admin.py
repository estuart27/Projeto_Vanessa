from django.contrib import admin
from django.utils.html import format_html
from .models import Pedido, ItemPedido
from perfil.models import Perfil

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.conf import settings
import os

class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ['item_detalhado']
    can_delete = False
    max_num = 0
    
    fields = ['item_detalhado']
    
    def item_detalhado(self, obj):
        """
        Exibe os detalhes do item de forma organizada e limpa
        """
        def resolve_image_url(image_path):
            # Estratégias para resolver URL da imagem
            if not image_path:
                return '/static/placeholder.png'
            
            # Se for uma URL completa, retorna direto
            if image_path.startswith(('http://', 'https://')):
                return image_path
            
            # Tenta resolver como caminho de mídia
            try:
                # Tenta construir caminho completo para mídia
                full_media_path = os.path.join(settings.MEDIA_URL, image_path)
                return full_media_path
            except:
                # Se falhar, usa placeholder
                return '/static/placeholder.png'
        
        # Resolve URL da imagem
        imagem = resolve_image_url(obj.imagem)
        
        produto = obj.produto or 'Produto não especificado'
        variacao = obj.variacao or 'Sem variação'
        quantidade = obj.quantidade or 0
        preco = obj.preco or 0
        preco_promocional = obj.preco_promocional or 0
        
        # Calcula o subtotal com segurança
        subtotal = (quantidade * preco) or 0
        
        # Determina o preço a ser exibido
        preco_exibido = preco_promocional if preco_promocional > 0 else preco
        
        return mark_safe(
            f'<div style="'
            f'display: flex; '
            f'background-color: #f8f9fa; '
            f'border: 1px solid #e9ecef; '
            f'border-radius: 8px; '
            f'padding: 15px; '
            f'gap: 15px; '
            f'width: 100%;">'
            f'    <div style="flex: 0 0 120px; margin-right: 15px;">'
            f'        <img src="{imagem}" style="'
            f'            width: 120px; '
            f'            height: 120px; '
            f'            object-fit: cover; '
            f'            border-radius: 6px; '
            f'            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">'
            f'    </div>'
            f'    <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">'
            f'        <h3 style="'
            f'            margin: 0 0 10px 0; '
            f'            color: #343a40; '
            f'            font-size: 18px; '
            f'            font-weight: 600; '
            f'            border-bottom: 1px solid #dee2e6; '
            f'            padding-bottom: 10px;">{produto}</h3>'
            f'        <div style="'
            f'            display: grid; '
            f'            grid-template-columns: 1fr 1fr; '
            f'            gap: 8px; '
            f'            color: #6c757d;">'
            f'            <div><strong>Tamanho :</strong> {variacao}</div>'
            f'            <div><strong>Quantidade:</strong> {quantidade}</div>'
            f'            <div><strong>Preço Unitário:</strong> R$ {preco_exibido:.2f}</div>'
            f'          {"<div><strong style=\"color: #dc3545;\">Preço Promocional:</strong> R$ " + f"{preco_promocional:.2f}</div>" if preco_promocional > 0 else ""}'
            f'            <div style="'
            f'                grid-column: 1 / -1; '
            f'                font-weight: bold; '
            f'                color: #28a745; '
            f'                border-top: 1px solid #dee2e6; '
            f'                padding-top: 8px; '
            f'                text-align: right;">Subtotal: R$ {subtotal:.2f}</div>'
            f'        </div>'
            f'    </div>'
            f'</div>'
        )

    item_detalhado.short_description = "Detalhes do Item"

    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
class PedidoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_pedido', 
        'status_colorido', 
        'get_cliente', 
        'total', 
        'qtd_total', 
        'data', 
        'ultima_atualizacao',  # Novo campo adicionado
        'get_payment_info_short'  # Novo método para resumo do pagamento
    ]
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
                'data',
                'ultima_atualizacao',  # Novo campo adicionado
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
                'external_reference',  # Novo campo adicionado
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
        'processing_mode', 'external_reference',  # Novo campo adicionado
        'data', 'ultima_atualizacao',  # Campos de data agora são somente leitura
    ]

    def get_payment_info(self, obj):
        """Retorna um resumo formatado dos dados de pagamento"""
        return format_html(
            '<div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px;">'
            '<strong style="color: #666;">Resumo do Pagamento</strong><br>'
            '<strong>ID da Transação:</strong> {}<br>'
            '<strong>Tipo de Pagamento:</strong> {}<br>'
            '<strong>Ordem:</strong> {}<br>'
            '<strong>Referência Externa:</strong> {}<br>'
            '<strong>Modo de Processamento:</strong> {}'
            '</div>',
            obj.payment_id or 'Não disponível',
            obj.payment_type or 'Não disponível',
            obj.merchant_order_id or 'Não disponível',
            obj.external_reference or 'Não disponível',
            obj.processing_mode or 'Não disponível',
        )
    get_payment_info.short_description = "Informações do Pagamento"

    def get_payment_info_short(self, obj):
        """Retorna um resumo curto dos dados de pagamento para a lista de pedidos"""
        return format_html(
            '<strong>ID:</strong> {}<br>'
            '<strong>Tipo:</strong> {}<br>'
            '<strong>Referência:</strong> {}',
            obj.payment_id or 'N/A',
            obj.payment_type or 'N/A',
            obj.external_reference or 'N/A',
        )
    get_payment_info_short.short_description = "Pagamento"

    def numero_pedido(self, obj):
        return format_html('<strong>Pedido #{}</strong>', obj.id)
    numero_pedido.short_description = "Número do Pedido"

    def status_colorido(self, obj):
        cores = {
            'A': '#0066CC',  # Aprovado
            'C': '#FFA500',  # Criado
            'R': '#FF0000',  # Reprovado
            'P': '#9370DB',  # Pendente
            'E': '#32CD32',  # Enviado
            'F': '#006400',  # Finalizado
        }
        cor = cores.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 5px;">{}</span>',
            cor,
            obj.get_status_display()  # Exibe o nome legível do status
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
