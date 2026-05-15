from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_page_jsx_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='section',
            name='level',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='section',
            name='order_index',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='section',
            name='parent_section',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, related_name='children', to='documents.section'),
        ),
        migrations.AlterModelOptions(
            name='section',
            options={'ordering': ['order_index', 'start_line', 'id']},
        ),
    ]
