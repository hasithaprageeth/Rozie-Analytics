# Generated by Django 2.0.2 on 2018-02-16 21:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Clusters',
            fields=[
                ('cluster_id', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('summary', models.CharField(max_length=100)),
                ('tweet_rate', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Tweets',
            fields=[
                ('tweet_id', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('preprocessed_text', models.CharField(max_length=200)),
                ('full_text', models.CharField(max_length=400)),
                ('created_at', models.CharField(max_length=50)),
                ('assignment_time', models.CharField(max_length=50)),
                ('tweet', models.CharField(max_length=1000)),
                ('cluster_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.Clusters')),
            ],
        ),
        migrations.RemoveField(
            model_name='choice',
            name='question',
        ),
        migrations.DeleteModel(
            name='Choice',
        ),
        migrations.DeleteModel(
            name='Question',
        ),
    ]
