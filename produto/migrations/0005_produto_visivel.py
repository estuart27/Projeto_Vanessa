# Generated by Django 5.0.2 on 2025-02-08 14:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produto', '0004_alter_produto_imagem'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='visivel',
            field=models.BooleanField(default=True, verbose_name='Visível na tela de vendas'),
        ),
    ]
