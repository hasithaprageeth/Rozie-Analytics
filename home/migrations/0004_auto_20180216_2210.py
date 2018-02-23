# Generated by Django 2.0.2 on 2018-02-16 22:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_auto_20180216_2200'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tweets',
            name='cluster_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.Clusters'),
        ),
        migrations.AlterField(
            model_name='tweets',
            name='tweet_id',
            field=models.CharField(max_length=50, primary_key=True, serialize=False),
        ),
    ]
