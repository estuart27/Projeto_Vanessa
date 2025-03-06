from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'produto'

urlpatterns = [
    path('', views.ListaProdutos.as_view(), name="lista"),
    path('produto/<slug:slug>/', views.DetalheProduto.as_view(), name="detalhe"),
    path('adicionaraocarrinho/', views.AdicionarAoCarrinho.as_view(),
         name="adicionaraocarrinho"),
    path('removerdocarrinho/', views.RemoverDoCarrinho.as_view(),
         name="removerdocarrinho"),
    path('carrinho/', views.Carrinho.as_view(), name="carrinho"),
    path('resumodacompra/', views.ResumoDaCompra.as_view(), name="resumodacompra"),
    path('busca/', views.Busca.as_view(), name="busca"),
    path('contact/', views.contact, name="contact"),
    path('blog/', views.ListaPostagensView.as_view(), name='blog'),
    path('post/<slug:slug>/', views.DetalhesPostagemView.as_view(), name='detalhes_post'),

    #Novos 
     path('index/', views.index, name="index"),
     path('about/', views.about, name="about"),
     path('contact/', views.contact, name="contact"),
     path('gerar-pagamento/', views.GerarPagamentoMercadoPago.as_view(), name='gerar_pagamento'),
     path('blog/', views.ListaPostagensView.as_view(), name='blog'),
     path('post/<slug:slug>/', views.DetalhesPostagemView.as_view(), name='detalhes_post'),
     path('postagem/<slug:slug>/comentar/', views.adicionar_comentario, name='adicionar_comentario'),
     path('termos-e-condicoes/', views.termos, name='termos'),
     path('politica-de-privacidade/', views.politica, name='politica'),
     path('trocas-e-devolucoes/', views.troca, name='troca'),
     



] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
