# Generated by Django 5.1.5 on 2025-03-12 18:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produto', '0007_alter_cor_codigo_hex_alter_cor_nome'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cor',
            options={},
        ),
        migrations.RemoveField(
            model_name='cor',
            name='nome',
        ),
        migrations.AlterField(
            model_name='cor',
            name='codigo_hex',
            field=models.CharField(max_length=7, verbose_name='Código Hex da Cor'),
        ),
        migrations.AlterField(
            model_name='cor',
            name='imagem',
            field=models.ImageField(blank=True, null=True, upload_to='cores/', verbose_name='Imagem da Cor'),
        ),
    ]
