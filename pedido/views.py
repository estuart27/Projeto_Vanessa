from django.shortcuts import redirect, reverse
from django.views.generic import ListView, DetailView
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import mercadopago
from django.conf import settings

from .models import Pedido, ItemPedido
from produto.models import Variacao

from utils import utils


class DispatchLoginRequiredMixin(View):
    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('perfil:criar')

        return super().dispatch(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(usuario=self.request.user)
        return qs


class Pagar(DispatchLoginRequiredMixin, DetailView):
    template_name = 'pedido/pagar.html'
    model = Pedido
    pk_url_kwarg = 'pk'
    context_object_name = 'pedido'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = self.object
        
        # Criar a mensagem
        itens_pedido = pedido.itempedido_set.all()
        mensagem = "Olá! Gostaria de realizar o pagamento do \n\n"

        for item in itens_pedido:
            mensagem += f"pedido N°.*{pedido.id}*\n"

        # Criar o link do WhatsApp
        numero_destino = '5543996341638'  # Substitua pelo número de destino
        mensagem_url = f"https://wa.me/{numero_destino}?text={mensagem.replace(' ', '%20')}"

        # Adiciona o link ao contexto para uso no template
        context['whatsapp_link'] = mensagem_url
        return context



from django.urls import reverse

class SalvarPedido(View):
    template_name = 'pedido/pagar.html'

    def get(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            messages.error(
                self.request,
                'Você precisa fazer login.'
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
        bd_variacoes = list(
            Variacao.objects.select_related('produto')
            .filter(id__in=carrinho_variacao_ids)
        )

        for variacao in bd_variacoes:
            vid = str(variacao.id)

            estoque = variacao.estoque
            qtd_carrinho = carrinho[vid]['quantidade']
            preco_unt = carrinho[vid]['preco_unitario']
            preco_unt_promo = carrinho[vid]['preco_unitario_promocional']

            if estoque < qtd_carrinho:
                carrinho[vid]['quantidade'] = estoque
                carrinho[vid]['preco_quantitativo'] = estoque * preco_unt
                carrinho[vid]['preco_quantitativo_promocional'] = estoque * preco_unt_promo

                messages.error(
                    self.request,
                    'Estoque insuficiente para alguns produtos do seu carrinho.'
                )
                self.request.session.save()
                return redirect('produto:carrinho')

        qtd_total_carrinho = utils.cart_total_qtd(carrinho)
        valor_total_carrinho = utils.cart_totals(carrinho)

        # Armazena os dados do carrinho e do pedido temporariamente na sessão
        self.request.session['dados_pedido'] = {
            'usuario_id': self.request.user.id,
            'total': valor_total_carrinho,
            'qtd_total': qtd_total_carrinho,
            'status': 'A',
            'itens': list(carrinho.values())
        }

        # Inicializa o SDK do Mercado Pago
        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        nome = settings.MERCADO_PAGO_STORE_NAME

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

        # Configura os dados do pagamento
        payment_data = {
            "items": items,
            "external_reference": str(self.request.user.id),  # Usando o ID do usuário como referência temporária
            "back_urls": {
                "success": self.request.build_absolute_uri(reverse('pedido:pagamento_confirmado')),
                "failure": self.request.build_absolute_uri(reverse('produto:resumodacompra')),
                "pending": self.request.build_absolute_uri(reverse('produto:resumodacompra'))

            },
            "auto_return": "approved",
            "binary_mode": True,
            "statement_descriptor": nome
        }

        try:
            preference_response = sdk.preference().create(payment_data)
            
            if "response" in preference_response:
                # Guarda o carrinho temporariamente para uso posterior
                self.request.session['carrinho_temp'] = carrinho
                # Limpa o carrinho original
                del self.request.session['carrinho']
                self.request.session.save()
                
                return redirect(preference_response["response"]["init_point"])
            else:
                messages.error(
                    self.request,
                    'Erro na resposta do Mercado Pago.'
                )
        except Exception as e:
            messages.error(
                self.request,
                f'Erro ao processar pagamento: {str(e)}'
            )
        
        return redirect('pedido:lista')

    


@method_decorator(csrf_exempt, name='dispatch')
class PagamentoConfirmado(View):
    def get(self, *args, **kwargs):
        status = self.request.GET.get('status')
        external_reference = self.request.GET.get('external_reference')
        
        try:
            # Se o pagamento foi aprovado
            if status == 'approved':
                # Recupera os dados do pedido da sessão
                dados_pedido = self.request.session.get('dados_pedido')
                
                if dados_pedido:
                    # Cria o pedido
                    pedido = Pedido(
                        usuario_id=dados_pedido['usuario_id'],
                        total=dados_pedido['total'],
                        qtd_total=dados_pedido['qtd_total'],
                        status='P',  # Pago
                    )
                    pedido.save()

                    # Cria os itens do pedido
                    ItemPedido.objects.bulk_create(
                        [
                            ItemPedido(
                                pedido=pedido,
                                produto=v['produto_nome'],
                                produto_id=v['produto_id'],
                                variacao=v['variacao_nome'],
                                variacao_id=v['variacao_id'],
                                preco=v['preco_quantitativo'],
                                preco_promocional=v['preco_quantitativo_promocional'],
                                quantidade=v['quantidade'],
                                imagem=v['imagem'],
                            ) for v in dados_pedido['itens']
                        ]
                    )

                    # Limpa os dados temporários da sessão
                    if 'dados_pedido' in self.request.session:
                        del self.request.session['dados_pedido']
                    if 'carrinho_temp' in self.request.session:
                        del self.request.session['carrinho_temp']

                    messages.success(
                        self.request,
                        'Pagamento confirmado com sucesso! Obrigado pela compra.'
                    )
                    return redirect('produto:lista')
                else:
                    messages.error(
                        self.request,
                        'Dados do pedido não encontrados.'
                    )
                    return redirect('produto:resumodacompra')
            else:
                # Se o pagamento falhou, restaura o carrinho
                if 'carrinho_temp' in self.request.session:
                    self.request.session['carrinho'] = self.request.session['carrinho_temp']
                    del self.request.session['carrinho_temp']
                
                messages.error(
                    self.request,
                    'Erro no pagamento. Por favor, tente novamente.'
                )
                return redirect('produto:resumodacompra')
                
        except Exception as e:
            messages.warning(
                self.request,
                'Erro ao processar retorno do pagamento. Entre em contato com o suporte.'
            )
            return redirect('produto:lista')
        
        finally:
            self.request.session.save()



class Detalhe(DispatchLoginRequiredMixin, DetailView):
    model = Pedido
    context_object_name = 'pedido'
    template_name = 'pedido/detalhe.html'
    pk_url_kwarg = 'pk'
    


class Lista(DispatchLoginRequiredMixin, ListView):
    model = Pedido
    context_object_name = 'pedidos'
    template_name = 'pedido/lista.html'
    paginate_by = 10
    ordering = ['-id']