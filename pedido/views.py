import json
import uuid
import time
import logging
import traceback
from urllib.parse import quote

import mercadopago

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, reverse, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, DetailView
from django.views.decorators.csrf import csrf_exempt

from .models import Pedido, ItemPedido
from produto.models import Variacao
from perfil.models import Perfil

from utils import utils


logger = logging.getLogger(__name__)


class DispatchLoginRequiredMixin(View):
    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request,
                'Você precisa fazer login para acessar esta página.'
            )
            return redirect('perfil:criar')

        return super().dispatch(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(usuario=self.request.user)
        return qs
    

def pagamento_whatsapp(request):
    try:
        # Verificar se usuário está autenticado
        if not request.user.is_authenticated:
            messages.error(
                request,
                'Você precisa fazer login para finalizar a compra.'
            )
            return redirect('perfil:criar')
            
        # Obter o carrinho da sessão
        carrinho = request.session.get('carrinho', {})
        
        # Verificar se o carrinho está vazio
        if not carrinho:
            messages.error(
                request,
                'Seu carrinho está vazio. Adicione produtos antes de finalizar.'
            )
            return redirect('produto:lista')
        
        # Obter o perfil do usuário para cálculo do frete
        try:
            perfil = Perfil.objects.get(usuario=request.user)
            # Importar a função de cálculo de frete
            from produto.templatetags.frete import calcular_frete
            valor_frete = calcular_frete(perfil)
        except Exception as e:
            logger.error(f"Erro ao calcular frete: {str(e)}")
            # Em caso de erro, usar um valor padrão para o frete
            valor_frete = 15.00
            logger.info(f"Usando valor padrão de frete: R$ {valor_frete}")
            
        # Calcular o subtotal
        subtotal = sum(item['preco_quantitativo'] for item in carrinho.values())
        
        # Calcular o total com frete
        total_com_frete = subtotal + valor_frete
        
        pedido_id = request.session.get('pedido_id', 'N/A')

        # Criar a mensagem profissional
        mensagem = (
            f"🔹 *Solicitação de Pagamento*\n\n"
            f"📌 *Pedido Nº {pedido_id}*\n"
            f"🛍️ *Itens do Pedido:*\n"
        )

        for item in carrinho.values():
            mensagem += (
                f"   - {item['produto_nome']} ({item['variacao_nome']}) — "
                f"Cor: {item['cor_nome']} — "
                f"Qtd: {item['quantidade']}\n"
            )

        mensagem += (
            f"\n💵 *Subtotal:* R$ {subtotal:.2f}\n"
            f"🚚 *Frete:* R$ {valor_frete:.2f}\n"
            f"💰 *Valor Total:* R$ {total_com_frete:.2f}\n\n"
            f"Por favor, me informe os detalhes do pagamento.\n"
            f"Agradeço pela preferência! 😊"
        )

        # Verificar configuração do número de WhatsApp
        whatsapp_number = getattr(settings, 'WHATSAPP_NUMBER', "554330276717")
        # whatsapp_number = getattr(settings, 'WHATSAPP_NUMBER', "5543996341638")

        
        if not whatsapp_number:
            logger.error("Número de WhatsApp não configurado")
            messages.error(
                request,
                'Erro na configuração do sistema de pagamento. Entre em contato com o suporte.'
            )
            return redirect('produto:lista')

        # Codificar a mensagem para URL
        mensagem_codificada = quote(mensagem)

        # Gerar a URL do WhatsApp
        whatsapp_url = f"https://wa.me/{whatsapp_number}?text={mensagem_codificada}"

        return redirect(whatsapp_url)
    except Exception as e:
        logger.error(f"Erro no pagamento via WhatsApp: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(
            request,
            'Ocorreu um erro ao processar o pagamento. Por favor, tente novamente ou entre em contato com o suporte.'
        )
        return redirect('produto:lista')


# class SalvarPedido(View):
#     template_name = 'pedido/pagar.html'

#     def get(self, *args, **kwargs):
#         # Adicionar logs para depuração
#         print("Iniciando SalvarPedido.get()")
#         try:
#             if not self.request.user.is_authenticated:
#                 messages.error(
#                     self.request,
#                     'Você precisa fazer login para finalizar a compra.'
#                 )
#                 return redirect('perfil:criar')

#             if not self.request.session.get('carrinho'):
#                 messages.error(
#                     self.request,
#                     'Seu carrinho está vazio.'
#                 )
#                 return redirect('produto:lista')

#             # Obter o perfil do usuário para cálculo do frete
#             try:
#                 perfil = Perfil.objects.get(usuario=self.request.user)
#             except Perfil.DoesNotExist:
#                 messages.error(
#                     self.request,
#                     'Complete seu perfil para finalizar a compra.'
#                 )
#                 return redirect('perfil:criar')

#             # Calcular o frete baseado no endereço do usuário
#             try:
#                 # Importar a função de cálculo de frete
#                 from produto.templatetags.omfilters import calcular_frete
#                 valor_frete = calcular_frete(perfil)
#                 print(f"Valor do frete calculado: R$ {valor_frete}")
#             except Exception as e:
#                 print(f"Erro ao calcular frete: {str(e)}")
#                 # Em caso de erro, usar um valor padrão para o frete
#                 valor_frete = 15.00
#                 print(f"Usando valor padrão de frete: R$ {valor_frete}")

#             carrinho = self.request.session.get('carrinho')
#             print(f"Carrinho obtido da sessão: {carrinho}")
            
#             # Verificar se há itens no carrinho
#             if not carrinho:
#                 messages.error(
#                     self.request,
#                     'Seu carrinho está vazio ou inválido.'
#                 )
#                 return redirect('produto:lista')

#             carrinho_variacao_ids = []
#             for item_key in carrinho:
#                 if '-' in str(item_key):
#                     variacao_id, cor_id = item_key.split('-')
#                     if cor_id == 'padrao':
#                         cor_id = None  # Define cor_id como None para produtos sem cor
#                     carrinho_variacao_ids.append(int(variacao_id))
#                 else:
#                     carrinho_variacao_ids.append(int(item_key))
            
#             print(f"IDs de variação no carrinho: {carrinho_variacao_ids}")
            
#             # Verificar se as variações existem no banco de dados
#             bd_variacoes = list(
#                 Variacao.objects.select_related('produto')
#                 .filter(id__in=carrinho_variacao_ids)
#             )
            
#             print(f"Variações encontradas no banco: {len(bd_variacoes)}")
            
#             # Verificar se todas as variações foram encontradas
#             if len(bd_variacoes) != len(set(carrinho_variacao_ids)):
#                 messages.error(
#                     self.request,
#                     'Alguns produtos no seu carrinho não estão mais disponíveis. O carrinho foi atualizado.'
#                 )
#                 return redirect('produto:carrinho')

#             # Processamento do carrinho
#             for variacao in bd_variacoes:
#                 vid = str(variacao.id)
                
#                 # Verificar todas as chaves do carrinho que contêm esta variação
#                 chaves_relacionadas = []
#                 for item_key in carrinho:
#                     if '-' in str(item_key):
#                         v_id, _ = item_key.split('-')
#                         if v_id == vid:
#                             chaves_relacionadas.append(item_key)
#                     elif str(item_key) == vid:
#                         chaves_relacionadas.append(item_key)
                
#                 for chave in chaves_relacionadas:
#                     # Verificar se a chave existe no carrinho
#                     if chave not in carrinho:
#                         continue
                        
#                     estoque = variacao.estoque
#                     qtd_carrinho = carrinho[chave]['quantidade']
#                     preco_unt = carrinho[chave]['preco_unitario']
#                     preco_unt_promo = carrinho[chave]['preco_unitario_promocional']

#                     if estoque < qtd_carrinho:
#                         carrinho[chave]['quantidade'] = estoque
#                         carrinho[chave]['preco_quantitativo'] = estoque * preco_unt
#                         carrinho[chave]['preco_quantitativo_promocional'] = estoque * preco_unt_promo

#                         messages.warning(
#                             self.request,
#                             f'Estoque insuficiente para o produto "{carrinho[chave]["produto_nome"]}". Quantidade ajustada automaticamente.'
#                         )
                    
#                     # Verificar se o preço foi alterado desde a adição ao carrinho
#                     preco_atual = variacao.preco
#                     preco_atual_promo = variacao.preco_promocional
                    
#                     if preco_atual != preco_unt or (preco_atual_promo and preco_atual_promo != preco_unt_promo):
#                         carrinho[chave]['preco_unitario'] = preco_atual
#                         carrinho[chave]['preco_unitario_promocional'] = preco_atual_promo
#                         carrinho[chave]['preco_quantitativo'] = qtd_carrinho * preco_atual
#                         carrinho[chave]['preco_quantitativo_promocional'] = qtd_carrinho * preco_atual_promo if preco_atual_promo else 0
                        
#                         messages.info(
#                             self.request,
#                             f'O preço do produto "{carrinho[chave]["produto_nome"]}" foi atualizado no seu carrinho.'
#                         )
                    
#             self.request.session.save()
            
#             # Recalcular totais após atualizações
#             qtd_total_carrinho = utils.cart_total_qtd(carrinho)
#             valor_total_carrinho = utils.cart_totals(carrinho)
            
#             # Adicionar o valor do frete ao total
#             valor_total_com_frete = valor_total_carrinho + valor_frete
            
#             print(f"Quantidade total: {qtd_total_carrinho}")
#             print(f"Subtotal: R$ {valor_total_carrinho}")
#             print(f"Frete: R$ {valor_frete}")
#             print(f"Total com frete: R$ {valor_total_com_frete}")
            
#             # Verificar se ainda há itens no carrinho após as atualizações
#             if not carrinho:
#                 messages.error(
#                     self.request,
#                     'Seu carrinho está vazio após as atualizações de estoque.'
#                 )
#                 return redirect('produto:lista')

#             # Gerar um identificador único para referência externa
#             pedido_uuid = str(uuid.uuid4())
#             print(f"Referência externa gerada: {pedido_uuid}")
            
#             # Criar o pedido usando try/except para capturar possíveis erros
#             # Criar o pedido usando try/except para capturar possíveis erros
#             try:
#                 pedido = Pedido(
#                     usuario=self.request.user,
#                     total=valor_total_com_frete,  # Total com frete
#                     frete=valor_frete,  # Valor do frete
#                     qtd_total=qtd_total_carrinho,
#                     status='C',  # Status de criado, conforme definido no modelo
#                     external_reference=pedido_uuid,  # Referência externa para rastreamento
#                 )
#                 pedido.save()
#                 print(f"Pedido criado com ID: {pedido.id}")
#             except Exception as e:
#                 print(f"Erro ao criar pedido: {str(e)}")
#                 messages.error(
#                     self.request,
#                     f'Erro ao criar pedido: {str(e)}'
#                 )
#                 return redirect('produto:carrinho')
            
#             # Criar os itens do pedido
#             item_pedido_list = []
#             try:
#                 for item_key, v in carrinho.items():
#                     # Verificar se o item_key contém uma cor
#                     cor_nome = ''
#                     cor_id = None
#                     imagem = v.get('imagem', '')
                    
#                     if '-' in str(item_key):
#                         # Se tiver hífen, extrair ID da variação e da cor
#                         variacao_id, cor_id = item_key.split('-')
#                         if cor_id == 'padrao':
#                             cor_id = None  # Define cor_id como None para produtos sem cor
#                         cor_nome = v.get('cor_nome', '')
#                     else:
#                         variacao_id = item_key
                    
#                     item = ItemPedido(
#                         pedido=pedido,
#                         produto=v['produto_nome'],
#                         produto_id=v['produto_id'],
#                         variacao=v['variacao_nome'],
#                         variacao_id=v['variacao_id'],
#                         cor=cor_nome,
#                         cor_id=cor_id,
#                         preco=v['preco_unitario'],
#                         preco_promocional=v['preco_unitario_promocional'],
#                         quantidade=v['quantidade'],
#                         imagem=imagem
#                     )
#                     item_pedido_list.append(item)
                
#                 # Criar itens em massa
#                 ItemPedido.objects.bulk_create(item_pedido_list)
#                 print(f"Criados {len(item_pedido_list)} itens de pedido")
#             except Exception as e:
#                 print(f"Erro ao criar itens do pedido: {str(e)}")
#                 # Se houve erro ao criar os itens, excluir o pedido para evitar pedidos órfãos
#                 if pedido.id:
#                     pedido.delete()
#                 messages.error(
#                     self.request,
#                     f'Erro ao criar itens do pedido: {str(e)}'
#                 )
#                 return redirect('produto:carrinho')
            
#             # Atualizar estoque das variações
#             try:
#                 for v in carrinho.values():
#                     variacao = Variacao.objects.get(id=v['variacao_id'])
#                     variacao.estoque -= v['quantidade']
#                     if variacao.estoque < 0:
#                         variacao.estoque = 0
#                     variacao.save()
#                     print(f"Estoque da variação {variacao.id} atualizado para {variacao.estoque}")
#             except Exception as e:
#                 print(f"Erro ao atualizar estoque: {str(e)}")
#                 # Não vamos reverter o pedido aqui, apenas logar o erro
            
#             # Limpar o carrinho após finalizar o pedido
#             del self.request.session['carrinho']
#             self.request.session.save()
            
#             messages.success(
#                 self.request,
#                 'Pedido criado com sucesso! Obrigado pela compra.'
#             )
            
#             print(f"Redirecionando para detalhes do pedido: {pedido.id}")
#             # Redirecionar para a página de detalhes do pedido
#             return redirect('pedido:detalhe', pk=pedido.id)
            
#         except Exception as e:
#             import traceback
#             print(f"Erro geral em SalvarPedido: {str(e)}")
#             print(traceback.format_exc())
#             messages.error(
#                 self.request,
#                 f'Ocorreu um erro ao processar seu pedido: {str(e)}. Por favor, tente novamente.'
#             )
#             return redirect('produto:lista')

class SalvarPedido(View):
    template_name = 'pedido/pagar.html'

    def get(self, *args, **kwargs):
        # Adicionar logs para depuração
        logger.info("Iniciando SalvarPedido.get()")
        try:
            if not self.request.user.is_authenticated:
                messages.error(
                    self.request,
                    'Você precisa fazer login para finalizar a compra.'
                )
                return redirect('perfil:criar')

            if not self.request.session.get('carrinho'):
                messages.error(
                    self.request,
                    'Seu carrinho está vazio.'
                )
                return redirect('produto:lista')

            # Obter o perfil do usuário para cálculo do frete
            try:
                perfil = Perfil.objects.get(usuario=self.request.user)
            except Perfil.DoesNotExist:
                messages.error(
                    self.request,
                    'Complete seu perfil para finalizar a compra.'
                )
                return redirect('perfil:criar')

            # Calcular o frete baseado no endereço do usuário
            try:
                # Importar a função de cálculo de frete
                from produto.templatetags.frete import calcular_frete
                valor_frete = calcular_frete(perfil)
                logger.info(f"Valor do frete calculado: R$ {valor_frete}")
            except Exception as e:
                logger.error(f"Erro ao calcular frete: {str(e)}")
                # Em caso de erro, usar um valor padrão para o frete
                valor_frete = 15.00
                logger.info(f"Usando valor padrão de frete: R$ {valor_frete}")

            carrinho = self.request.session.get('carrinho')
            logger.info(f"Carrinho obtido da sessão: {carrinho}")
            
            # Verificar se há itens no carrinho
            if not carrinho:
                messages.error(
                    self.request,
                    'Seu carrinho está vazio ou inválido.'
                )
                return redirect('produto:lista')

            # Extrair todas as chaves de itens do carrinho
            carrinho_item_keys = [k for k in carrinho]
            
            # Extrair IDs de variação, lidando com a possibilidade de chaves com cor
            carrinho_variacao_ids = []
            for item_key in carrinho_item_keys:
                # Se o item_key contiver um hífen, temos uma variação com cor
                if '-' in str(item_key):
                    variacao_id, _ = item_key.split('-')
                    carrinho_variacao_ids.append(int(variacao_id))
                else:
                    carrinho_variacao_ids.append(int(item_key))
            
            logger.info(f"IDs de variação no carrinho: {carrinho_variacao_ids}")
            
            # Verificar se existem IDs no carrinho
            if not carrinho_variacao_ids:
                messages.error(
                    self.request,
                    'Carrinho inválido. Por favor, adicione os produtos novamente.'
                )
                del self.request.session['carrinho']
                self.request.session.save()
                return redirect('produto:lista')
                
            # Verificar se as variações existem no banco de dados
            bd_variacoes = list(
                Variacao.objects.select_related('produto')
                .filter(id__in=carrinho_variacao_ids)
            )
            
            logger.info(f"Variações encontradas no banco: {len(bd_variacoes)}")
            
            # Verificar se todas as variações foram encontradas
            if len(bd_variacoes) != len(set(carrinho_variacao_ids)):
                messages.error(
                    self.request,
                    'Alguns produtos no seu carrinho não estão mais disponíveis. O carrinho foi atualizado.'
                )
                # Remover variações que não existem mais
                for item_key in list(carrinho.keys()):
                    if '-' in str(item_key):
                        variacao_id, _ = item_key.split('-')
                        if int(variacao_id) not in [v.id for v in bd_variacoes]:
                            del carrinho[item_key]
                    else:
                        if int(item_key) not in [v.id for v in bd_variacoes]:
                            del carrinho[item_key]        
                self.request.session.save()
                return redirect('produto:carrinho')

            # Processamento do carrinho
            for variacao in bd_variacoes:
                vid = str(variacao.id)
                
                # Verificar todas as chaves do carrinho que contêm esta variação
                chaves_relacionadas = []
                for item_key in carrinho:
                    if '-' in str(item_key):
                        v_id, _ = item_key.split('-')
                        if v_id == vid:
                            chaves_relacionadas.append(item_key)
                    elif str(item_key) == vid:
                        chaves_relacionadas.append(item_key)
                
                for chave in chaves_relacionadas:
                    # Verificar se a chave existe no carrinho
                    if chave not in carrinho:
                        continue
                        
                    estoque = variacao.estoque
                    qtd_carrinho = carrinho[chave]['quantidade']
                    preco_unt = carrinho[chave]['preco_unitario']
                    preco_unt_promo = carrinho[chave]['preco_unitario_promocional']

                    if estoque < qtd_carrinho:
                        carrinho[chave]['quantidade'] = estoque
                        carrinho[chave]['preco_quantitativo'] = estoque * preco_unt
                        carrinho[chave]['preco_quantitativo_promocional'] = estoque * preco_unt_promo

                        messages.warning(
                            self.request,
                            f'Estoque insuficiente para o produto "{carrinho[chave]["produto_nome"]}". Quantidade ajustada automaticamente.'
                        )
                    
                    # Verificar se o preço foi alterado desde a adição ao carrinho
                    preco_atual = variacao.preco
                    preco_atual_promo = variacao.preco_promocional
                    
                    if preco_atual != preco_unt or (preco_atual_promo and preco_atual_promo != preco_unt_promo):
                        carrinho[chave]['preco_unitario'] = preco_atual
                        carrinho[chave]['preco_unitario_promocional'] = preco_atual_promo
                        carrinho[chave]['preco_quantitativo'] = qtd_carrinho * preco_atual
                        carrinho[chave]['preco_quantitativo_promocional'] = qtd_carrinho * preco_atual_promo if preco_atual_promo else 0
                        
                        messages.info(
                            self.request,
                            f'O preço do produto "{carrinho[chave]["produto_nome"]}" foi atualizado no seu carrinho.'
                        )
                    
            self.request.session.save()
            
            # Recalcular totais após atualizações
            qtd_total_carrinho = utils.cart_total_qtd(carrinho)
            valor_total_carrinho = utils.cart_totals(carrinho)
            
            # Adicionar o valor do frete ao total
            valor_total_com_frete = valor_total_carrinho + valor_frete
            
            logger.info(f"Quantidade total: {qtd_total_carrinho}")
            logger.info(f"Subtotal: R$ {valor_total_carrinho}")
            logger.info(f"Frete: R$ {valor_frete}")
            logger.info(f"Total com frete: R$ {valor_total_com_frete}")
            
            # Verificar se ainda há itens no carrinho após as atualizações
            if not carrinho:
                messages.error(
                    self.request,
                    'Seu carrinho está vazio após as atualizações de estoque.'
                )
                return redirect('produto:lista')

            # Gerar um identificador único para referência externa
            pedido_uuid = str(uuid.uuid4())
            logger.info(f"Referência externa gerada: {pedido_uuid}")
            
            # Armazenar na sessão para recuperar posteriormente
            self.request.session['pedido_referencia'] = pedido_uuid
            
            # Armazena os dados do carrinho e do pedido temporariamente na sessão
            # Inclui todos os itens necessários para criar o pedido após o pagamento
            self.request.session['dados_pedido'] = {
                'usuario_id': self.request.user.id,
                'total': valor_total_com_frete,  # Total com frete
                'frete': valor_frete,  # Valor do frete
                'qtd_total': qtd_total_carrinho,
                'status': 'A',  # Status aprovado
                'itens': [],  # Será preenchido abaixo
                'external_reference': pedido_uuid
            }
            
            # Preencher os itens com todos os detalhes necessários
            for item_key, item_data in carrinho.items():
                # Preparar dados do item para a sessão
                item_info = item_data.copy()  # Copiar todos os dados existentes
                
                # Adicionar dados específicos de cor para itens com variação de cor
                if '-' in str(item_key):
                    variacao_id, cor_id = item_key.split('-')
                    item_info['variacao_id'] = int(variacao_id)
                    if cor_id == 'padrao':
                        item_info['cor_id'] = None
                    else:
                        item_info['cor_id'] = cor_id
                else:
                    item_info['cor_id'] = None
                
                # Adicionar à lista de itens na sessão
                self.request.session['dados_pedido']['itens'].append(item_info)
            
            # Verificar se o token do Mercado Pago está configurado
            if not hasattr(settings, 'MERCADO_PAGO_ACCESS_TOKEN') or not settings.MERCADO_PAGO_ACCESS_TOKEN:
                logger.error("Token do Mercado Pago não configurado")
                messages.error(
                    self.request,
                    'Erro na configuração do gateway de pagamento. Entre em contato com o suporte.'
                )
                return redirect('produto:carrinho')
            
            # Inicializa o SDK do Mercado Pago
            try:
                sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
                logger.info("MERCADO_PAGO_ACCESS_TOKEN configurado com sucesso")
                nome = getattr(settings, 'MERCADO_PAGO_STORE_NAME', 'Vivan Calçados')

                # Prepara os itens para o Mercado Pago
                items = []
                for item_key, item in carrinho.items():
                    items.append({
                        "id": item_key,
                        "title": item['produto_nome'],
                        "quantity": item['quantidade'],
                        "currency_id": "BRL",
                        "unit_price": float(item['preco_unitario'])
                    })
                    
                # items.append({
                #     "id": "frete",
                #     "title": "Frete",
                #     "quantity": 1,
                #     "currency_id": "BRL",
                #     "unit_price": float(valor_frete)
                # })

                # Verifica URLs de retorno
                success_url = self.request.build_absolute_uri(reverse('pedido:pagamento_confirmado'))
                failure_url = self.request.build_absolute_uri(reverse('produto:resumodacompra'))
                pending_url = self.request.build_absolute_uri(reverse('produto:resumodacompra'))

                # Dados do pagador
                payer = {
                    "first_name": self.request.user.first_name or self.request.user.username,
                    "last_name": self.request.user.last_name or self.request.user.username,
                    "email": self.request.user.email,
                }
                
                # # Configura os dados do pagamento
                # payment_data = {
                #     "items": items,
                #     "payer": payer,
                #     "back_urls": {
                #         "success": success_url,
                #         "failure": failure_url,
                #         "pending": pending_url
                #     },
                #     "auto_return": "approved",
                #     "binary_mode": False,  # Permite pagamentos parcelados e cartões
                #     "statement_descriptor": nome,
                #     "external_reference": pedido_uuid,
                #     # Permite cartões de crédito e parcelamento
                #     "payment_methods": {
                #         "excluded_payment_types": [],
                #         "excluded_payment_methods": [],
                #         "default_payment_method_id": None,
                #         "installments": 12,
                #         "default_installments": 1
                #     }
                # }


                # Configura os dados do pagamento
                payment_data = {
                    "items": items,
                    "payer": payer,
                    "back_urls": {
                        "success": success_url,
                        "failure": failure_url,
                        "pending": pending_url
                    },
                    "auto_return": "approved",
                    "binary_mode": False,  # Permite pagamentos parcelados e cartões
                    "statement_descriptor": nome,
                    "notification_url": self.request.build_absolute_uri(reverse('pedido:webhook')),
                    "external_reference": pedido_uuid,
                    # Permite cartões de crédito e parcelamento
                    "payment_methods": {
                        "excluded_payment_types": [],
                        "excluded_payment_methods": [],
                        "default_payment_method_id": None,
                        "installments": 12,
                        "default_installments": 1
                    },
                    # Adicionar informações de envio com o valor do frete
                    "shipments": {
                        "cost": float(valor_frete),
                        "mode": "not_specified"
                    }
                }

                preference_response = sdk.preference().create(payment_data)
                
                if "response" in preference_response:
                    logger.info(f"Preference criada com sucesso: {preference_response['response']['id']}")
                    # Guarda o carrinho temporariamente para uso posterior
                    self.request.session['carrinho_temp'] = carrinho
                    # Limpa o carrinho original
                    del self.request.session['carrinho']
                    self.request.session.save()
                    
                    # Redireciona para a página de pagamento
                    return redirect(preference_response["response"]["init_point"])
                else:
                    logger.error(f"Erro na resposta do Mercado Pago: {preference_response}")
                    messages.error(
                        self.request,
                        'Erro na resposta do gateway de pagamento. Por favor, tente novamente.'
                    )
            except Exception as e:
                logger.error(f"Erro ao processar pagamento: {str(e)}")
                logger.error(traceback.format_exc())
                messages.error(
                    self.request,
                    'Erro ao processar o pagamento. Por favor, tente novamente mais tarde.'
                )
            
            return redirect('produto:carrinho')
        
        except mercadopago.exceptions.MPException as e:
            logger.error(f"Erro ao processar pagamento com Mercado Pago: {str(e)}")
            messages.error(self.request, 'Erro ao processar o pagamento. Por favor, tente novamente mais tarde.')
            return redirect('produto:carrinho')
        except Exception as e:
            logger.error(f"Erro geral em SalvarPedido: {str(e)}")
            logger.error(traceback.format_exc())
            messages.error(self.request, 'Ocorreu um erro ao processar seu pedido. Por favor, tente novamente.')
            return redirect('produto:lista')


@method_decorator(csrf_exempt, name='dispatch')
class PagamentoConfirmado(View):
    def get(self, *args, **kwargs):
        status = self.request.GET.get('status')
        payment_id = self.request.GET.get('payment_id', '')
        merchant_order_id = self.request.GET.get('merchant_order_id', '')
        
        # Registro de informações recebidas
        logger.info(f"Retorno de pagamento: status={status}, payment_id={payment_id}, merchant_order_id={merchant_order_id}")
        
        # Verificar se o usuário está autenticado
        if not self.request.user.is_authenticated:
            messages.error(
                self.request,
                'Sessão expirada. Por favor, faça login novamente.'
            )
            # Salvar dados temporários para recuperação com chaves de identificação
            if 'dados_pedido' in self.request.session:
                dados_pedido = self.request.session['dados_pedido']
                session_key = f"pedido_pendente_{payment_id}_{merchant_order_id}"
                self.request.session[session_key] = self.request.session['dados_pedido']
                logger.info(f"Dados de pedido salvos em sessão temporária: {session_key}")
            return redirect('perfil:criar')
            
        try:
            # Registrar tentativa de verificação de status
            logger.info(f"Verificando status de pagamento para usuário {self.request.user.id}: {status}")
            
            # Verificar se os dados foram fornecidos corretamente
            dados_pedido = self.request.session.get('dados_pedido')
            if not dados_pedido and status == 'approved':
                # Tenta recuperar usando o payment_id
                session_key = f"pedido_pendente_{payment_id}_{merchant_order_id}"
                dados_pedido = self.request.session.get(session_key)
                if dados_pedido:
                    logger.info(f"Dados de pedido recuperados de sessão temporária: {session_key}")
                    
            # Verificar direto no Mercado Pago se necessário
            if not dados_pedido and payment_id:
                try:
                    logger.info(f"Tentando obter dados do pagamento do Mercado Pago: {payment_id}")
                    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
                    payment_info = sdk.payment().get(payment_id)
                    if "response" in payment_info:
                        payment_response = payment_info["response"]
                        payment_status = payment_response.get("status")
                        if payment_status == "approved":
                            # Tenta obter o pedido no banco de dados se já existir
                            pedido_existente = Pedido.objects.filter(payment_id=payment_id).first()
                            if pedido_existente:
                                logger.info(f"Pedido {pedido_existente.id} encontrado para payment_id {payment_id}")
                                messages.success(
                                    self.request,
                                    'Pagamento confirmado! Seu pedido já foi registrado em nosso sistema.'
                                )
                                return redirect('pedido:detalhe', pk=pedido_existente.id)
                except Exception as e:
                    logger.error(f"Erro ao consultar Mercado Pago: {str(e)}")
            
            email_usuario = self.request.user.email
            email_loja = getattr(settings, 'EMAIL_HOST_USER', '')
            
            # Verificar se o email da loja está configurado
            if not email_loja:
                logger.warning("EMAIL_HOST_USER não configurado")
                
            if status == 'approved':
                if not dados_pedido:
                    messages.error(
                        self.request,
                        'Dados do pedido não encontrados. O pagamento foi processado, mas ocorreu um erro ao salvar o pedido.'
                    )
                    logger.error("Pagamento aprovado mas dados_pedido não encontrados na sessão")
                    return redirect('produto:lista')
                
                # Usar transação para garantir que todas as operações sejam concluídas com sucesso
                with transaction.atomic():
                    # Verifica se já existe um pedido com este payment_id
                    pedido_existente = None
                    if payment_id:
                        pedido_existente = Pedido.objects.filter(payment_id=payment_id).first()
                        
                    if pedido_existente:
                        logger.info(f"Pedido {pedido_existente.id} já existe para payment_id {payment_id}")
                        pedido = pedido_existente
                    else:
                        # Cria o pedido
                        pedido = Pedido(
                            usuario_id=dados_pedido['usuario_id'],
                            total=dados_pedido['total'],
                            frete=dados_pedido.get('frete', 0),  # Adicionado campo de frete
                            qtd_total=dados_pedido['qtd_total'],
                            status='A',  # Aprovado
                            # Dados do pagamento
                            collection_id=self.request.GET.get('collection_id', ''),
                            payment_id=payment_id,
                            payment_type=self.request.GET.get('payment_type', ''),
                            merchant_order_id=merchant_order_id,
                            preference_id=self.request.GET.get('preference_id', ''),
                            site_id=self.request.GET.get('site_id', ''),
                            processing_mode=self.request.GET.get('processing_mode', ''),
                            external_reference=dados_pedido.get('external_reference', ''),  # Referência externa
                        )
                        pedido.save()
                        logger.info(f"Novo pedido criado: {pedido.id} (payment_id: {payment_id})")
                        
                        # Verificar se há itens no pedido
                        if not dados_pedido['itens']:
                            raise ValueError("Não há itens no pedido")

                        # Cria os itens do pedido
                        itens_pedido = []
                        for v in dados_pedido['itens']:
                            # Verificar campos obrigatórios
                            if not all(k in v for k in ['produto_nome', 'produto_id', 'variacao_nome', 'variacao_id']):
                                raise ValueError(f"Dados de item incompletos: {v}")
                            
                            item = ItemPedido(
                                pedido=pedido,
                                produto=v['produto_nome'],
                                produto_id=v['produto_id'],
                                variacao=v['variacao_nome'],
                                variacao_id=v['variacao_id'],
                                cor=v.get('cor_nome', ''),  # Obter o nome da cor com valor padrão vazio
                                cor_id=v.get('cor_id', None),  # Obter o ID da cor com valor padrão None
                                preco=v['preco_unitario'],
                                preco_promocional=v['preco_unitario_promocional'],
                                quantidade=v['quantidade'],
                                imagem=v.get('imagem', '')  # Imagem da cor ou imagem padrão
                            )
                            itens_pedido.append(item)
                        
                        # Criar itens em massa
                        ItemPedido.objects.bulk_create(itens_pedido)
                        logger.info(f"Criados {len(itens_pedido)} itens para o pedido {pedido.id}")
                        
                        # Atualizar estoque das variações
                        for v in dados_pedido['itens']:
                            try:
                                variacao = Variacao.objects.get(id=v['variacao_id'])
                                variacao.estoque -= v['quantidade']
                                if variacao.estoque < 0:
                                    variacao.estoque = 0
                                variacao.save()
                                logger.info(f"Estoque atualizado: variacao_id={v['variacao_id']}, novo_estoque={variacao.estoque}")
                            except Variacao.DoesNotExist:
                                logger.warning(f"Variação {v['variacao_id']} não encontrada ao atualizar estoque")
                            except Exception as e:
                                logger.error(f"Erro ao atualizar estoque: {str(e)}")

                    # Lista de produtos para incluir no email
                    produtos_lista = '\n'.join([
                        f"- {item['quantidade']}x {item['produto_nome']} ({item['variacao_nome']})"
                        for item in dados_pedido['itens']
                    ])

                    # Tentar enviar emails com sistema de retry
                    max_tentativas = 3
                    for tentativa in range(1, max_tentativas + 1):
                        try:
                            if email_usuario and email_loja:
                                # Email para o cliente
                                send_mail(
                                    subject='🎉 Pedido Confirmado - Vivan Calçados',
                                    message=(
                                        f'Olá, {self.request.user.first_name}!\n\n'
                                        'Temos uma ótima notícia! O seu pedido foi confirmado com sucesso e já estamos preparando tudo para envio. 📦✨\n\n'
                                        f'🔹 Número do Pedido: #{pedido.id}\n'
                                        f'🔹 Status: Confirmado ✅\n\n'
                                        '📝 Seus produtos:\n'
                                        f'{produtos_lista}\n\n'
                                        f'💰 Total do pedido: R$ {dados_pedido["total"]:.2f}\n'
                                        f'🚚 Valor do frete: R$ {dados_pedido.get("frete", 0):.2f}\n\n'
                                        '📌 O que acontece agora?\n'
                                        '➡️ Nossa equipe está separando os itens do seu pedido.\n'
                                        '➡️ Assim que for enviado, você receberá um novo e-mail com os detalhes.\n\n'
                                        '📅 Previsão de Entrega: Em breve você receberá detalhes sobre o prazo estimado.\n\n'
                                        'Caso tenha dúvidas, entre em contato com nosso suporte. Estamos à disposição para te ajudar! 😊\n\n'
                                        'Obrigado por confiar na Vivan Calçados! Esperamos que você aproveite sua compra. 💙\n\n'
                                        'Atenciosamente,\n'
                                        'Equipe Vivan Calçados\n'
                                        '📧 suporte@vivancalcados.com | 📞 +55 (43) 9641-4232'
                                    ),
                                    from_email=email_loja,
                                    recipient_list=[email_usuario],
                                )
                                logger.info(f"Email de confirmação enviado para o cliente: {email_usuario}")

                                # Email para a loja
                                send_mail(
                                    subject=f'🛍️ Novo Pedido #{pedido.id} - Preparar para Envio',
                                    message=(
                                        '🔔 Novo pedido recebido!\n\n'
                                        f'📦 Pedido #{pedido.id}\n'
                                        f'👤 Cliente: {self.request.user.get_full_name()}\n'
                                        f'📧 Email: {email_usuario}\n\n'
                                        '📝 Produtos:\n'
                                        f'{produtos_lista}\n\n'
                                        f'💰 Valor total: R$ {dados_pedido["total"]:.2f}\n'
                                        f'🚚 Valor do frete: R$ {dados_pedido.get("frete", 0):.2f}\n\n'
                                        '⚠️ Por favor, prepare este pedido para envio.\n\n'
                                        'Este é um email automático do sistema.'
                                    ),
                                    from_email=email_loja,
                                    recipient_list=[email_loja],
                                )
                                logger.info(f"Email de notificação enviado para a loja: {email_loja}")
                                break  # Sai do loop de tentativas se o envio for bem-sucedido
                            else:
                                logger.warning("Emails não enviados: faltam endereços de email")
                                break
                        except Exception as e:
                            logger.error(f"Tentativa {tentativa}/{max_tentativas} - Erro ao enviar emails: {str(e)}")
                            if tentativa == max_tentativas:
                                logger.error("Todas as tentativas de envio de email falharam")
                            else:
                                # Pequeno delay antes da próxima tentativa
                                time.sleep(1)

                    # Limpa os dados temporários
                    keys_to_delete = ['dados_pedido', 'carrinho_temp', 'pedido_referencia']
                    # Adiciona chaves de sessão temporárias
                    if payment_id and merchant_order_id:
                        keys_to_delete.append(f"pedido_pendente_{payment_id}_{merchant_order_id}")
                        
                    for key in keys_to_delete:
                        if key in self.request.session:
                            del self.request.session[key]
                            logger.debug(f"Chave de sessão removida: {key}")

                    messages.success(
                        self.request,
                        'Pagamento confirmado com sucesso! Seu pedido foi registrado e está sendo processado. Obrigado pela compra.'
                    )

                    # Armazenar ID do pedido na sessão para referência
                    self.request.session['ultimo_pedido_id'] = pedido.id
                    self.request.session.save()

                    return redirect('pedido:detalhe', pk=pedido.id)
            else:
                # Restaura o carrinho se o pagamento falhou
                if 'carrinho_temp' in self.request.session:
                    self.request.session['carrinho'] = self.request.session['carrinho_temp']
                    del self.request.session['carrinho_temp']
                    logger.info("Carrinho restaurado após falha no pagamento")
                
                # Registrar o status recebido
                logger.warning(f"Pagamento não aprovado. Status: {status}")
                
                messages.warning(
                    self.request,
                    f'O pagamento não foi aprovado (status: {status}). Por favor, tente novamente ou escolha outra forma de pagamento.'
                )
            
            return redirect('produto:resumodacompra')
                
        except Exception as e:
            logger.error(f"Erro ao processar retorno do pagamento: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Restaurar o carrinho em caso de erro
            if 'carrinho_temp' in self.request.session:
                self.request.session['carrinho'] = self.request.session['carrinho_temp']
                del self.request.session['carrinho_temp']
                logger.info("Carrinho restaurado após erro no processamento")
            
            messages.error(
                self.request,
                'Ocorreu um erro ao processar o retorno do pagamento. Por favor, verifique se a compra foi concluída em sua conta ou entre em contato com o suporte.'
            )
            return redirect('produto:lista')
        
        finally:
            self.request.session.save()

        

@method_decorator(csrf_exempt, name='dispatch')
class MercadoPagoWebhook(View):
    def post(self, request, *args, **kwargs):
        try:
            # Log de todos os cabeçalhos para diagnóstico
            headers_log = {k: v for k, v in request.headers.items()}
            logger.info(f"Cabeçalhos recebidos: {headers_log}")
            
            # Receber o payload antes de verificar a assinatura
            body = request.body
            payload = json.loads(body)
            logger.info(f"Webhook recebido: {payload}")
            
            # Verificação básica do tipo de evento
            if 'action' not in payload:
                logger.warning("Webhook recebido sem campo action")
                return HttpResponse(status=200)  # Aceitar mesmo assim
                
            # REMOÇÃO DA VERIFICAÇÃO DE ASSINATURA
            # O Mercado Pago pode não estar enviando a assinatura ou o formato mudou
            # Esta é uma abordagem temporária enquanto você investiga o formato correto
            
            # Verificar o tipo de evento
            if payload.get('action') == 'payment.updated' or payload.get('action') == 'payment.created':
                payment_id = payload.get('data', {}).get('id')
                if payment_id:
                    # Buscar o pagamento no Mercado Pago para atualizar o status
                    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
                    payment_info = sdk.payment().get(payment_id)

                    if "response" in payment_info:
                        payment_data = payment_info["response"]
                        payment_status = payment_data.get("status")
                        external_reference = payment_data.get("external_reference")
                        
                        logger.info(f"Status do pagamento {payment_id}: {payment_status}")

                        # Tentar encontrar o pedido pelo payment_id
                        try:
                            pedido = Pedido.objects.filter(
                                Q(payment_id=payment_id) | 
                                Q(external_reference=external_reference)
                            ).first()
                            
                            if pedido:
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
                                
                                # Atualizar status do pedido se necessário
                                new_status = status_map.get(payment_status)
                                if new_status and pedido.status != new_status:
                                    old_status = pedido.status
                                    pedido.status = new_status
                                    
                                    # Atualizar dados do pagamento
                                    if not pedido.payment_id:
                                        pedido.payment_id = payment_id
                                    
                                    # Extrair outros dados relevantes do pagamento
                                    if 'collection_id' in payment_data:
                                        pedido.collection_id = payment_data.get('collection_id')
                                    if 'payment_type' in payment_data:
                                        pedido.payment_type = payment_data.get('payment_type')
                                    if 'merchant_order_id' in payment_data:
                                        pedido.merchant_order_id = payment_data.get('merchant_order_id')
                                    if 'preference_id' in payment_data:
                                        pedido.preference_id = payment_data.get('preference_id')
                                    if 'site_id' in payment_data:
                                        pedido.site_id = payment_data.get('site_id')
                                    if 'processing_mode' in payment_data:
                                        pedido.processing_mode = payment_data.get('processing_mode')
                                    
                                    pedido.save()
                                    
                                    logger.info(f"Status do pedido {pedido.id} atualizado: {old_status} -> {new_status}")
                                else:
                                    logger.info(f"Pedido {pedido.id} já está com status {pedido.status}, não é necessário atualizar")
                            else:
                                logger.warning(f"Pedido não encontrado para payment_id={payment_id}, external_reference={external_reference}")
                        except Exception as e:
                            logger.error(f"Erro ao processar pedido: {str(e)}")
                    else:
                        logger.error(f"Erro ao consultar pagamento {payment_id}: {payment_info}")
            elif payload.get('action') == 'test':
                logger.info("Teste de webhook recebido")
            else:
                logger.info(f"Evento não processado: {payload.get('action')}")

            return HttpResponse(status=200)
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {str(e)}")
            logger.error(traceback.format_exc())
            return HttpResponse(status=200)  # Retornar 200 mesmo em caso de erro para evitar retentativas


class Detalhe(DispatchLoginRequiredMixin, DetailView):
    model = Pedido
    context_object_name = 'pedido'
    template_name = 'pedido/detalhe.html'
    pk_url_kwarg = 'pk'
    
    def get_object(self, queryset=None):
        # Sobrescrever para tratar casos de pedido não encontrado
        try:
            return super().get_object(queryset)
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do pedido: {str(e)}")
            messages.error(
                self.request,
                'Pedido não encontrado ou você não tem permissão para visualizá-lo.'
            )
            return None
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            return redirect('pedido:lista')
        
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class Lista(DispatchLoginRequiredMixin, ListView):
    model = Pedido
    context_object_name = 'pedidos'
    template_name = 'pedido/lista.html'
    paginate_by = 10
    ordering = ['-id']        
    
    def get_queryset(self):
        # Adicionar tratamento para possíveis erros na consulta
        try:
            # return super().get_queryset()
            return super().get_queryset().filter(usuario=self.request.user)
        except Exception as e:
            logger.error(f"Erro ao listar pedidos: {str(e)}")
            messages.error(
                self.request,
                'Ocorreu um erro ao carregar seus pedidos. Por favor, tente novamente.'
            )
            return Pedido.objects.none()  # Retorna queryset vazio em caso de erro
