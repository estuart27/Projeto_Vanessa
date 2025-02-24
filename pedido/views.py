from django.shortcuts import redirect, reverse, get_object_or_404
from django.views.generic import ListView, DetailView
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import mercadopago
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
import logging
import traceback
from django.db import transaction


from .models import Pedido, ItemPedido
from produto.models import Variacao, Produto


from utils import utils
from urllib.parse import quote

# Configurar logger para registrar erros
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
            
        # Calcular o total
        cart_total = sum(item['preco_quantitativo'] for item in carrinho.values())
        pedido_id = request.session.get('pedido_id', 'N/A')

        # Criar a mensagem profissional
        mensagem = (
            f"🔹 *Solicitação de Pagamento*\n\n"
            f"📌 *Pedido Nº {pedido_id}*\n"
            f"🛍️ *Itens do Pedido:*\n"
        )

        for item in carrinho.values():
            mensagem += f"   - {item['produto_nome']} ({item['variacao_nome']}) — Qtd: {item['quantidade']}\n"

        mensagem += (
            f"\n💰 *Valor Total:* R$ {cart_total:.2f}\n"
            f"Por favor, me informe os detalhes do pagamento.\n"
            f"Agradeço pela preferência! 😊"
        )

        # Verificar configuração do número de WhatsApp
        whatsapp_number = getattr(settings, 'WHATSAPP_NUMBER', "5543996341638")
        if not whatsapp_number:
            logger.error("Número de WhatsApp não configurado")
            messages.error(
                request,
                'Erro na configuração do sistema de pagamento. Entre em contato com o suporte.'
            )
            return redirect('produto:lista')

        # Gerar a URL do WhatsApp
        whatsapp_url = f"https://wa.me/{whatsapp_number}?text={quote(mensagem)}"

        return redirect(whatsapp_url)
    except Exception as e:
        logger.error(f"Erro no pagamento via WhatsApp: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(
            request,
            'Ocorreu um erro ao processar o pagamento. Por favor, tente novamente ou entre em contato com o suporte.'
        )
        return redirect('produto:lista')


