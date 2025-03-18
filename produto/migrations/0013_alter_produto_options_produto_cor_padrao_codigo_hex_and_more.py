# Generated by Django 5.1.5 on 2025-03-15 22:45

import imagekit.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produto', '0012_produto_cor_padrao'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='produto',
            options={},
        ),
        migrations.AddField(
            model_name='produto',
            name='cor_padrao_codigo_hex',
            field=models.CharField(choices=[('#000000', 'Preto'), ('#FFFFFF', 'Branco'), ('#FF0000', 'Vermelho'), ('#0000FF', 'Azul'), ('#008000', 'Verde'), ('#FFFF00', 'Amarelo'), ('#FFA500', 'Laranja'), ('#800080', 'Roxo'), ('#A52A2A', 'Marrom'), ('#C0C0C0', 'Cinza'), ('#FFC0CB', 'Rosa'), ('#FFD700', 'Dourado'), ('#00FFFF', 'Ciano'), ('#808080', 'Grafite'), ('#8B4513', 'Marrom Escuro'), ('#FF4500', 'Vermelho Alaranjado'), ('#4B0082', 'Índigo'), ('#00FF00', 'Verde Limão'), ('#FF1493', 'Rosa Choque'), ('#000080', 'Azul Marinho')], default='#000000', max_length=7, verbose_name='Código Hex da Cor Padrão'),
        ),
        migrations.AddField(
            model_name='produto',
            name='cor_padrao_nome',
            field=models.CharField(default='Padrão', max_length=50, verbose_name='Nome da Cor Padrão'),
        ),
        migrations.AlterField(
            model_name='produto',
            name='imagem',
            field=imagekit.models.fields.ProcessedImageField(default=11, help_text='Esta imagem será usada para a cor padrão do produto', upload_to='produtos/', verbose_name='Imagem da cor padrão'),
            preserve_default=False,
        ),
    ]
