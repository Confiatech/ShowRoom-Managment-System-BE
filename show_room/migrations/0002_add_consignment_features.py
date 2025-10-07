# Generated migration for consignment car features

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('show_room', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='car',
            name='car_type',
            field=models.CharField(
                choices=[('investment', 'Investment Car'), ('consignment', 'Consignment Car')],
                default='investment',
                help_text='Investment: funded by investors, Consignment: owned by seller',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='car',
            name='car_owner',
            field=models.ForeignKey(
                blank=True,
                help_text='Owner of the consignment car (seller)',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='owned_consignment_cars',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name='car',
            name='asking_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Asking price for consignment cars',
                max_digits=15,
                null=True
            ),
        ),
        migrations.AlterField(
            model_name='car',
            name='show_room_owner',
            field=models.ForeignKey(
                blank=True,
                help_text='Show room owner who manages this car',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='managed_cars',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name='carexpense',
            name='investor',
            field=models.ForeignKey(
                help_text='For investment cars: investor who paid. For consignment cars: show room owner',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='car_expenses',
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]