#Viwes Pedidos 
class SalvarPedido(View):
    template_name = 'pedido/pagar.html'

    def get(self, *args, **kwargs):
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

            carrinho = self.request.session.get('carrinho')
            carrinho_variacao_ids = [v for v in carrinho]
            
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
            
            # Verificar se todas as variações foram encontradas
            if len(bd_variacoes) != len(carrinho_variacao_ids):
                messages.error(
                    self.request,
                    'Alguns produtos no seu carrinho não estão mais disponíveis. O carrinho foi atualizado.'
                )
                # Remover variações que não existem mais
                for variacao_id in list(carrinho.keys()):
                    if int(variacao_id) not in [v.id for v in bd_variacoes]:
                        del carrinho[variacao_id]
                self.request.session.save()
                return redirect('produto:carrinho')

            for variacao in bd_variacoes:
                vid = str(variacao.id)

                # Verificar se a variação ainda está no carrinho
                if vid not in carrinho:
                    continue

                estoque = variacao.estoque
                qtd_carrinho = carrinho[vid]['quantidade']
                preco_unt = carrinho[vid]['preco_unitario']
                preco_unt_promo = carrinho[vid]['preco_unitario_promocional']

                if estoque < qtd_carrinho:
                    carrinho[vid]['quantidade'] = estoque
                    carrinho[vid]['preco_quantitativo'] = estoque * preco_unt
                    carrinho[vid]['preco_quantitativo_promocional'] = estoque * preco_unt_promo

                    messages.warning(
                        self.request,
                        f'Estoque insuficiente para o produto "{carrinho[vid]["produto_nome"]}". Quantidade ajustada automaticamente.'
                    )
                    
                # Verificar se o preço foi alterado desde a adição ao carrinho
                preco_atual = variacao.preco
                preco_atual_promo = variacao.preco_promocional
                
                if preco_atual != preco_unt or (preco_atual_promo and preco_atual_promo != preco_unt_promo):
                    carrinho[vid]['preco_unitario'] = preco_atual
                    carrinho[vid]['preco_unitario_promocional'] = preco_atual_promo
                    carrinho[vid]['preco_quantitativo'] = qtd_carrinho * preco_atual
                    carrinho[vid]['preco_quantitativo_promocional'] = qtd_carrinho * preco_atual_promo if preco_atual_promo else 0
                    
                    messages.info(
                        self.request,
                        f'O preço do produto "{carrinho[vid]["produto_nome"]}" foi atualizado no seu carrinho.'
                    )
                    
            self.request.session.save()
            
            # Recalcular totais após atualizações
            qtd_total_carrinho = utils.cart_total_qtd(carrinho)
            valor_total_carrinho = utils.cart_totals(carrinho)
            
            # Verificar se ainda há itens no carrinho após as atualizações
            if not carrinho:
                messages.error(
                    self.request,
                    'Seu carrinho está vazio após as atualizações de estoque.'
                )
                return redirect('produto:lista')

            # Armazena os dados do carrinho e do pedido temporariamente na sessão
            self.request.session['dados_pedido'] = {
                'usuario_id': self.request.user.id,
                'total': valor_total_carrinho,
                'qtd_total': qtd_total_carrinho,
                'status': 'A',
                'itens': list(carrinho.values())
            }

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
                nome = getattr(settings, 'MERCADO_PAGO_STORE_NAME', 'Vivan Calçados')

                # Prepara os itens para o Mercado Pago
                items = []
                for item_id, item in carrinho.items():
                    items.append({
                        "id": item_id,
                        "title": item['produto_nome'],
                        "quantity": item['quantidade'],
                        "currency_id": "BRL",
                        "unit_price": float(item['preco_unitario'])
                    })

                # Verifica URLs de retorno
                success_url = self.request.build_absolute_uri(reverse('pedido:pagamento_confirmado'))
                failure_url = self.request.build_absolute_uri(reverse('produto:resumodacompra'))
                pending_url = self.request.build_absolute_uri(reverse('produto:resumodacompra'))

                # Configura os dados do pagamento
                payment_data = {
                    "items": items,
                    "external_reference": str(self.request.user.id),  # Usando o ID do usuário como referência temporária
                    "back_urls": {
                        "success": success_url,
                        "failure": failure_url,
                        "pending": pending_url
                    },
                    "auto_return": "approved",
                    "binary_mode": True,
                    "statement_descriptor": nome
                }

                preference_response = sdk.preference().create(payment_data)
                
                if "response" in preference_response:
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
        except Exception as e:
            logger.error(f"Erro geral em SalvarPedido: {str(e)}")
            logger.error(traceback.format_exc())
            messages.error(
                self.request,
                'Ocorreu um erro ao processar seu pedido. Por favor, tente novamente.'
            )
            return redirect('produto:lista')


