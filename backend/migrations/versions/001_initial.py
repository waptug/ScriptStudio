"""Initial durable schema, frozen independently of future ORM changes."""
from alembic import op
import sqlalchemy as sa
revision='001'
down_revision=None


def column(name,kind,nullable=False,primary=False,foreign=False):
    args=[name,kind]
    if foreign:args.append(sa.ForeignKey('projects.id'))
    return sa.Column(*args,nullable=nullable,primary_key=primary)


def upgrade():
    op.create_table('projects',
        column('id',sa.String(),primary=True),column('name',sa.String()),
        column('original_script',sa.Text()),column('script',sa.Text()),column('script_revision',sa.Integer()),
        column('settings',sa.JSON()),column('storyboard',sa.JSON()),column('timeline',sa.JSON()),
        column('revision',sa.Integer()),column('undo',sa.JSON()),column('redo',sa.JSON()),column('created',sa.Float()))
    op.create_table('revisions',
        column('id',sa.String(),primary=True),column('project_id',sa.String(),foreign=True),
        column('number',sa.Integer()),column('document',sa.JSON()),column('settings',sa.JSON()))
    op.create_table('assets',
        column('id',sa.String(),primary=True),column('project_id',sa.String(),foreign=True),
        column('kind',sa.String()),column('name',sa.String()),column('path',sa.String()),
        column('checksum',sa.String()),column('duration',sa.Float()),column('info',sa.JSON()),
        column('provenance',sa.JSON()),column('thumbnail',sa.String(),nullable=True),
        column('proxy',sa.String(),nullable=True),column('created',sa.Float()))
    op.create_table('jobs',
        column('id',sa.String(),primary=True),column('project_id',sa.String(),foreign=True),
        column('kind',sa.String()),column('provider',sa.String()),column('model',sa.String()),
        column('state',sa.String()),column('provider_id',sa.String(),nullable=True),
        column('fingerprint',sa.String()),column('inputs',sa.JSON()),column('attempts',sa.Integer()),
        column('retries',sa.Integer()),column('estimated_cost',sa.Float()),column('reported_cost',sa.Float(),nullable=True),
        column('asset_id',sa.String(),nullable=True),column('result',sa.JSON()),column('error',sa.Text(),nullable=True),
        column('progress',sa.Float()),column('lease_until',sa.Float()),column('next_run',sa.Float()),
        column('created',sa.Float()),column('updated',sa.Float()))
    for table in ('revisions','assets','jobs'):
        op.create_index(f'ix_{table}_project_id',table,['project_id'])
    op.create_index('ix_jobs_state','jobs',['state'])


def downgrade():
    for table in ('jobs','assets','revisions','projects'):op.drop_table(table)
