# Generated by Django 4.2.13 on 2024-06-12 19:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0008_charginglogic_is_enabled_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='first_login',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('admin', 'Admin'), ('user', 'User')], default='user', max_length=5),
        ),
        migrations.AlterField(
            model_name='charginglogic',
            name='amount_rate',
            field=models.CharField(choices=[('second', 'Per Second'), ('minute', 'Per Minute'), ('hour', 'Per Hour'), ('day', 'Per Day'), ('week', 'Per Week'), ('month', 'Per Month')], max_length=10),
        ),
        migrations.AlterField(
            model_name='location',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='location',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions'),
        ),
    ]