@method_decorator(csrf_exempt, name='dispatch')
class PagamentoConfirmado(View):
    def get(self, *args, **kwargs):
        status = self.request.GET.get('status')
        
        # Verificar se o usuário está autenticado
        if not self.request.user.is_authenticated:
            messages.error(
                self.request,
                'Sessão expirada. Por favor, faça login novamente.'
            )
            # Salvar dados temporários para recuperação
            if 'dados_pedido' in self.request.session:
                self.request.session['pedido_pendente'] = self.request.session['dados_pedido']
            return redirect('perfil:criar')
            
        try:
            email_usuario = self.request.user.email
            email_loja = getattr(settings, 'EMAIL_HOST_USER', '')
            
            # Verificar se o email da loja está configurado
            if not email_loja:
                logger.warning("EMAIL_HOST_USER não configurado")
                
            if status == 'approved':
                dados_pedido = self.request.session.get('dados_pedido')
                
                if not dados_pedido:
                    messages.error(
                        self.request,
                        'Dados do pedido não encontrados. O pagamento foi processado, mas ocorreu um erro ao salvar o pedido.'
                    )
                    logger.error("Pagamento aprovado mas dados_pedido não encontrados na sessão")
                    return redirect('produto:lista')
                
                # Usar transação para garantir que todas as operações sejam concluídas com sucesso
                with transaction.atomic():
                    # Cria o pedido
                    pedido = Pedido(
                        usuario_id=dados_pedido['usuario_id'],
                        total=dados_pedido['total'],
                        qtd_total=dados_pedido['qtd_total'],
                        status='P',  # Pago
                        # Dados do pagamento
                        collection_id=self.request.GET.get('collection_id', ''),
                        payment_id=self.request.GET.get('payment_id', ''),
                        payment_type=self.request.GET.get('payment_type', ''),
                        merchant_order_id=self.request.GET.get('merchant_order_id', ''),
                        preference_id=self.request.GET.get('preference_id', ''),
                        site_id=self.request.GET.get('site_id', ''),
                        processing_mode=self.request.GET.get('processing_mode', '')
                    )
                    pedido.save()
                    
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
                            preco=v['preco_quantitativo'],
                            preco_promocional=v['preco_quantitativo_promocional'],
                            quantidade=v['quantidade'],
                            imagem=v.get('imagem', ''),  # Campo opcional
                        )
                        itens_pedido.append(item)
                    
                    # Atualizar estoque das variações
                    for v in dados_pedido['itens']:
                        try:
                            variacao = Variacao.objects.get(id=v['variacao_id'])
                            variacao.estoque -= v['quantidade']
                            if variacao.estoque < 0:
                                variacao.estoque = 0
                            variacao.save()
                        except Variacao.DoesNotExist:
                            logger.warning(f"Variação {v['variacao_id']} não encontrada ao atualizar estoque")
                        except Exception as e:
                            logger.error(f"Erro ao atualizar estoque: {str(e)}")
                    
                    # Criar itens em massa
                    ItemPedido.objects.bulk_create(itens_pedido)

                    # Lista de produtos para incluir no email
                    produtos_lista = '\n'.join([
                        f"- {item['quantidade']}x {item['produto_nome']} ({item['variacao_nome']})"
                        for item in dados_pedido['itens']
                    ])

                    # Tentar enviar emails, mas não falhar se houver erro
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
                                    f'💰 Total do pedido: R$ {dados_pedido["total"]:.2f}\n\n'
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
                                fail_silently=True,
                            )

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
                                    f'💰 Valor total: R$ {dados_pedido["total"]:.2f}\n\n'
                                    '⚠️ Por favor, prepare este pedido para envio.\n\n'
                                    'Este é um email automático do sistema.'
                                ),
                                from_email=email_loja,
                                recipient_list=[email_loja],
                                fail_silently=True,
                            )
                    except Exception as e:
                        logger.error(f"Erro ao enviar emails: {str(e)}")
                        # Não interromper o fluxo por erro nos emails

                    # Limpa os dados temporários
                    if 'dados_pedido' in self.request.session:
                        del self.request.session['dados_pedido']
                    if 'carrinho_temp' in self.request.session:
                        del self.request.session['carrinho_temp']

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
            
            messages.error(
                self.request,
                'Ocorreu um erro ao processar o retorno do pagamento. Por favor, verifique se a compra foi concluída em sua conta ou entre em contato com o suporte.'
            )
            return redirect('produto:lista')
        
        finally:
            self.request.session.save()


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
            return super().get_queryset()
        except Exception as e:
            logger.error(f"Erro ao listar pedidos: {str(e)}")
            messages.error(
                self.request,
                'Ocorreu um erro ao carregar seus pedidos. Por favor, tente novamente.'
            )
            return Pedido.objects.none()  # Retorna queryset vazio em caso de erro