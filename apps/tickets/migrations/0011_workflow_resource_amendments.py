from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('tickets', '0010_ticket_workflow_refactor')]

    operations = [
        migrations.RemoveConstraint(model_name='workflownodeinstance', name='tickets_workflow_node_run_uniq'),
    ]
