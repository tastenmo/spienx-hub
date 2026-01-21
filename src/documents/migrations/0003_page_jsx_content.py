# Generated migration to add jsx_content field to Page

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_alter_page_options_rename_document_page_build_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='jsx_content',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
