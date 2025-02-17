from django.forms.models import BaseInlineFormSet
from django import forms
from django.core.exceptions import ValidationError
from .models import Produto,Comentario,Contato  # Importe seu modelo Produto

class ContatoForm(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ['nome', 'email', 'motivo', 'mensagem']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Seu Nome'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Seu E-mail'
            }),
            'motivo': forms.Select(attrs={
                'class': 'form-control'
            }),
            'mensagem': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Digite sua mensagem aqui',
                'rows': '7'
            }),
        }


class VariacaoObrigatoria(BaseInlineFormSet):
    def _construct_form(self, i, **kwargs):
        form = super(VariacaoObrigatoria, self)._construct_form(i, **kwargs)
        form.empty_permitted = False
        return form
    
class FormularioComentario(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['conteudo']
        widgets = {
            'conteudo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Digite seu comentário aqui...'
            }),
        }
        labels = {
            'conteudo': 'Comentário'
        }