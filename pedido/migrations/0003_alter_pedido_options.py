# Generated by Django 5.1.5 on 2025-02-20 21:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pedido', '0002_alter_itempedido_id_alter_pedido_id'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='pedido',
            options={'verbose_name': 'Pedidos', 'verbose_name_plural': 'Pedidos Feitos'},
        ),
    ]
