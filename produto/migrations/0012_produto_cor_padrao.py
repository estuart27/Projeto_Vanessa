# Generated by Django 5.1.5 on 2025-03-15 22:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produto', '0011_remove_produto_cor_padrao_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='cor_padrao',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='produtos_padrao', to='produto.cor', verbose_name='Cor Padrão'),
        ),
    ]
