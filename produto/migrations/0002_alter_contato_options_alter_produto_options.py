# Generated by Django 5.1.5 on 2025-02-20 21:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('produto', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='contato',
            options={'verbose_name': 'Contato', 'verbose_name_plural': 'Feedback dos Clientes'},
        ),
        migrations.AlterModelOptions(
            name='produto',
            options={'verbose_name': 'Produtos', 'verbose_name_plural': 'Produtos da Loja'},
        ),
    ]
