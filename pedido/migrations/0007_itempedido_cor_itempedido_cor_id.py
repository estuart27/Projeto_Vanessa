# Generated by Django 5.1.5 on 2025-03-13 18:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedido', '0006_pedido_external_reference_pedido_ultima_atualizacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='itempedido',
            name='cor',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='itempedido',
            name='cor_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
